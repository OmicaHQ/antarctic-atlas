import Foundation
import Observation
import Security

struct AIProviderConfiguration: Codable, Equatable, Sendable {
    var endpoint: String
    var model: String
}

enum CredentialPersistence: Sendable {
    case session
    case keychain
}

enum SecureTokenStoreError: LocalizedError {
    case invalidEncoding
    case keychain(OSStatus)

    var errorDescription: String? {
        switch self {
        case .invalidEncoding:
            "The credential could not be encoded."
        case .keychain(let status):
            SecCopyErrorMessageString(status, nil) as String? ?? "Keychain error \(status)."
        }
    }
}

protocol SecureTokenStore {
    func token(for account: String) throws -> String?
    func store(_ token: String, for account: String) throws
    func removeToken(for account: String) throws
}

struct KeychainTokenStore: SecureTokenStore {
    let service: String

    init(service: String = "com.omicachow.AntarcticAtlas.ai") {
        self.service = service
    }

    func token(for account: String) throws -> String? {
        var query = baseQuery(account: account)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess else { throw SecureTokenStoreError.keychain(status) }
        guard let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            throw SecureTokenStoreError.invalidEncoding
        }
        return token
    }

    func store(_ token: String, for account: String) throws {
        guard let data = token.data(using: .utf8) else {
            throw SecureTokenStoreError.invalidEncoding
        }

        let query = baseQuery(account: account)
        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        ]

        let updateStatus = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if updateStatus == errSecSuccess { return }
        guard updateStatus == errSecItemNotFound else {
            throw SecureTokenStoreError.keychain(updateStatus)
        }

        var newItem = query
        attributes.forEach { newItem[$0.key] = $0.value }
        let addStatus = SecItemAdd(newItem as CFDictionary, nil)
        guard addStatus == errSecSuccess else {
            throw SecureTokenStoreError.keychain(addStatus)
        }
    }

    func removeToken(for account: String) throws {
        let status = SecItemDelete(baseQuery(account: account) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw SecureTokenStoreError.keychain(status)
        }
    }

    private func baseQuery(account: String) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }
}

@MainActor
@Observable
final class AIService {
    private enum Keys {
        static func endpoint(_ provider: AIProvider) -> String { "ai.\(provider.rawValue).endpoint" }
        static func model(_ provider: AIProvider) -> String { "ai.\(provider.rawValue).model" }
    }

    @ObservationIgnored private let defaults: UserDefaults
    @ObservationIgnored private let tokenStore: any SecureTokenStore
    @ObservationIgnored private var sessionCredentials: [AIProvider: String] = [:]

    private(set) var configurations: [AIProvider: AIProviderConfiguration]
    private(set) var credentialProviders: Set<AIProvider> = []
    private(set) var lastCredentialError: String?

    init(
        defaults: UserDefaults = .standard,
        tokenStore: any SecureTokenStore = KeychainTokenStore()
    ) {
        self.defaults = defaults
        self.tokenStore = tokenStore

        var initialConfigurations: [AIProvider: AIProviderConfiguration] = [:]
        for provider in AIProvider.allCases where provider != .evidenceOnly {
            initialConfigurations[provider] = AIProviderConfiguration(
                endpoint: defaults.string(forKey: Keys.endpoint(provider)) ?? provider.defaultEndpoint,
                model: defaults.string(forKey: Keys.model(provider)) ?? provider.defaultModel
            )
        }
        configurations = initialConfigurations

        refreshCredentialAvailability()
    }

    func configuration(for provider: AIProvider) -> AIProviderConfiguration {
        configurations[provider] ?? AIProviderConfiguration(
            endpoint: provider.defaultEndpoint,
            model: provider.defaultModel
        )
    }

    func updateEndpoint(_ endpoint: String, for provider: AIProvider) {
        guard provider != .evidenceOnly else { return }
        var configuration = configuration(for: provider)
        configuration.endpoint = endpoint
        configurations[provider] = configuration
        defaults.set(endpoint, forKey: Keys.endpoint(provider))
    }

    func updateModel(_ model: String, for provider: AIProvider) {
        guard provider != .evidenceOnly else { return }
        var configuration = configuration(for: provider)
        configuration.model = model
        configurations[provider] = configuration
        defaults.set(model, forKey: Keys.model(provider))
    }

    func hasCredential(for provider: AIProvider) -> Bool {
        sessionCredentials[provider] != nil || credentialProviders.contains(provider)
    }

    func credential(for provider: AIProvider) throws -> String? {
        if let sessionCredential = sessionCredentials[provider] {
            return sessionCredential
        }
        guard provider.requiresCredential else { return nil }
        return try tokenStore.token(for: provider.rawValue)
    }

    func storeCredential(
        _ rawCredential: String,
        for provider: AIProvider,
        persistence: CredentialPersistence
    ) throws {
        let credential = rawCredential.trimmingCharacters(in: .whitespacesAndNewlines)
        guard provider.requiresCredential, !credential.isEmpty else { return }

        switch persistence {
        case .session:
            sessionCredentials[provider] = credential
            credentialProviders.insert(provider)
        case .keychain:
            try tokenStore.store(credential, for: provider.rawValue)
            sessionCredentials.removeValue(forKey: provider)
            credentialProviders.insert(provider)
        }
        lastCredentialError = nil
    }

    func removeCredential(for provider: AIProvider) throws {
        sessionCredentials.removeValue(forKey: provider)
        try tokenStore.removeToken(for: provider.rawValue)
        credentialProviders.remove(provider)
        lastCredentialError = nil
    }

    func validationIssue(for provider: AIProvider) -> String? {
        guard provider != .evidenceOnly else { return nil }
        let configuration = configuration(for: provider)
        guard let url = URL(string: configuration.endpoint),
              let scheme = url.scheme?.lowercased(),
              scheme == "https" || (provider == .ollama && scheme == "http") else {
            return "Enter a valid \(provider == .ollama ? "HTTP or HTTPS" : "HTTPS") endpoint."
        }
        guard !configuration.model.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return "Enter a model name."
        }
        if provider.requiresCredential && !hasCredential(for: provider) {
            return "Add an API credential before using this provider."
        }
        return nil
    }

    func refreshCredentialAvailability() {
        var available = Set<AIProvider>()
        do {
            for provider in AIProvider.allCases where provider.requiresCredential {
                if let token = try tokenStore.token(for: provider.rawValue), !token.isEmpty {
                    available.insert(provider)
                }
            }
            credentialProviders = available
            lastCredentialError = nil
        } catch {
            credentialProviders = available
            lastCredentialError = error.localizedDescription
        }
    }
}
