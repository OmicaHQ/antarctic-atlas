import AppKit
import SwiftUI

@main
@MainActor
struct AntarcticAtlasApp: App {
    @State private var model = AppModel()
    @State private var theme = Theme()
    @State private var aiService = AIService()

    var body: some Scene {
        WindowGroup {
            AntarcticAtlasRootView(model: model, aiService: aiService)
                .environment(model)
                .environment(theme)
                .environment(aiService)
                .environment(\.locale, Locale(identifier: model.language.rawValue))
                .preferredColorScheme(model.appearance.colorScheme)
                .frame(minWidth: 1_080, minHeight: 620)
        }
        .defaultSize(width: 1_488, height: 980)
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified(showsTitle: false))
        .commands {
            SidebarCommands()
            AntarcticAtlasCommands(model: model)
        }

        Settings {
            SettingsView(model: model, aiService: aiService)
                .environment(model)
                .environment(theme)
                .environment(aiService)
                .environment(\.locale, Locale(identifier: model.language.rawValue))
                .preferredColorScheme(model.appearance.colorScheme)
        }
    }
}

@MainActor
struct AntarcticAtlasRootView: View {
    @Bindable var model: AppModel
    @Bindable var aiService: AIService
    @Environment(Theme.self) private var theme
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        NavigationSplitView(columnVisibility: $model.columnVisibility) {
            SidebarView(model: model)
        } detail: {
            if usesEmbeddedInspector {
                configuredDetail
            } else {
                configuredDetail
                    .inspector(isPresented: $model.isInspectorPresented) {
                        ModuleInspectorView(model: model, aiService: aiService)
                    }
            }
        }
        .navigationSplitViewStyle(.balanced)
        .toolbar(removing: .sidebarToggle)
        .toolbar {
            ToolbarItemGroup(placement: .navigation) {
                Button {
                    withAnimation(theme.selectionAnimation(reduceMotion: reduceMotion)) {
                        model.columnVisibility = model.columnVisibility == .detailOnly ? .all : .detailOnly
                    }
                } label: {
                    Label(
                        model.text("Toggle Sidebar", "切换侧边栏"),
                        systemImage: "sidebar.left"
                    )
                    .labelStyle(.iconOnly)
                }
                .keyboardShortcut("s", modifiers: [.command, .control])
                .help(model.text("Show or hide the sidebar", "显示或隐藏侧边栏"))

                AtlasLayersMenu(model: model)
            }

            ToolbarItem(placement: .principal) {
                AtlasToolbarIdentity()
            }

            ToolbarItemGroup(placement: .primaryAction) {
                ShareLink(
                    item: URL(string: "https://github.com/OmicaChow/antarctic-atlas")!,
                    subject: Text("Antarctic Atlas"),
                    message: Text(model.text("Explore Antarctic science with evidence.", "用论文证据探索南极科学。"))
                ) {
                    Label(model.text("Share", "分享"), systemImage: "square.and.arrow.up")
                        .labelStyle(.iconOnly)
                }
                .help(model.text("Share Antarctic Atlas", "分享 Antarctic Atlas"))

                Button {
                    showAboutPanel()
                } label: {
                    Label(model.text("Information", "信息"), systemImage: "info.circle")
                        .labelStyle(.iconOnly)
                }
                .help(model.text("About Antarctic Atlas", "关于 Antarctic Atlas"))

                Button {
                    withAnimation(theme.selectionAnimation(reduceMotion: reduceMotion)) {
                        model.isInspectorPresented.toggle()
                    }
                } label: {
                    Label(
                        model.text("Inspector", "检查器"),
                        systemImage: "sidebar.right"
                    )
                    .labelStyle(.iconOnly)
                }
                .help(inspectorHelp)
            }
        }
        .tint(theme.tint(for: model.selectedModule))
        .animation(
            theme.selectionAnimation(reduceMotion: reduceMotion),
            value: model.selectedModule
        )
        .background {
            AtlasWindowConfigurator()
                .frame(width: 0, height: 0)
        }
    }

    private var configuredDetail: some View {
        ModuleDetailView(model: model)
            .searchable(
                text: $model.searchText,
                placement: .toolbar,
                prompt: Text(model.text("Search", "搜索"))
            )
            .onSubmit(of: .search) {
                model.submitSearch()
            }
    }

    private var usesEmbeddedInspector: Bool {
        model.selectedModule == .researchUniverse || model.selectedModule == .antarcticSystem
    }

    private var inspectorHelp: String {
        if usesEmbeddedInspector {
            return model.text("The evidence inspector is visible in this workspace", "证据检查器已显示在当前工作区")
        }
        return model.text("Show or hide the inspector", "显示或隐藏检查器")
    }

    private func showAboutPanel() {
        let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String
            ?? model.text("Native Development Build", "原生开发版本")
        let credits = model.text(
            "An evidence-grounded explorer for Antarctic Ice Sheet science.\n\nIncluded paper: Noble et al. (2020), Reviews of Geophysics.",
            "以论文证据为依据的南极冰盖科学探索工具。\n\n内置论文：Noble 等（2020），Reviews of Geophysics。"
        )

        NSApplication.shared.orderFrontStandardAboutPanel(options: [
            .applicationName: "Antarctic Atlas",
            .applicationVersion: version,
            .credits: NSAttributedString(string: credits),
        ])
        NSApplication.shared.activate(ignoringOtherApps: true)
    }
}

@MainActor
private struct AtlasLayersMenu: View {
    @Bindable var model: AppModel

    private var moduleSelection: Binding<AppModule> {
        Binding(
            get: { model.selectedModule },
            set: { model.select($0) }
        )
    }

    var body: some View {
        Menu {
            Picker(model.text("Workspace", "工作区"), selection: moduleSelection) {
                ForEach(AppModule.allCases) { module in
                    Label(
                        module.title(language: model.language),
                        systemImage: module.symbolName
                    )
                    .tag(module)
                }
            }

            Divider()

            Toggle(
                model.text("Show evidence metadata", "显示证据元数据"),
                isOn: $model.showsEvidenceMetadata
            )
        } label: {
            Label(model.text("Layers", "图层"), systemImage: "square.3.layers.3d")
        }
        .help(model.text("Choose a workspace or evidence layer", "选择工作区或证据图层"))
    }
}

private struct AtlasToolbarIdentity: View {
    var body: some View {
        HStack(spacing: 8) {
            Image(nsImage: NSApplication.shared.applicationIconImage)
                .resizable()
                .interpolation(.high)
                .frame(width: 23, height: 23)
                .clipShape(RoundedRectangle(cornerRadius: 4.5, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: 4.5, style: .continuous)
                        .strokeBorder(.white.opacity(0.18), lineWidth: 0.6)
                }

            Text("Antarctic Atlas")
                .font(.system(size: 13.5, weight: .semibold))
                .lineLimit(1)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Antarctic Atlas")
    }
}

private struct AtlasWindowConfigurator: NSViewRepresentable {
    func makeNSView(context: Context) -> NSView {
        let view = NSView(frame: .zero)
        configure(view)
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        configure(nsView)
    }

    private func configure(_ view: NSView) {
        DispatchQueue.main.async {
            guard let window = view.window else { return }
            window.title = "Antarctic Atlas"
            window.titleVisibility = .hidden
            window.titlebarAppearsTransparent = true
            window.toolbarStyle = .unified
            window.titlebarSeparatorStyle = .line
            window.backgroundColor = NSColor(red: 0.012, green: 0.035, blue: 0.073, alpha: 1)
        }
    }
}

@MainActor
private struct ModuleDetailView: View {
    @Bindable var model: AppModel
    @Environment(Theme.self) private var theme
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        ZStack {
            theme.detailBackground
                .ignoresSafeArea()

            ForEach(AppModule.allCases) { module in
                if model.loadedModules.contains(module) {
                    RetainedModuleFeature(
                        isActive: model.selectedModule == module,
                        reduceMotion: reduceMotion
                    ) {
                        feature(for: module)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func feature(for module: AppModule) -> some View {
        switch module {
        case .researchUniverse:
            UniverseView { topic in
                model.select(.rawPaper)
                model.searchText = topic.name
            }
        case .antarcticSystem:
            SystemExplorerView { caseStudy, observation in
                model.select(.rawPaper)
                model.searchText = "\(caseStudy.rawValue) \(observation.shortName)"
            }
        case .aiVisualizer:
            VisualizerView()
        case .miniResearchLab:
            MiniLabView()
        case .researchCompass:
            CompassView()
        case .rawPaper:
            PaperView()
        }
    }
}

/// Keeps a visited top-level workspace in the view tree, while making only the current
/// workspace visible and interactive. This lets a user return to a map, graph, or lab
/// exactly where they left it instead of rebuilding the entire feature view.
@MainActor
private struct RetainedModuleFeature<Content: View>: View {
    let isActive: Bool
    let reduceMotion: Bool
    private let content: Content

    init(
        isActive: Bool,
        reduceMotion: Bool,
        @ViewBuilder content: () -> Content
    ) {
        self.isActive = isActive
        self.reduceMotion = reduceMotion
        self.content = content()
    }

    var body: some View {
        content
            .opacity(isActive ? 1 : 0)
            .scaleEffect(isActive || reduceMotion ? 1 : 0.985)
            .allowsHitTesting(isActive)
            .accessibilityHidden(!isActive)
            .zIndex(isActive ? 1 : 0)
            .animation(
                reduceMotion ? nil : .smooth(duration: 0.36, extraBounce: 0.03),
                value: isActive
            )
    }
}

@MainActor
private struct AntarcticAtlasCommands: Commands {
    @Bindable var model: AppModel

    var body: some Commands {
        CommandGroup(replacing: .appInfo) {
            Button(model.text("About Antarctic Atlas", "关于 Antarctic Atlas")) {
                showAboutPanel()
            }
        }

        CommandMenu(model.text("Navigate", "导航")) {
            ForEach(AppModule.allCases) { module in
                Button(module.title(language: model.language)) {
                    model.select(module)
                }
                .keyboardShortcut(module.shortcut, modifiers: .command)
            }

            Divider()

            Button(model.text("Toggle Inspector", "切换检查器")) {
                model.isInspectorPresented.toggle()
            }
            .keyboardShortcut("i", modifiers: [.command, .option])
        }

        CommandGroup(replacing: .help) {
            Button(model.text("GitHub Releases", "GitHub 发布页")) {
                open("https://github.com/OmicaChow/antarctic-atlas/releases")
            }

            Button(model.text("Report an Issue", "报告问题")) {
                open("https://github.com/OmicaChow/antarctic-atlas/issues")
            }
        }
    }

    private func showAboutPanel() {
        let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String
            ?? model.text("Native Development Build", "原生开发版本")
        let credits = model.text(
            "An evidence-grounded explorer for Antarctic Ice Sheet science.\n\nIncluded paper: Noble et al. (2020), Reviews of Geophysics.",
            "以论文证据为依据的南极冰盖科学探索工具。\n\n内置论文：Noble 等（2020），Reviews of Geophysics。"
        )

        NSApplication.shared.orderFrontStandardAboutPanel(options: [
            .applicationName: "Antarctic Atlas",
            .applicationVersion: version,
            .credits: NSAttributedString(string: credits),
        ])
        NSApplication.shared.activate(ignoringOtherApps: true)
    }

    private func open(_ address: String) {
        guard let url = URL(string: address) else { return }
        NSWorkspace.shared.open(url)
    }
}
