import SwiftUI

@MainActor
struct SidebarView: View {
    @Bindable var model: AppModel
    @Environment(Theme.self) private var theme

    var body: some View {
        VStack(spacing: 0) {
            SidebarBrand(language: model.language)

            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    moduleSection
                    recentSection
                }
                .padding(.horizontal, 13)
                .padding(.bottom, 18)
            }
            .scrollIndicators(.hidden)

            SidebarFooter(model: model)
        }
        .background(theme.sidebarBackground.ignoresSafeArea())
        .overlay(alignment: .trailing) {
            Rectangle()
                .fill(theme.separator)
                .frame(width: 1)
                .ignoresSafeArea()
        }
        .navigationSplitViewColumnWidth(
            min: 244,
            ideal: AtlasMetrics.sidebarIdealWidth,
            max: 310
        )
        .tint(theme.tint(for: model.selectedModule))
        .preferredColorScheme(.dark)
    }

    private var moduleSection: some View {
        VStack(alignment: .leading, spacing: 7) {
            SidebarSectionTitle(
                model.text("Modules", "模块")
            )

            VStack(spacing: 4) {
                ForEach(AppModule.allCases) { module in
                    Button {
                        model.select(module)
                    } label: {
                        SidebarModuleRow(
                            module: module,
                            language: model.language,
                            isSelected: model.selectedModule == module
                        )
                    }
                    .buttonStyle(.plain)
                    .accessibilityHint(
                        model.text(
                            "Open \(module.title(language: .english))",
                            "打开\(module.title(language: .simplifiedChinese))"
                        )
                    )
                }
            }
        }
    }

    private var recentSection: some View {
        VStack(alignment: .leading, spacing: 7) {
            SidebarSectionTitle(
                model.text("Recent Topics", "最近主题")
            )

            VStack(spacing: 3) {
                ForEach(recentTopics.indices, id: \.self) { index in
                    let topic = recentTopics[index]
                    Button {
                        model.select(.researchUniverse)
                        model.searchText = topic.title(language: model.language)
                    } label: {
                        RecentTopicRow(
                            topic: topic,
                            language: model.language,
                            isCurrent: isCurrent(topic, index: index)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func isCurrent(_ topic: SidebarRecentTopic, index: Int) -> Bool {
        model.searchText == topic.title(language: model.language)
            || (index == 0 && model.selectedModule == .researchUniverse && model.searchText.isEmpty)
    }
}

private struct SidebarBrand: View {
    let language: AppLanguage

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "globe.americas.fill")
                .font(.system(size: 19, weight: .semibold))
                .symbolRenderingMode(.hierarchical)
                .foregroundStyle(Color(red: 0.30, green: 0.66, blue: 1.0))

            Text(AtlasCopy.text("System Explorer", "系统探索器", language: language))
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(Color(red: 0.30, green: 0.66, blue: 1.0))

            Spacer(minLength: 0)
        }
        .padding(.horizontal, 19)
        .padding(.top, 22)
        .padding(.bottom, 21)
        .accessibilityElement(children: .combine)
    }
}

private struct SidebarSectionTitle: View {
    let title: String

    init(_ title: String) {
        self.title = title
    }

    var body: some View {
        Text(title.uppercased())
            .font(.system(size: 10, weight: .semibold))
            .tracking(1.15)
            .foregroundStyle(.white.opacity(0.50))
            .padding(.leading, 5)
    }
}

private struct SidebarModuleRow: View {
    let module: AppModule
    let language: AppLanguage
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 13) {
            Image(systemName: module.symbolName)
                .font(.system(size: 18, weight: .medium))
                .symbolRenderingMode(.hierarchical)
                .foregroundStyle(isSelected ? .white : .white.opacity(0.78))
                .frame(width: 28)

            Text(module.title(language: language))
                .font(.system(size: 14, weight: isSelected ? .medium : .regular))
                .foregroundStyle(isSelected ? .white : .white.opacity(0.82))
                .lineLimit(1)

            Spacer(minLength: 0)
        }
        .padding(.horizontal, 11)
        .frame(height: 47)
        .contentShape(Rectangle())
        .background {
            if isSelected {
                RoundedRectangle(cornerRadius: AtlasMetrics.sidebarRowCornerRadius, style: .continuous)
                    .fill(Color(red: 0.085, green: 0.235, blue: 0.39))
                    .overlay {
                        RoundedRectangle(cornerRadius: AtlasMetrics.sidebarRowCornerRadius, style: .continuous)
                            .strokeBorder(Color(red: 0.31, green: 0.62, blue: 0.94).opacity(0.40), lineWidth: 0.8)
                    }
            }
        }
    }
}

private struct SidebarRecentTopic: Identifiable {
    let id: String
    let englishTitle: String
    let chineseTitle: String
    let englishTime: String
    let chineseTime: String
    let color: Color

    func title(language: AppLanguage) -> String {
        AtlasCopy.text(englishTitle, chineseTitle, language: language)
    }

    func time(language: AppLanguage) -> String {
        AtlasCopy.text(englishTime, chineseTime, language: language)
    }
}

private let recentTopics: [SidebarRecentTopic] = [
    SidebarRecentTopic(
        id: "grounding-line-retreat",
        englishTitle: "Grounding Line Retreat",
        chineseTitle: "接地线退缩",
        englishTime: "Just now",
        chineseTime: "刚刚",
        color: Color(red: 0.31, green: 0.61, blue: 1.0)
    ),
    SidebarRecentTopic(
        id: "ice-dynamics",
        englishTitle: "Ice Dynamics",
        chineseTitle: "冰动力学",
        englishTime: "2h ago",
        chineseTime: "2 小时前",
        color: Color(red: 1.0, green: 0.49, blue: 0.28)
    ),
    SidebarRecentTopic(
        id: "southern-ocean-heat",
        englishTitle: "Southern Ocean Heat",
        chineseTitle: "南大洋热量",
        englishTime: "5h ago",
        chineseTime: "5 小时前",
        color: Color(red: 0.67, green: 0.82, blue: 0.32)
    ),
    SidebarRecentTopic(
        id: "future-sea-level-risk",
        englishTitle: "Future Sea-Level Risk",
        chineseTitle: "未来海平面风险",
        englishTime: "Yesterday",
        chineseTime: "昨天",
        color: Color(red: 0.27, green: 0.55, blue: 0.98)
    ),
    SidebarRecentTopic(
        id: "ice-sheet-mass",
        englishTitle: "Antarctic Ice Sheet Mass",
        chineseTitle: "南极冰盖质量",
        englishTime: "2d ago",
        chineseTime: "2 天前",
        color: Color(red: 0.58, green: 0.38, blue: 0.84)
    ),
]

private struct RecentTopicRow: View {
    let topic: SidebarRecentTopic
    let language: AppLanguage
    let isCurrent: Bool

    var body: some View {
        HStack(alignment: .top, spacing: 11) {
            Circle()
                .fill(topic.color)
                .frame(width: 8, height: 8)
                .shadow(color: topic.color.opacity(0.65), radius: 4)
                .padding(.top, 5)

            VStack(alignment: .leading, spacing: 2) {
                Text(topic.title(language: language))
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(.white.opacity(0.90))
                    .lineLimit(1)

                Text(topic.time(language: language))
                    .font(.system(size: 11))
                    .foregroundStyle(.white.opacity(0.48))
            }

            Spacer(minLength: 0)
        }
        .padding(.horizontal, 11)
        .padding(.vertical, 9)
        .contentShape(Rectangle())
        .background {
            if isCurrent {
                RoundedRectangle(cornerRadius: 9, style: .continuous)
                    .fill(.white.opacity(0.065))
                    .overlay {
                        RoundedRectangle(cornerRadius: 9, style: .continuous)
                            .strokeBorder(.white.opacity(0.08), lineWidth: 0.6)
                    }
            }
        }
    }
}

@MainActor
private struct SidebarFooter: View {
    @Bindable var model: AppModel
    @Environment(Theme.self) private var theme

    var body: some View {
        HStack(spacing: 13) {
            SettingsLink {
                Image(systemName: "gearshape")
                    .font(.system(size: 15, weight: .medium))
                    .foregroundStyle(.white.opacity(0.66))
                    .frame(width: 28, height: 28)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .help(model.text("Open Settings", "打开设置"))

            Menu {
                Picker(model.text("Language", "语言"), selection: $model.language) {
                    ForEach(AppLanguage.allCases) { language in
                        Text(language.nativeName).tag(language)
                    }
                }
            } label: {
                HStack(spacing: 7) {
                    Text(model.language.nativeName)
                        .font(.system(size: 12.5, weight: .medium))
                        .foregroundStyle(.white.opacity(0.80))

                    Spacer(minLength: 4)

                    Image(systemName: "chevron.down")
                        .font(.system(size: 9, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.45))
                }
                .contentShape(Rectangle())
            }
            .menuStyle(.borderlessButton)

            if model.aiProvider != .evidenceOnly {
                Spacer(minLength: 4)

                Circle()
                    .fill(statusColor)
                    .frame(width: 6, height: 6)
                    .help(model.aiProvider.title(language: model.language))
            }
        }
        .padding(.horizontal, 14)
        .frame(height: 58)
        .background(Color.black.opacity(0.10))
        .overlay(alignment: .top) {
            Rectangle()
                .fill(theme.separator)
                .frame(height: 1)
        }
    }

    private var statusColor: Color {
        switch model.aiProvider {
        case .evidenceOnly: theme.iceBlue
        case .deepSeek, .openAI, .orcaRouter: .orange
        case .ollama: .green
        }
    }
}

@MainActor
struct ModuleInspectorView: View {
    @Bindable var model: AppModel
    @Bindable var aiService: AIService
    @Environment(Theme.self) private var theme

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                VStack(alignment: .leading, spacing: 8) {
                    Image(systemName: model.selectedModule.symbolName)
                        .font(.title2)
                        .foregroundStyle(theme.tint(for: model.selectedModule))
                        .symbolRenderingMode(.hierarchical)

                    Text(model.selectedModule.title(language: model.language))
                        .font(.headline)

                    Text(model.selectedModule.subtitle(language: model.language))
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Divider()

                InspectorSection(
                    title: model.text("Answer mode", "回答模式"),
                    systemImage: model.aiProvider.symbolName
                ) {
                    Text(model.aiProvider.title(language: model.language))
                        .font(.callout.weight(.medium))
                    Text(providerStatus)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                if !model.searchText.isEmpty {
                    InspectorSection(
                        title: model.text("Current search", "当前搜索"),
                        systemImage: "magnifyingglass"
                    ) {
                        Text(model.searchText)
                            .font(.callout)
                            .textSelection(.enabled)
                    }
                }

                InspectorSection(
                    title: model.text("Evidence", "证据"),
                    systemImage: "text.quote"
                ) {
                    Text(
                        model.showsEvidenceMetadata
                            ? model.text("Passage, page, and source details are shown with results.", "结果会同时显示段落、页码与来源信息。")
                            : model.text("Evidence details are available on demand.", "证据详情可按需展开。")
                    )
                    .font(.caption)
                    .foregroundStyle(.secondary)

                    Button(model.text("Open the paper", "打开论文")) {
                        model.select(.rawPaper)
                    }
                    .buttonStyle(.link)
                }

                Spacer(minLength: 8)
            }
            .padding(18)
        }
        .background(theme.controlBackground.opacity(0.28))
        .inspectorColumnWidth(
            min: 238,
            ideal: AtlasMetrics.inspectorIdealWidth,
            max: 370
        )
    }

    private var providerStatus: String {
        if model.aiProvider == .evidenceOnly {
            return model.text("Local and offline by default", "默认在本机离线运行")
        }
        if let issue = aiService.validationIssue(for: model.aiProvider) {
            return model.language == .simplifiedChinese
                ? "配置尚未完成"
                : issue
        }
        return model.aiProvider == .ollama
            ? model.text("Local model is configured", "本地模型已配置")
            : model.text("Online provider is configured", "在线服务已配置")
    }
}

private struct InspectorSection<Content: View>: View {
    let title: String
    let systemImage: String
    @ViewBuilder let content: Content

    init(
        title: String,
        systemImage: String,
        @ViewBuilder content: () -> Content
    ) {
        self.title = title
        self.systemImage = systemImage
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            Label(title, systemImage: systemImage)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
