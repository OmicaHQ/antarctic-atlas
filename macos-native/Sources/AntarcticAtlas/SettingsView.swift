import SwiftUI

@MainActor
struct SettingsView: View {
    @Bindable var model: AppModel
    @Bindable var aiService: AIService

    var body: some View {
        TabView {
            GeneralSettingsPane(model: model)
                .tabItem {
                    Label(model.text("General", "通用"), systemImage: "gearshape")
                }

            IntelligenceSettingsPane(model: model, aiService: aiService)
                .tabItem {
                    Label(model.text("Intelligence", "智能"), systemImage: "sparkles")
                }

            PrivacySettingsPane(model: model)
                .tabItem {
                    Label(model.text("Privacy", "隐私"), systemImage: "hand.raised")
                }
        }
        .frame(width: 560, height: 440)
    }
}

@MainActor
private struct GeneralSettingsPane: View {
    @Bindable var model: AppModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        Form {
            Section(model.text("Language & Appearance", "语言与外观")) {
                Picker(model.text("Language", "语言"), selection: $model.language) {
                    ForEach(AppLanguage.allCases) { language in
                        Text(language.nativeName).tag(language)
                    }
                }

                Picker(model.text("Appearance", "外观"), selection: $model.appearance) {
                    ForEach(AppearancePreference.allCases) { appearance in
                        Text(appearance.title(language: model.language)).tag(appearance)
                    }
                }

                LabeledContent(model.text("Motion", "动态效果")) {
                    Text(
                        reduceMotion
                            ? model.text("Reduced by macOS", "已由 macOS 减弱")
                            : model.text("Follows macOS", "跟随 macOS")
                    )
                    .foregroundStyle(.secondary)
                }
            }

            Section(model.text("Research Results", "研究结果")) {
                Toggle(
                    model.text("Show page and source details with evidence", "随证据显示页码与来源详情"),
                    isOn: $model.showsEvidenceMetadata
                )

                Text(
                    model.text(
                        "This keeps every explanation traceable to the included review paper.",
                        "这样可让每项解释都能追溯到内置综述论文。"
                    )
                )
                .font(.caption)
                .foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding(8)
    }
}

@MainActor
private struct IntelligenceSettingsPane: View {
    @Bindable var model: AppModel
    @Bindable var aiService: AIService

    @State private var credentialDraft = ""
    @State private var rememberCredential = false
    @State private var feedback: String?
    @State private var feedbackIsError = false

    var body: some View {
        Form {
            Section(model.text("Answer Mode", "回答模式")) {
                Picker(model.text("Provider", "服务"), selection: $model.aiProvider) {
                    ForEach(AIProvider.allCases) { provider in
                        Label(provider.title(language: model.language), systemImage: provider.symbolName)
                            .tag(provider)
                    }
                }

                Text(model.aiProvider.detail(language: model.language))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if model.aiProvider != .evidenceOnly {
                Section(model.text("Model", "模型")) {
                    TextField(
                        model.text("Endpoint", "服务地址"),
                        text: endpointBinding
                    )
                    .textFieldStyle(.roundedBorder)

                    TextField(
                        model.text("Model name", "模型名称"),
                        text: modelBinding
                    )
                    .textFieldStyle(.roundedBorder)
                }
            }

            if model.aiProvider.requiresCredential {
                Section(model.text("Credential", "凭据")) {
                    SecureField(
                        model.text("API key", "API 密钥"),
                        text: $credentialDraft
                    )
                    .textFieldStyle(.roundedBorder)

                    Toggle(
                        model.text("Remember in macOS Keychain", "保存到 macOS 钥匙串"),
                        isOn: $rememberCredential
                    )

                    HStack {
                        Button(model.text("Save Credential", "保存凭据")) {
                            saveCredential()
                        }
                        .disabled(credentialDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

                        if aiService.hasCredential(for: model.aiProvider) {
                            Button(model.text("Remove", "移除"), role: .destructive) {
                                removeCredential()
                            }
                        }
                    }

                    if let feedback {
                        Label(
                            feedback,
                            systemImage: feedbackIsError ? "exclamationmark.triangle" : "checkmark.circle"
                        )
                        .font(.caption)
                        .foregroundStyle(feedbackIsError ? Color.orange : Color.secondary)
                    }

                    Text(
                        rememberCredential
                            ? model.text("The key is stored by macOS Keychain and is never written to app preferences.", "密钥由 macOS 钥匙串保管，不会写入应用偏好设置。")
                            : model.text("The key remains in memory only until the app quits.", "密钥仅保留在内存中，退出应用后即清除。")
                    )
                    .font(.caption)
                    .foregroundStyle(.secondary)
                }
            }

            if model.aiProvider == .ollama {
                Section {
                    Label(
                        model.text("Ollama does not require an API key for the default local endpoint.", "默认本地 Ollama 地址不需要 API 密钥。"),
                        systemImage: "lock.open.display"
                    )
                    .font(.caption)
                    .foregroundStyle(.secondary)
                }
            }
        }
        .formStyle(.grouped)
        .padding(8)
        .onChange(of: model.aiProvider) { _, _ in
            credentialDraft = ""
            feedback = nil
            feedbackIsError = false
        }
    }

    private var endpointBinding: Binding<String> {
        Binding(
            get: { aiService.configuration(for: model.aiProvider).endpoint },
            set: { aiService.updateEndpoint($0, for: model.aiProvider) }
        )
    }

    private var modelBinding: Binding<String> {
        Binding(
            get: { aiService.configuration(for: model.aiProvider).model },
            set: { aiService.updateModel($0, for: model.aiProvider) }
        )
    }

    private func saveCredential() {
        do {
            try aiService.storeCredential(
                credentialDraft,
                for: model.aiProvider,
                persistence: rememberCredential ? .keychain : .session
            )
            credentialDraft = ""
            feedbackIsError = false
            feedback = model.text("Credential saved securely.", "凭据已安全保存。")
        } catch {
            feedbackIsError = true
            feedback = error.localizedDescription
        }
    }

    private func removeCredential() {
        do {
            try aiService.removeCredential(for: model.aiProvider)
            credentialDraft = ""
            feedbackIsError = false
            feedback = model.text("Credential removed.", "凭据已移除。")
        } catch {
            feedbackIsError = true
            feedback = error.localizedDescription
        }
    }
}

@MainActor
private struct PrivacySettingsPane: View {
    @Bindable var model: AppModel

    private var allowsOnlineBinding: Binding<Bool> {
        Binding(
            get: { model.allowsOnlineAI },
            set: { model.allowsOnlineAI = $0 }
        )
    }

    var body: some View {
        Form {
            Section(model.text("Default Protection", "默认保护")) {
                Label {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(model.text("Evidence Only is the default", "默认使用仅论文证据模式"))
                            .fontWeight(.medium)
                        Text(model.text("Paper search and passage retrieval stay on this Mac.", "论文搜索与段落检索均留在这台 Mac 上。"))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } icon: {
                    Image(systemName: "checkmark.shield.fill")
                        .foregroundStyle(.blue)
                }
            }

            Section(model.text("Online AI", "在线 AI")) {
                Toggle(
                    model.text("Allow online providers", "允许使用在线服务"),
                    isOn: allowsOnlineBinding
                )

                Text(
                    model.text(
                        "When enabled and selected, the current question and relevant paper passages may be sent to DeepSeek, OpenAI, or OrcaRouter. Antarctic Atlas never sends the whole PDF.",
                        "启用并选择在线服务后，当前问题和相关论文段落可能会发送给 DeepSeek、OpenAI 或 OrcaRouter。Antarctic Atlas 不会发送整份 PDF。"
                    )
                )
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            }

            Section(model.text("Local Models", "本地模型")) {
                Label(
                    model.text("Ollama can run locally without enabling online providers.", "Ollama 可在本机运行，无需启用在线服务。"),
                    systemImage: "desktopcomputer"
                )
                .foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding(8)
    }
}
