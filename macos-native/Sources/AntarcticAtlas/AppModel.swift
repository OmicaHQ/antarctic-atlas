import Foundation
import Observation
import SwiftUI

enum AppLanguage: String, CaseIterable, Identifiable, Sendable {
    case english = "en"
    case simplifiedChinese = "zh-Hans"

    var id: String { rawValue }

    var nativeName: String {
        switch self {
        case .english: "English"
        case .simplifiedChinese: "简体中文"
        }
    }

    static var systemDefault: AppLanguage {
        let preferred = Locale.preferredLanguages.first ?? "en"
        return preferred.lowercased().hasPrefix("zh") ? .simplifiedChinese : .english
    }
}

enum AppearancePreference: String, CaseIterable, Identifiable, Sendable {
    case system
    case light
    case dark

    var id: String { rawValue }

    var colorScheme: ColorScheme? {
        switch self {
        case .system: nil
        case .light: .light
        case .dark: .dark
        }
    }

    func title(language: AppLanguage) -> String {
        switch (self, language) {
        case (.system, .english): "System"
        case (.system, .simplifiedChinese): "跟随系统"
        case (.light, .english): "Light"
        case (.light, .simplifiedChinese): "浅色"
        case (.dark, .english): "Dark"
        case (.dark, .simplifiedChinese): "深色"
        }
    }
}

enum AIProvider: String, CaseIterable, Identifiable, Codable, Sendable {
    case evidenceOnly
    case deepSeek
    case openAI
    case orcaRouter
    case ollama

    var id: String { rawValue }

    var symbolName: String {
        switch self {
        case .evidenceOnly: "checkmark.shield"
        case .deepSeek: "sparkles"
        case .openAI: "brain.head.profile"
        case .orcaRouter: "arrow.triangle.2.circlepath"
        case .ollama: "desktopcomputer"
        }
    }

    var requiresCredential: Bool {
        self == .deepSeek || self == .openAI || self == .orcaRouter
    }

    var sendsDataOffDevice: Bool {
        self == .deepSeek || self == .openAI || self == .orcaRouter
    }

    var defaultEndpoint: String {
        switch self {
        case .evidenceOnly: ""
        case .deepSeek: "https://api.deepseek.com"
        case .openAI: "https://api.openai.com/v1"
        case .orcaRouter: "https://api.orcarouter.ai/v1"
        case .ollama: "http://127.0.0.1:11434"
        }
    }

    var defaultModel: String {
        switch self {
        case .evidenceOnly: ""
        case .deepSeek: "deepseek-chat"
        case .openAI: "gpt-4.1-mini"
        case .orcaRouter: "gpt-4o"
        case .ollama: "qwen3:8b"
        }
    }

    func title(language: AppLanguage) -> String {
        switch (self, language) {
        case (.evidenceOnly, .english): "Evidence Only"
        case (.evidenceOnly, .simplifiedChinese): "仅论文证据"
        case (.deepSeek, _): "DeepSeek"
        case (.openAI, _): "OpenAI"
        case (.orcaRouter, _): "OrcaRouter"
        case (.ollama, _): "Ollama"
        }
    }

    func detail(language: AppLanguage) -> String {
        switch (self, language) {
        case (.evidenceOnly, .english):
            "Search the included paper locally. Nothing is sent off this Mac."
        case (.evidenceOnly, .simplifiedChinese):
            "仅在本机检索内置论文，不向外发送任何内容。"
        case (.deepSeek, .english), (.openAI, .english):
            "Questions and selected paper passages are sent to this provider when you ask for an AI answer."
        case (.deepSeek, .simplifiedChinese), (.openAI, .simplifiedChinese):
            "仅在请求 AI 回答时，问题和选中的论文段落会发送给该服务商。"
        case (.orcaRouter, .english):
            "An optional OpenAI-compatible provider. Questions and selected paper passages are sent only when you ask for an AI answer."
        case (.orcaRouter, .simplifiedChinese):
            "可选的 OpenAI 兼容服务商。仅在请求 AI 回答时发送问题和选中的论文段落。"
        case (.ollama, .english):
            "Use a model served by Ollama on this Mac or your private network."
        case (.ollama, .simplifiedChinese):
            "使用这台 Mac 或私有网络中由 Ollama 提供的模型。"
        }
    }
}

enum AppModule: String, CaseIterable, Identifiable, Hashable, Sendable {
    case researchUniverse
    case antarcticSystem
    case aiVisualizer
    case miniResearchLab
    case researchCompass
    case rawPaper

    var id: String { rawValue }

    var symbolName: String {
        switch self {
        case .researchUniverse: "circle.hexagongrid"
        case .antarcticSystem: "globe.americas"
        case .aiVisualizer: "sparkles.rectangle.stack"
        case .miniResearchLab: "testtube.2"
        case .researchCompass: "safari"
        case .rawPaper: "doc.richtext"
        }
    }

    var shortcut: KeyEquivalent {
        switch self {
        case .researchUniverse: "1"
        case .antarcticSystem: "2"
        case .aiVisualizer: "3"
        case .miniResearchLab: "4"
        case .researchCompass: "5"
        case .rawPaper: "6"
        }
    }

    func title(language: AppLanguage) -> String {
        switch (self, language) {
        case (.researchUniverse, .english): "Research Universe"
        case (.researchUniverse, .simplifiedChinese): "研究宇宙"
        case (.antarcticSystem, .english): "Antarctic System"
        case (.antarcticSystem, .simplifiedChinese): "南极系统"
        case (.aiVisualizer, .english): "AI Visualizer"
        case (.aiVisualizer, .simplifiedChinese): "AI 可视化"
        case (.miniResearchLab, .english): "Mini Research Lab"
        case (.miniResearchLab, .simplifiedChinese): "迷你研究实验室"
        case (.researchCompass, .english): "Research Compass"
        case (.researchCompass, .simplifiedChinese): "研究罗盘"
        case (.rawPaper, .english): "Read Raw Paper"
        case (.rawPaper, .simplifiedChinese): "阅读原始论文"
        }
    }

    func subtitle(language: AppLanguage) -> String {
        switch (self, language) {
        case (.researchUniverse, .english): "Concepts and relationships grounded in the review paper"
        case (.researchUniverse, .simplifiedChinese): "以综述论文为依据，探索概念与关联"
        case (.antarcticSystem, .english): "Observation layers, regions, and coupled processes"
        case (.antarcticSystem, .simplifiedChinese): "观测图层、关键区域与耦合过程"
        case (.aiVisualizer, .english): "Turn scientific evidence into an explanatory visual story"
        case (.aiVisualizer, .simplifiedChinese): "将科学证据转化为可解释的视觉故事"
        case (.miniResearchLab, .english): "Explore transparent, educational system responses"
        case (.miniResearchLab, .simplifiedChinese): "探索透明、面向教育的系统响应"
        case (.researchCompass, .english): "Open questions and promising research directions"
        case (.researchCompass, .simplifiedChinese): "开放问题与值得推进的研究方向"
        case (.rawPaper, .english): "Search and read the complete included review"
        case (.rawPaper, .simplifiedChinese): "搜索并阅读完整内置综述论文"
        }
    }

    func searchPrompt(language: AppLanguage) -> String {
        switch (self, language) {
        case (.researchUniverse, .english): "Search concepts and evidence"
        case (.researchUniverse, .simplifiedChinese): "搜索概念与证据"
        case (.antarcticSystem, .english): "Search regions and observations"
        case (.antarcticSystem, .simplifiedChinese): "搜索区域与观测"
        case (.aiVisualizer, .english): "Search visual stories"
        case (.aiVisualizer, .simplifiedChinese): "搜索视觉故事"
        case (.miniResearchLab, .english): "Search experiments"
        case (.miniResearchLab, .simplifiedChinese): "搜索实验"
        case (.researchCompass, .english): "Search research directions"
        case (.researchCompass, .simplifiedChinese): "搜索研究方向"
        case (.rawPaper, .english): "Search the paper"
        case (.rawPaper, .simplifiedChinese): "搜索论文"
        }
    }
}

enum AtlasCopy {
    static func text(_ english: String, _ chinese: String, language: AppLanguage) -> String {
        language == .simplifiedChinese ? chinese : english
    }
}

@MainActor
@Observable
final class AppModel {
    private enum Keys {
        static let language = "app.language"
        static let appearance = "app.appearance"
        static let aiProvider = "ai.provider"
        static let showEvidenceMetadata = "research.showEvidenceMetadata"
        static let allowsOnlineAI = "privacy.allowsOnlineAI"
    }

    @ObservationIgnored private let defaults: UserDefaults

    var selectedModule: AppModule = .researchUniverse
    /// Modules stay mounted after their first visit so their local workspace state is not reset
    /// when the user moves between the top-level areas of the app.
    private(set) var loadedModules: Set<AppModule> = [.researchUniverse]
    var searchText = ""
    var searchSubmissionToken = 0
    var columnVisibility: NavigationSplitViewVisibility = .all
    var isInspectorPresented = true

    var language: AppLanguage {
        didSet { defaults.set(language.rawValue, forKey: Keys.language) }
    }

    var appearance: AppearancePreference {
        didSet { defaults.set(appearance.rawValue, forKey: Keys.appearance) }
    }

    var aiProvider: AIProvider {
        didSet {
            defaults.set(aiProvider.rawValue, forKey: Keys.aiProvider)
            if aiProvider.sendsDataOffDevice {
                allowsOnlineAI = true
            }
        }
    }

    var showsEvidenceMetadata: Bool {
        didSet { defaults.set(showsEvidenceMetadata, forKey: Keys.showEvidenceMetadata) }
    }

    var allowsOnlineAI: Bool {
        didSet {
            defaults.set(allowsOnlineAI, forKey: Keys.allowsOnlineAI)
            if !allowsOnlineAI && aiProvider.sendsDataOffDevice {
                aiProvider = .evidenceOnly
            }
        }
    }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults

        if let rawLanguage = defaults.string(forKey: Keys.language),
           let storedLanguage = AppLanguage(rawValue: rawLanguage) {
            language = storedLanguage
        } else {
            language = .systemDefault
        }

        appearance = AppearancePreference(
            rawValue: defaults.string(forKey: Keys.appearance) ?? ""
        ) ?? .system

        aiProvider = AIProvider(
            rawValue: defaults.string(forKey: Keys.aiProvider) ?? ""
        ) ?? .evidenceOnly

        showsEvidenceMetadata = defaults.object(forKey: Keys.showEvidenceMetadata) as? Bool ?? true
        allowsOnlineAI = defaults.object(forKey: Keys.allowsOnlineAI) as? Bool ?? false

        if !allowsOnlineAI && aiProvider.sendsDataOffDevice {
            aiProvider = .evidenceOnly
        }

    }

    var isEvidenceOnly: Bool { aiProvider == .evidenceOnly }

    var localizedSearchPrompt: String {
        selectedModule.searchPrompt(language: language)
    }

    func select(_ module: AppModule) {
        guard selectedModule != module else { return }
        loadedModules.insert(module)
        selectedModule = module
        searchText = ""
    }

    func submitSearch() {
        searchSubmissionToken &+= 1
    }

    func text(_ english: String, _ chinese: String) -> String {
        AtlasCopy.text(english, chinese, language: language)
    }
}
