import SwiftUI
import UniformTypeIdentifiers

struct CompassView: View {
    @Environment(AppModel.self) private var appModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var selection: String? = AACompassDirection.samples.first?.id
    @State private var themeFilter: AACompassTheme? = nil
    @State private var evidenceFilter: AACompassEvidence? = nil
    @State private var visualMode: AACompassVisualMode = .compass
    @State private var ambition = 3
    @State private var selectedRegion = "Amundsen Sea"
    @State private var selectedStarterQuestion = ""
    @State private var selectedMethods: Set<String> = []
    @State private var selectedProposalRegions: Set<String> = []
    @State private var hoveredDirectionID: String?
    @State private var researcherNote = ""
    @State private var isExporting = false
    @State private var exportMessage: String?

    private let directions = AACompassDirection.samples

    var body: some View {
        VStack(spacing: 0) {
            header
                .padding(.horizontal, 28)
                .padding(.top, 24)
                .padding(.bottom, 18)

            Divider()

            ViewThatFits(in: .horizontal) {
                HSplitView {
                    directionList
                        .frame(minWidth: 255, idealWidth: 285, maxWidth: 340)
                    detail
                        .frame(minWidth: 620)
                }

                VStack(spacing: 0) {
                    directionList
                        .frame(height: 280)
                    Divider()
                    detail
                }
            }
        }
        .background(Color(nsColor: .windowBackgroundColor).ignoresSafeArea())
        .navigationTitle("Research Compass")
        .fileExporter(
            isPresented: $isExporting,
            document: AAProposalDocument(text: proposalMarkdown),
            contentType: .plainText,
            defaultFilename: proposalFilename
        ) { result in
            switch result {
            case .success:
                exportMessage = appModel.text("Proposal seed exported.", "提案种子已导出。")
            case .failure(let error):
                exportMessage = appModel.text("Export failed", "导出失败") + ": \(error.localizedDescription)"
            }
        }
        .onChange(of: selection) { _, _ in
            exportMessage = nil
            resetDirectionControls()
        }
        .onChange(of: availableDirectionIDs) { _, _ in
            reconcileSelectionWithFilters()
        }
        .onChange(of: selectedRegion) { _, region in
            if selectedDirection.regions.contains(region) {
                selectedProposalRegions.insert(region)
            }
        }
        .onAppear {
            reconcileSelectionWithFilters()
            resetDirectionControls()
        }
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 18) {
            Image(systemName: "safari")
                .font(.system(size: 28, weight: .semibold))
                .foregroundStyle(.tint)
                .frame(width: 52, height: 52)
                .background(.tint.opacity(0.12), in: RoundedRectangle(cornerRadius: 14))
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 5) {
                Text(appModel.text("Research Compass", "研究罗盘"))
                    .font(.largeTitle.weight(.semibold))
                Text(appModel.text(
                    "Turn high-impact uncertainty into a focused, evidence-aware starting question.",
                    "把高影响、高不确定性的问题，转化为聚焦且重视证据的研究起点。"
                ))
                    .font(.title3)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            if let exportMessage {
                Label(exportMessage, systemImage: exportMessage.hasPrefix("Export failed") ? "exclamationmark.triangle" : "checkmark.circle")
                    .font(.callout)
                    .foregroundStyle(
                        exportMessage.hasPrefix("Export failed") || exportMessage.hasPrefix("导出失败")
                            ? Color.red : Color.secondary
                    )
                    .transition(.opacity)
                    .animation(focusAnimation, value: exportMessage)
            }
        }
    }

    private var directionList: some View {
        VStack(spacing: 0) {
            VStack(spacing: 10) {
                Picker(appModel.text("Theme", "主题"), selection: $themeFilter) {
                    Text(appModel.text("All themes", "全部主题")).tag(AACompassTheme?.none)
                    ForEach(AACompassTheme.allCases) { theme in
                        Text(appModel.text(theme.title, theme.chineseTitle)).tag(Optional(theme))
                    }
                }
                .pickerStyle(.menu)

                Picker(appModel.text("Evidence", "证据"), selection: $evidenceFilter) {
                    Text(appModel.text("Any evidence", "任意证据")).tag(AACompassEvidence?.none)
                    ForEach(AACompassEvidence.allCases) { evidence in
                        Text(appModel.text(evidence.title, evidence.chineseTitle)).tag(Optional(evidence))
                    }
                }
                .pickerStyle(.menu)
            }
            .padding(12)

            Divider()

            if filteredDirections.isEmpty {
                ContentUnavailableView.search(text: appModel.searchText)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                List(filteredDirections, selection: $selection) { direction in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Image(systemName: direction.theme.symbol)
                                .foregroundStyle(direction.tint)
                            Text(direction.title)
                                .font(.headline)
                                .lineLimit(2)
                        }
                        Text(direction.question)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(3)
                        HStack(spacing: 5) {
                            Text(appModel.text(direction.theme.title, direction.theme.chineseTitle))
                            Text("•")
                            Text(appModel.text("Uncertainty", "不确定性") + " \(direction.uncertainty)")
                        }
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                    }
                    .padding(.vertical, 5)
                    .tag(direction.id)
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel("\(direction.title). \(direction.question). Uncertainty \(direction.uncertainty) out of 100")
                }
                .listStyle(.sidebar)
            }
        }
        .accessibilityLabel(appModel.text("Research directions", "研究方向"))
    }

    private var detail: some View {
        ScrollView {
            if filteredDirections.isEmpty {
                ContentUnavailableView(
                    appModel.text("No matching research directions", "没有匹配的研究方向"),
                    systemImage: "scope",
                    description: Text(appModel.text("Adjust the theme, evidence, or global search filter to continue.", "请调整主题、证据或全局搜索条件后继续。"))
                )
                .frame(maxWidth: .infinity, minHeight: 420)
                .padding(26)
            } else {
                ZStack(alignment: .topLeading) {
                    VStack(alignment: .leading, spacing: 22) {
                        directionSummary
                        scoreRow
                        visualModeControl
                        modeVisualization
                            .id(visualMode)
                            .transition(focusTransition)
                        questionAndMethods
                        if visualMode == .proposalBuilder {
                            proposalBuilder
                        } else {
                            researchSeeds
                        }
                    }
                    .id(selectedDirection.id)
                    .transition(focusTransition)
                }
                .padding(26)
                .frame(maxWidth: 960, alignment: .leading)
                .frame(maxWidth: .infinity)
                .animation(focusAnimation, value: selectedDirection.id)
                .animation(focusAnimation, value: visualMode)
            }
        }
    }

    private var visualModeControl: some View {
        HStack(alignment: .center, spacing: 12) {
            Label(appModel.text("View", "视图"), systemImage: "rectangle.3.group")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)

            ViewThatFits(in: .horizontal) {
                Picker(appModel.text("View mode", "视图模式"), selection: $visualMode) {
                    ForEach(AACompassVisualMode.allCases) { mode in
                        Text(appModel.text(mode.title, mode.chineseTitle)).tag(mode)
                    }
                }
                .labelsHidden()
                .pickerStyle(.segmented)

                Picker(appModel.text("View mode", "视图模式"), selection: $visualMode) {
                    ForEach(AACompassVisualMode.allCases) { mode in
                        Label(appModel.text(mode.title, mode.chineseTitle), systemImage: mode.symbol)
                            .tag(mode)
                    }
                }
                .pickerStyle(.menu)
            }

            Spacer(minLength: 0)

            if visualMode == .compass {
                Label(appModel.text("Select any frontier bubble", "选择任一前沿气泡"), systemImage: "cursorarrow.click")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
        .padding(12)
        .background(.quaternary.opacity(0.55), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .accessibilityElement(children: .contain)
    }

    @ViewBuilder
    private var modeVisualization: some View {
        switch visualMode {
        case .compass:
            AACompassScatterPlot(
                directions: filteredDirections,
                selectedID: selectedDirection.id,
                hoveredID: $hoveredDirectionID,
                reduceMotion: reduceMotion,
                onSelect: selectDirection
            )
        case .timeline:
            AACompassTimeline(
                direction: selectedDirection,
                reduceMotion: reduceMotion
            )
        case .regionMap:
            AACompassRegionMap(
                direction: selectedDirection,
                selectedRegion: $selectedRegion,
                reduceMotion: reduceMotion
            )
        case .proposalBuilder:
            AAProposalPrelude(
                direction: selectedDirection,
                ambition: ambition,
                reduceMotion: reduceMotion
            )
        }
    }

    private var directionSummary: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 9) {
                Label(
                    appModel.text(selectedDirection.theme.title, selectedDirection.theme.chineseTitle),
                    systemImage: selectedDirection.theme.symbol
                )
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(selectedDirection.tint)
                Text(selectedDirection.timeScale)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(.quaternary, in: Capsule())
            }

            Text(selectedDirection.title)
                .font(.system(.title, design: .rounded, weight: .semibold))
                .accessibilityAddTraits(.isHeader)
            Text(selectedDirection.question)
                .font(.title3)
                .foregroundStyle(.secondary)
                .textSelection(.enabled)

            Label(selectedDirection.whyNow, systemImage: "clock.badge.exclamationmark")
                .font(.callout)
                .padding(12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(selectedDirection.tint.opacity(0.09), in: RoundedRectangle(cornerRadius: 12))
        }
    }

    private var scoreRow: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 150), spacing: 12)], spacing: 12) {
            AACompassScore(title: appModel.text("Impact", "影响力"), value: selectedDirection.impact, symbol: "globe.americas.fill", tint: selectedDirection.tint)
            AACompassScore(title: appModel.text("Uncertainty", "不确定性"), value: selectedDirection.uncertainty, symbol: "questionmark.circle.fill", tint: .orange)
            AACompassScore(title: appModel.text("Observability", "可观测性"), value: selectedDirection.observability, symbol: "eye.fill", tint: .cyan)
        }
    }

    private var questionAndMethods: some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .top, spacing: 14) {
                researchCard
                methodsCard
            }

            VStack(spacing: 14) {
                researchCard
                methodsCard
            }
        }
    }

    private var researchCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(appModel.text("Research opening", "研究切入点"), systemImage: "scope")
                .font(.headline)
            Text(selectedDirection.opening)
                .foregroundStyle(.secondary)
                .textSelection(.enabled)
            Divider()
            LabeledContent(appModel.text("Primary evidence", "主要证据")) {
                Text(selectedDirection.evidence.map { appModel.text($0.title, $0.chineseTitle) }.joined(separator: ", "))
                    .multilineTextAlignment(.trailing)
            }
            LabeledContent(appModel.text("Key uncertainty", "关键不确定性")) {
                Text(selectedDirection.uncertaintyNote)
                    .multilineTextAlignment(.trailing)
            }
        }
        .padding(18)
        .frame(maxWidth: .infinity, minHeight: 210, alignment: .topLeading)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }

    private var methodsCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(appModel.text("Useful methods", "可用方法"), systemImage: "wrench.and.screwdriver")
                .font(.headline)
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 120), spacing: 8)], alignment: .leading, spacing: 8) {
                ForEach(selectedDirection.methods, id: \.self) { method in
                    Label(method, systemImage: "checkmark")
                        .font(.caption.weight(.medium))
                        .padding(.horizontal, 9)
                        .padding(.vertical, 6)
                        .background(.quaternary, in: Capsule())
                }
            }
            Spacer(minLength: 8)
            Text(appModel.text(
                "Combine at least one observational method with an explicit uncertainty test.",
                "至少结合一种观测方法，并明确设置不确定性检验。"
            ))
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(18)
        .frame(maxWidth: .infinity, minHeight: 210, alignment: .topLeading)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }

    private var researchSeeds: some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .top, spacing: 14) {
                researchSeedGap
                researchSeedQuestions
            }

            VStack(spacing: 14) {
                researchSeedGap
                researchSeedQuestions
            }
        }
    }

    private var researchSeedGap: some View {
        VStack(alignment: .leading, spacing: 9) {
            Label(appModel.text("Key gap", "关键缺口"), systemImage: "arrow.triangle.branch")
                .font(.headline)
            Text(selectedDirection.gap)
                .foregroundStyle(.secondary)
                .textSelection(.enabled)
            Divider()
            Label(appModel.text("A practical angle", "一个可落地的切入角度"), systemImage: "lightbulb")
                .font(.caption.weight(.semibold))
                .foregroundStyle(selectedDirection.tint)
            Text(selectedDirection.studentAngle)
                .font(.callout)
                .foregroundStyle(.secondary)
                .textSelection(.enabled)
        }
        .padding(18)
        .frame(maxWidth: .infinity, minHeight: 184, alignment: .topLeading)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }

    private var researchSeedQuestions: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(appModel.text("Starter questions", "起步问题"), systemImage: "questionmark.bubble")
                .font(.headline)
            ForEach(selectedDirection.starterQuestions, id: \.self) { question in
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: "circle.fill")
                        .font(.system(size: 5))
                        .foregroundStyle(selectedDirection.tint)
                        .padding(.top, 6)
                    Text(question)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(18)
        .frame(maxWidth: .infinity, minHeight: 184, alignment: .topLeading)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }

    private var proposalBuilder: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Label(appModel.text("Proposal seed", "提案种子"), systemImage: "doc.badge.plus")
                        .font(.title3.weight(.semibold))
                    Text(appModel.text("A structured starting point — edit it after export.", "一个结构化起点；导出后可继续编辑。"))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()

                ShareLink(item: proposalMarkdown, preview: SharePreview(proposalFilename)) {
                    Label(appModel.text("Share", "分享"), systemImage: "square.and.arrow.up")
                }

                Button {
                    isExporting = true
                } label: {
                    Label(appModel.text("Export Markdown", "导出 Markdown"), systemImage: "arrow.down.doc")
                }
                .buttonStyle(.borderedProminent)
            }

            VStack(alignment: .leading, spacing: 12) {
                Picker(appModel.text("Starter question", "起步问题"), selection: $selectedStarterQuestion) {
                    ForEach(selectedDirection.starterQuestions, id: \.self) { question in
                        Text(question).tag(question)
                    }
                }
                .pickerStyle(.menu)

                ViewThatFits(in: .horizontal) {
                    HStack(alignment: .top, spacing: 18) {
                        methodSelection
                        regionSelection
                    }

                    VStack(alignment: .leading, spacing: 14) {
                        methodSelection
                        regionSelection
                    }
                }

                Stepper(appModel.text("Ambition", "目标强度") + " \(ambition) / 5", value: $ambition, in: 1...5)
                    .fixedSize()
            }

            VStack(alignment: .leading, spacing: 7) {
                Text(appModel.text("Your note", "你的备注"))
                    .font(.caption.weight(.medium))
                TextField(
                    appModel.text("Optional constraint, dataset, or collaborator", "可选：约束、数据集或合作者"),
                    text: $researcherNote,
                    axis: .vertical
                )
                    .textFieldStyle(.roundedBorder)
            }

            Text(proposalMarkdown)
                .font(.system(.callout, design: .monospaced))
                .foregroundStyle(.secondary)
                .textSelection(.enabled)
                .padding(14)
                .frame(maxWidth: .infinity, minHeight: 210, alignment: .topLeading)
                .background(Color(nsColor: .textBackgroundColor).opacity(0.62), in: RoundedRectangle(cornerRadius: 12))
                .accessibilityLabel(appModel.text("Proposal seed preview", "提案种子预览"))
        }
        .padding(20)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(.white.opacity(0.09))
        }
    }

    private var methodSelection: some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(appModel.text("Methods to include", "拟包含的方法"))
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            ForEach(selectedDirection.methods, id: \.self) { method in
                Toggle(method, isOn: methodBinding(for: method))
                    .toggleStyle(.checkbox)
                    .font(.callout)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var regionSelection: some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(appModel.text("Regions / evidence contexts", "区域／证据情境"))
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            ForEach(selectedDirection.regions, id: \.self) { region in
                Toggle(region, isOn: regionBinding(for: region))
                    .toggleStyle(.checkbox)
                    .font(.callout)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var filteredDirections: [AACompassDirection] {
        directions.filter { direction in
            let matchesTheme = themeFilter == nil || direction.theme == themeFilter
            let matchesEvidence = evidenceFilter == nil || direction.evidence.contains(evidenceFilter!)
            let query = appModel.searchText.trimmingCharacters(in: .whitespacesAndNewlines)
            let matchesSearch = query.isEmpty || [
                direction.title,
                direction.question,
                direction.opening,
                direction.theme.title,
                direction.theme.chineseTitle,
                direction.chineseSearchTerms
            ]
                .joined(separator: " ")
                .localizedCaseInsensitiveContains(query)
            return matchesTheme && matchesEvidence && matchesSearch
        }
    }

    private var availableDirectionIDs: [String] {
        filteredDirections.map(\.id)
    }

    private func selectDirection(_ direction: AACompassDirection) {
        guard filteredDirections.contains(where: { $0.id == direction.id }) else { return }
        selection = direction.id
    }

    private func reconcileSelectionWithFilters() {
        guard !filteredDirections.isEmpty else {
            selection = nil
            return
        }
        guard let selection,
              filteredDirections.contains(where: { $0.id == selection }) else {
            self.selection = filteredDirections[0].id
            return
        }
    }

    private func resetDirectionControls() {
        guard !filteredDirections.isEmpty else { return }
        let direction = selectedDirection
        selectedRegion = direction.regions.first ?? "Amundsen Sea"
        selectedStarterQuestion = direction.starterQuestions.first ?? direction.question
        selectedMethods = Set(direction.methods.prefix(2))
        selectedProposalRegions = Set(direction.regions.prefix(2))
    }

    private func methodBinding(for method: String) -> Binding<Bool> {
        Binding(
            get: { selectedMethods.contains(method) },
            set: { isSelected in
                if isSelected {
                    selectedMethods.insert(method)
                } else {
                    selectedMethods.remove(method)
                }
            }
        )
    }

    private func regionBinding(for region: String) -> Binding<Bool> {
        Binding(
            get: { selectedProposalRegions.contains(region) },
            set: { isSelected in
                if isSelected {
                    selectedProposalRegions.insert(region)
                    selectedRegion = region
                } else {
                    selectedProposalRegions.remove(region)
                }
            }
        )
    }

    private var selectedProposalMethodList: [String] {
        let choices = selectedDirection.methods.filter(selectedMethods.contains)
        return choices.isEmpty ? Array(selectedDirection.methods.prefix(2)) : choices
    }

    private var selectedProposalRegionList: [String] {
        let choices = selectedDirection.regions.filter(selectedProposalRegions.contains)
        return choices.isEmpty ? Array(selectedDirection.regions.prefix(2)) : choices
    }

    private var focusAnimation: Animation? {
        reduceMotion ? nil : .smooth(duration: 0.26)
    }

    private var focusTransition: AnyTransition {
        reduceMotion
            ? .identity
            : .asymmetric(
                insertion: .opacity.combined(with: .offset(x: 14, y: 0)),
                removal: .opacity.combined(with: .offset(x: -7, y: 0))
            )
    }

    private var selectedDirection: AACompassDirection {
        filteredDirections.first(where: { $0.id == selection }) ?? filteredDirections.first ?? directions[0]
    }

    private var proposalFilename: String {
        "Antarctic-Atlas-\(selectedDirection.id)-proposal.md"
    }

    private var proposalMarkdown: String {
        let noteLine = researcherNote.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? "Add a local constraint, dataset, or collaboration requirement."
            : researcherNote.trimmingCharacters(in: .whitespacesAndNewlines)
        let questionLabel = appModel.text("Research question", "研究问题")
        let styleLabel = appModel.text("Research style", "研究类型")
        let whyLabel = appModel.text("Motivation", "研究动机")
        let gapLabel = appModel.text("Knowledge gap", "知识缺口")
        let approachLabel = appModel.text("Possible approach", "可行方法")
        let outcomeLabel = appModel.text("Expected output", "预期产出")
        let hypothesisLabel = appModel.text("Working hypothesis", "工作假设")
        let uncertaintyLabel = appModel.text("Uncertainty test", "不确定性检验")
        let noteLabel = appModel.text("Researcher note", "研究者备注")
        let footer = appModel.text(
            "Generated as a proposal seed by Antarctic Atlas. Validate assumptions, data access, ethics, and feasibility before use.",
            "由 Antarctic Atlas 生成的提案种子。使用前请验证假设、数据可得性、伦理与可行性。"
        )
        return """
        # \(selectedDirection.title)

        **\(questionLabel)**
        \(selectedStarterQuestion.isEmpty ? selectedDirection.question : selectedStarterQuestion)

        **\(styleLabel)**
        \(AACompassAmbition.description(for: ambition, chinese: appModel.language == .simplifiedChinese))

        **\(whyLabel)**
        \(selectedDirection.whyNow)

        **\(gapLabel)**
        \(selectedDirection.gap)

        **\(approachLabel)**
        Use \(selectedProposalMethodList.joined(separator: ", ")) focused on \(selectedProposalRegionList.joined(separator: ", ")). The goal is to connect mechanism, observation, and uncertainty rather than only summarize the paper.

        **\(hypothesisLabel)**
        \(selectedDirection.hypothesis)

        **\(uncertaintyLabel)**
        \(selectedDirection.uncertaintyNote)

        **\(outcomeLabel)**
        1. A concept map of the mechanism.
        2. A small evidence table linking observations to physical interpretation.
        3. A visual figure or interactive module that explains the research direction.
        4. A short uncertainty paragraph explaining what remains unknown.

        **\(noteLabel)**
        \(noteLine)

        ---
        \(footer)
        """
    }
}

private enum AACompassVisualMode: String, CaseIterable, Identifiable {
    case compass
    case timeline
    case regionMap
    case proposalBuilder

    var id: String { rawValue }

    var title: String {
        switch self {
        case .compass: "Compass"
        case .timeline: "Timeline"
        case .regionMap: "Region map"
        case .proposalBuilder: "Proposal builder"
        }
    }

    var chineseTitle: String {
        switch self {
        case .compass: "罗盘"
        case .timeline: "时间线"
        case .regionMap: "区域地图"
        case .proposalBuilder: "提案构建器"
        }
    }

    var symbol: String {
        switch self {
        case .compass: "scope"
        case .timeline: "clock.arrow.circlepath"
        case .regionMap: "map"
        case .proposalBuilder: "doc.badge.plus"
        }
    }
}

private struct AACompassScatterPlot: View {
    let directions: [AACompassDirection]
    let selectedID: String
    @Binding var hoveredID: String?
    let reduceMotion: Bool
    let onSelect: (AACompassDirection) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Frontier compass")
                        .font(.headline)
                    Text("Impact, uncertainty, and direct observability across the current research directions.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Label("Bubble area = impact", systemImage: "circle.fill")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            GeometryReader { proxy in
                let plot = Self.plotRect(in: proxy.size)
                ZStack(alignment: .topLeading) {
                    Canvas { context, size in
                        Self.drawBackground(context: &context, size: size, plot: plot)

                        for direction in directions {
                            let point = Self.point(for: direction, in: plot)
                            let radius = Self.radius(for: direction)
                            let isSelected = direction.id == selectedID
                            let isHovered = direction.id == hoveredID
                            let bubble = Path(ellipseIn: CGRect(
                                x: point.x - radius,
                                y: point.y - radius,
                                width: radius * 2,
                                height: radius * 2
                            ))
                            let fill = Self.bubbleColor(for: direction)
                            context.fill(bubble, with: .color(fill.opacity(isSelected ? 0.92 : (isHovered ? 0.78 : 0.46))))
                            context.stroke(
                                bubble,
                                with: .color(isSelected ? .white : fill.opacity(isHovered ? 0.90 : 0.56)),
                                lineWidth: isSelected ? 3.3 : (isHovered ? 2.0 : 1.0)
                            )
                            if isSelected {
                                let halo = Path(ellipseIn: CGRect(
                                    x: point.x - radius - 6,
                                    y: point.y - radius - 6,
                                    width: (radius + 6) * 2,
                                    height: (radius + 6) * 2
                                ))
                                context.stroke(halo, with: .color(fill.opacity(0.36)), lineWidth: 2)
                            }
                        }
                    }

                    Text("High impact + high uncertainty = frontier zone")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                        .position(x: plot.midX + plot.width * 0.24, y: plot.minY + 18)
                        .allowsHitTesting(false)

                    Text("Sea-level impact")
                        .font(.caption2.weight(.medium))
                        .foregroundStyle(.secondary)
                        .rotationEffect(.degrees(-90))
                        .position(x: 14, y: plot.midY)
                        .allowsHitTesting(false)

                    Text("Scientific uncertainty")
                        .font(.caption2.weight(.medium))
                        .foregroundStyle(.secondary)
                        .position(x: plot.midX, y: plot.maxY + 22)
                        .allowsHitTesting(false)

                    ForEach(directions) { direction in
                        let point = Self.point(for: direction, in: plot)
                        let radius = Self.radius(for: direction)
                        let labelPoint = Self.labelPoint(for: direction, point: point, plot: plot)
                        AACompassScatterPoint(
                            direction: direction,
                            point: point,
                            radius: radius,
                            labelPoint: labelPoint,
                            isSelected: direction.id == selectedID,
                            isHovered: direction.id == hoveredID,
                            hoveredID: $hoveredID,
                            onSelect: onSelect
                        )
                        .frame(width: proxy.size.width, height: proxy.size.height, alignment: .topLeading)
                    }
                }
                .animation(reduceMotion ? nil : .smooth(duration: 0.30), value: selectedID)
                .animation(reduceMotion ? nil : .easeOut(duration: 0.16), value: hoveredID)
            }
            .frame(minHeight: 340, idealHeight: 372)

            HStack(spacing: 12) {
                Label("Low", systemImage: "circle.lefthalf.filled")
                Capsule()
                    .fill(LinearGradient(colors: [.white.opacity(0.75), .cyan, .blue], startPoint: .leading, endPoint: .trailing))
                    .frame(width: 128, height: 8)
                Label("High observability", systemImage: "eye")
            }
            .font(.caption2)
            .foregroundStyle(.secondary)
        }
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(.white.opacity(0.08))
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Frontier research compass")
    }

    private static func plotRect(in size: CGSize) -> CGRect {
        CGRect(
            x: 46,
            y: 34,
            width: max(260, size.width - 76),
            height: max(220, size.height - 72)
        )
    }

    private static func point(for direction: AACompassDirection, in plot: CGRect) -> CGPoint {
        let uncertainty = CGFloat(direction.uncertainty)
        let impact = CGFloat(direction.impact)
        let xFraction = max(0.04, min(0.96, (uncertainty - 35) / 65))
        let yFraction = max(0.06, min(0.94, 1 - ((impact - 65) / 35)))
        return CGPoint(
            x: plot.minX + plot.width * xFraction,
            y: plot.minY + plot.height * yFraction
        )
    }

    private static func radius(for direction: AACompassDirection) -> CGFloat {
        11 + CGFloat(direction.impact) * 0.15
    }

    private static func bubbleColor(for direction: AACompassDirection) -> Color {
        if direction.observability < 55 { return Color.white.opacity(0.84) }
        if direction.observability > 75 { return .cyan }
        return direction.tint
    }

    private static func labelPoint(for direction: AACompassDirection, point: CGPoint, plot: CGRect) -> CGPoint {
        let offset: CGSize
        switch direction.id {
        case "ocean-heat-pathways": offset = .init(width: -42, height: -49)
        case "grounding-line-instability": offset = .init(width: -62, height: -49)
        case "ice-shelf-fracture": offset = .init(width: -67, height: 47)
        case "subglacial-water": offset = .init(width: -50, height: 48)
        case "solid-earth-feedbacks": offset = .init(width: 66, height: -24)
        case "paleo-projection-constraints": offset = .init(width: -72, height: -28)
        case "ai-assisted-observation": offset = .init(width: -58, height: 48)
        default: offset = .init(width: 0, height: -44)
        }
        return CGPoint(
            x: min(plot.maxX - 64, max(plot.minX + 64, point.x + offset.width)),
            y: min(plot.maxY - 20, max(plot.minY + 16, point.y + offset.height))
        )
    }

    private static func drawBackground(context: inout GraphicsContext, size: CGSize, plot: CGRect) {
        let plotPath = Path(roundedRect: plot, cornerRadius: 14)
        context.fill(plotPath, with: .color(Color.black.opacity(0.10)))
        let frontier = CGRect(x: plot.midX, y: plot.minY, width: plot.width / 2, height: plot.height / 2)
        context.fill(Path(roundedRect: frontier, cornerRadius: 0), with: .color(Color.orange.opacity(0.08)))
        let stable = CGRect(x: plot.minX, y: plot.minY, width: plot.width / 2, height: plot.height / 2)
        context.fill(Path(roundedRect: stable, cornerRadius: 0), with: .color(Color.cyan.opacity(0.055)))
        for index in 0...5 {
            let x = plot.minX + plot.width * CGFloat(index) / 5
            let y = plot.minY + plot.height * CGFloat(index) / 5
            var vertical = Path()
            vertical.move(to: CGPoint(x: x, y: plot.minY))
            vertical.addLine(to: CGPoint(x: x, y: plot.maxY))
            context.stroke(vertical, with: .color(.white.opacity(0.09)), lineWidth: 1)
            var horizontal = Path()
            horizontal.move(to: CGPoint(x: plot.minX, y: y))
            horizontal.addLine(to: CGPoint(x: plot.maxX, y: y))
            context.stroke(horizontal, with: .color(.white.opacity(0.09)), lineWidth: 1)
        }
        context.stroke(plotPath, with: .color(.white.opacity(0.13)), lineWidth: 1)
    }
}

private struct AACompassScatterPoint: View {
    let direction: AACompassDirection
    let point: CGPoint
    let radius: CGFloat
    let labelPoint: CGPoint
    let isSelected: Bool
    let isHovered: Bool
    @Binding var hoveredID: String?
    let onSelect: (AACompassDirection) -> Void

    var body: some View {
        ZStack {
            Button {
                onSelect(direction)
            } label: {
                Circle()
                    .fill(.clear)
                    .contentShape(Circle())
            }
            .buttonStyle(.plain)
            .frame(width: max(44, radius * 2 + 14), height: max(44, radius * 2 + 14))
            .onHover { inside in
                hoveredID = inside ? direction.id : (hoveredID == direction.id ? nil : hoveredID)
            }
            .accessibilityLabel(direction.title)
            .accessibilityValue("Impact \(direction.impact), uncertainty \(direction.uncertainty), observability \(direction.observability)")
            .accessibilityHint("Select this research direction")
            .position(point)

            Text(direction.chartTitle)
                .font(.system(size: isSelected ? 10 : 9, weight: isSelected ? .semibold : .regular))
                .foregroundStyle(isSelected || isHovered ? .primary : .secondary)
                .multilineTextAlignment(.center)
                .lineLimit(2)
                .frame(width: isSelected ? 132 : 118)
                .position(labelPoint)
                .allowsHitTesting(false)
        }
    }
}

private struct AACompassTimeline: View {
    let direction: AACompassDirection
    let reduceMotion: Bool

    private var stages: [AACompassTimelineStage] {
        [
            .init("Past evidence", "Use paleo records to test whether the mechanism happened before.", "clock.arrow.circlepath"),
            .init("Present observation", "Use satellites, field data, and process observations to identify active signals.", "eye"),
            .init("Process model", "Represent the mechanism with \(direction.methods.prefix(2).joined(separator: ", ")).", "cube.transparent"),
            .init("Coupled projection", "Connect the mechanism to uncertainty: \(direction.gap)", "arrow.triangle.merge"),
            .init("Research product", "Turn the result into a map, figure, interactive tool, or proposal.", "sparkles")
        ]
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("\(direction.title) research pathway", systemImage: "clock.arrow.circlepath")
                .font(.headline)
            Text("A continuous evidence path from an earlier signal to a useful, transparent research product.")
                .font(.caption)
                .foregroundStyle(.secondary)

            GeometryReader { proxy in
                TimelineView(.animation(minimumInterval: 1.0 / 24.0, paused: reduceMotion)) { timeline in
                    let line = CGRect(x: 36, y: 104, width: max(260, proxy.size.width - 72), height: 1)
                    let phase = reduceMotion ? 0.0 : timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 3.6) / 3.6
                    ZStack(alignment: .topLeading) {
                        Canvas { context, _ in
                            var pathway = Path()
                            pathway.move(to: CGPoint(x: line.minX, y: line.midY))
                            pathway.addLine(to: CGPoint(x: line.maxX, y: line.midY))
                            context.stroke(pathway, with: .color(direction.tint.opacity(0.36)), lineWidth: 3)
                            let pulseX = line.minX + line.width * phase
                            let pulse = Path(ellipseIn: CGRect(x: pulseX - 6, y: line.midY - 6, width: 12, height: 12))
                            context.fill(pulse, with: .color(direction.tint.opacity(0.85)))
                            context.stroke(pulse, with: .color(.white.opacity(0.85)), lineWidth: 1.4)
                        }

                        ForEach(Array(stages.enumerated()), id: \.element.id) { index, stage in
                            let fraction = CGFloat(index) / CGFloat(max(stages.count - 1, 1))
                            let x = line.minX + line.width * fraction
                            VStack(spacing: 7) {
                                Label(stage.title, systemImage: stage.symbol)
                                    .font(.caption.weight(.semibold))
                                    .multilineTextAlignment(.center)
                                    .frame(width: 128)
                                Circle()
                                    .fill(direction.tint)
                                    .frame(width: 26, height: 26)
                                    .overlay {
                                        Circle().stroke(.white.opacity(0.86), lineWidth: 2)
                                    }
                                    .shadow(color: direction.tint.opacity(reduceMotion ? 0 : 0.36), radius: 8)
                                Text(stage.detail)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                    .multilineTextAlignment(.center)
                                    .frame(width: 132)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            .position(x: x, y: 112)
                            .accessibilityElement(children: .combine)
                        }
                    }
                }
            }
            .frame(minHeight: 260, idealHeight: 282)
        }
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(.white.opacity(0.08))
        }
        .accessibilityLabel("Research pathway timeline for \(direction.title)")
    }
}

private struct AACompassTimelineStage: Identifiable {
    let title: String
    let detail: String
    let symbol: String
    var id: String { title }

    init(_ title: String, _ detail: String, _ symbol: String) {
        self.title = title
        self.detail = detail
        self.symbol = symbol
    }
}

private struct AACompassRegionMap: View {
    let direction: AACompassDirection
    @Binding var selectedRegion: String
    let reduceMotion: Bool

    private let colors: [Color] = [.orange, .cyan, .yellow, .green]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Label("Conceptual region map", systemImage: "map")
                    .font(.headline)
                Spacer()
                Text("Select a region")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Text("A research-planning locator for \(direction.title), not a precise GIS layer.")
                .font(.caption)
                .foregroundStyle(.secondary)

            GeometryReader { proxy in
                let mapRect = CGRect(x: 28, y: 18, width: max(280, proxy.size.width - 56), height: max(200, proxy.size.height - 42))
                ZStack(alignment: .topLeading) {
                    Canvas { context, _ in
                        Self.drawMap(context: &context, mapRect: mapRect, tint: direction.tint)
                        for (index, region) in direction.regions.enumerated() {
                            let point = Self.point(for: region, in: mapRect)
                            let markerColor = colors[index % colors.count]
                            let isSelected = region == selectedRegion
                            let marker = Path(ellipseIn: CGRect(x: point.x - 9, y: point.y - 9, width: 18, height: 18))
                            context.fill(marker, with: .color(markerColor.opacity(isSelected ? 0.94 : 0.70)))
                            context.stroke(marker, with: .color(.white.opacity(isSelected ? 0.94 : 0.70)), lineWidth: isSelected ? 2.6 : 1.4)
                            if isSelected {
                                let halo = Path(ellipseIn: CGRect(x: point.x - 15, y: point.y - 15, width: 30, height: 30))
                                context.stroke(halo, with: .color(markerColor.opacity(0.36)), lineWidth: 2)
                            }
                        }
                    }

                    ForEach(Array(direction.regions.enumerated()), id: \.element) { index, region in
                        let point = Self.point(for: region, in: mapRect)
                        let label = Self.labelPoint(for: point, in: mapRect)
                        Button {
                            selectedRegion = region
                        } label: {
                            Color.clear.contentShape(Circle())
                        }
                        .buttonStyle(.plain)
                        .frame(width: 42, height: 42)
                        .position(point)
                        .accessibilityLabel(region)
                        .accessibilityValue(region == selectedRegion ? "Selected" : "")

                        Text(region)
                            .font(.caption.weight(region == selectedRegion ? .semibold : .regular))
                            .foregroundStyle(region == selectedRegion ? .primary : .secondary)
                            .lineLimit(1)
                            .padding(.horizontal, 7)
                            .padding(.vertical, 4)
                            .background(.thinMaterial.opacity(0.72), in: Capsule())
                            .position(label)
                            .allowsHitTesting(false)
                    }
                }
                .animation(reduceMotion ? nil : .smooth(duration: 0.24), value: selectedRegion)
            }
            .frame(minHeight: 270, idealHeight: 308)
        }
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(.white.opacity(0.08))
        }
        .accessibilityLabel("Conceptual Antarctic region map")
    }

    private static func drawMap(context: inout GraphicsContext, mapRect: CGRect, tint: Color) {
        let frame = Path(roundedRect: mapRect, cornerRadius: 18)
        context.fill(
            frame,
            with: .linearGradient(
                Gradient(colors: [Color(red: 0.035, green: 0.16, blue: 0.27), Color(red: 0.02, green: 0.07, blue: 0.15)]),
                startPoint: mapRect.origin,
                endPoint: CGPoint(x: mapRect.maxX, y: mapRect.maxY)
            )
        )
        context.stroke(frame, with: .color(.white.opacity(0.14)), lineWidth: 1)

        var antarctica = Path()
        antarctica.move(to: CGPoint(x: mapRect.midX - mapRect.width * 0.34, y: mapRect.midY + mapRect.height * 0.10))
        antarctica.addCurve(
            to: CGPoint(x: mapRect.midX + mapRect.width * 0.36, y: mapRect.midY + mapRect.height * 0.04),
            control1: CGPoint(x: mapRect.midX - mapRect.width * 0.18, y: mapRect.minY + mapRect.height * 0.16),
            control2: CGPoint(x: mapRect.midX + mapRect.width * 0.22, y: mapRect.minY + mapRect.height * 0.12)
        )
        antarctica.addCurve(
            to: CGPoint(x: mapRect.midX - mapRect.width * 0.34, y: mapRect.midY + mapRect.height * 0.10),
            control1: CGPoint(x: mapRect.midX + mapRect.width * 0.22, y: mapRect.maxY - mapRect.height * 0.15),
            control2: CGPoint(x: mapRect.midX - mapRect.width * 0.10, y: mapRect.maxY - mapRect.height * 0.08)
        )
        context.fill(
            antarctica,
            with: .linearGradient(
                Gradient(colors: [.white.opacity(0.93), tint.opacity(0.42)]),
                startPoint: CGPoint(x: mapRect.midX, y: mapRect.minY),
                endPoint: CGPoint(x: mapRect.midX, y: mapRect.maxY)
            )
        )
        context.stroke(antarctica, with: .color(.white.opacity(0.88)), lineWidth: 1.6)

        for fraction in [0.25, 0.5, 0.75] {
            var longitude = Path()
            let x = mapRect.minX + mapRect.width * fraction
            longitude.move(to: CGPoint(x: x, y: mapRect.minY + 14))
            longitude.addLine(to: CGPoint(x: x, y: mapRect.maxY - 14))
            context.stroke(longitude, with: .color(.white.opacity(0.055)), lineWidth: 1)
        }
    }

    private static func point(for region: String, in rect: CGRect) -> CGPoint {
        let coordinate = coordinates[region] ?? AACompassMapCoordinate(latitude: -75, longitude: 0)
        let xFraction = max(0.13, min(0.87, 0.5 + coordinate.longitude / 360))
        let yFraction = max(0.20, min(0.80, 0.52 + (coordinate.latitude + 75) / 70))
        return CGPoint(x: rect.minX + rect.width * xFraction, y: rect.minY + rect.height * yFraction)
    }

    private static func labelPoint(for point: CGPoint, in rect: CGRect) -> CGPoint {
        let x = point.x > rect.midX ? point.x - 54 : point.x + 56
        let y = point.y < rect.midY ? point.y + 20 : point.y - 20
        return CGPoint(
            x: min(rect.maxX - 68, max(rect.minX + 68, x)),
            y: min(rect.maxY - 14, max(rect.minY + 14, y))
        )
    }

    private static let coordinates: [String: AACompassMapCoordinate] = [
        "Amundsen Sea": .init(latitude: -74.5, longitude: -110),
        "Bellingshausen Sea": .init(latitude: -72, longitude: -85),
        "Totten sector": .init(latitude: -67, longitude: 116),
        "Weddell Sea": .init(latitude: -76, longitude: -55),
        "Thwaites Glacier": .init(latitude: -75.5, longitude: -106),
        "Pine Island Glacier": .init(latitude: -75, longitude: -100),
        "Wilkes Basin": .init(latitude: -70, longitude: 140),
        "Aurora Basin": .init(latitude: -72, longitude: 120),
        "Antarctic Peninsula": .init(latitude: -65, longitude: -62),
        "Wilkes Land": .init(latitude: -70, longitude: 130),
        "Ross Sea": .init(latitude: -77, longitude: -175),
        "East Antarctica": .init(latitude: -78, longitude: 80),
        "Whillans Ice Stream": .init(latitude: -84, longitude: -155),
        "Recovery Glacier": .init(latitude: -82, longitude: 30),
        "Continent-wide": .init(latitude: -80, longitude: 0)
    ]
}

private struct AACompassMapCoordinate {
    let latitude: CGFloat
    let longitude: CGFloat
}

private struct AAProposalPrelude: View {
    let direction: AACompassDirection
    let ambition: Int
    let reduceMotion: Bool

    private let steps = [
        ("Question", "questionmark.bubble"),
        ("Evidence", "checkmark.seal"),
        ("Methods", "wrench.and.screwdriver"),
        ("Research product", "sparkles")
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Label("Proposal builder", systemImage: "doc.badge.plus")
                        .font(.headline)
                    Text("Shape a transparent seed for \(direction.title) before taking it into a fuller proposal.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text("Ambition \(ambition) / 5")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(direction.tint)
                    .padding(.horizontal, 9)
                    .padding(.vertical, 5)
                    .background(direction.tint.opacity(0.12), in: Capsule())
            }

            HStack(spacing: 0) {
                ForEach(Array(steps.enumerated()), id: \.offset) { index, step in
                    VStack(spacing: 8) {
                        Image(systemName: step.1)
                            .font(.system(size: 18, weight: .semibold))
                            .foregroundStyle(direction.tint)
                            .frame(width: 42, height: 42)
                            .background(direction.tint.opacity(0.12), in: Circle())
                        Text(step.0)
                            .font(.caption.weight(.medium))
                            .multilineTextAlignment(.center)
                            .frame(maxWidth: 92)
                    }
                    .frame(maxWidth: .infinity)

                    if index < steps.count - 1 {
                        Capsule()
                            .fill(direction.tint.opacity(reduceMotion ? 0.24 : 0.42))
                            .frame(width: 34, height: 2)
                            .padding(.bottom, 26)
                    }
                }
            }
        }
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(.white.opacity(0.08))
        }
        .accessibilityLabel("Proposal builder steps")
    }
}

private enum AACompassAmbition {
    static func description(for value: Int, chinese: Bool) -> String {
        if chinese {
            switch value {
            case 1: return "小型课程项目式文献综合"
            case 2: return "聚焦的探索性分析"
            case 3: return "可执行的本科生研究方案"
            case 4: return "包含可视化或建模的进阶作品集项目"
            default: return "博士研究风格的前沿方案"
            }
        }
        switch value {
        case 1: return "a small class-project style literature synthesis"
        case 2: return "a focused exploratory analysis"
        case 3: return "a feasible undergraduate research proposal"
        case 4: return "an ambitious portfolio project with visualization or modeling"
        default: return "a high-end PhD-style frontier proposal"
        }
    }
}

private struct AACompassScore: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let title: String
    let value: Int
    let symbol: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(title, systemImage: symbol)
                .font(.caption.weight(.medium))
                .foregroundStyle(.secondary)
            scoreValue
            Gauge(value: Double(value), in: 0...100) { EmptyView() }
                .gaugeStyle(.accessoryLinearCapacity)
                .tint(tint)
                .accessibilityHidden(true)
        }
        .padding(15)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 15, style: .continuous))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title), \(value) out of 100")
    }

    @ViewBuilder
    private var scoreValue: some View {
        if reduceMotion {
            Text(value, format: .number)
                .font(.title.weight(.semibold).monospacedDigit())
        } else {
            Text(value, format: .number)
                .font(.title.weight(.semibold).monospacedDigit())
                .contentTransition(.numericText())
        }
    }
}

private struct AAProposalDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.plainText] }

    var text: String

    init(text: String) {
        self.text = text
    }

    init(configuration: ReadConfiguration) throws {
        guard let data = configuration.file.regularFileContents,
              let decoded = String(data: data, encoding: .utf8) else {
            throw CocoaError(.fileReadCorruptFile)
        }
        text = decoded
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: Data(text.utf8))
    }
}

private enum AACompassTheme: String, CaseIterable, Identifiable {
    case ocean
    case iceDynamics
    case solidEarth
    case observations
    case paleoclimate
    case computation

    var id: String { rawValue }

    var title: String {
        switch self {
        case .ocean: "Ocean"
        case .iceDynamics: "Ice dynamics"
        case .solidEarth: "Solid Earth"
        case .observations: "Observations"
        case .paleoclimate: "Paleoclimate"
        case .computation: "Computation"
        }
    }

    var chineseTitle: String {
        switch self {
        case .ocean: "海洋"
        case .iceDynamics: "冰动力学"
        case .solidEarth: "固体地球"
        case .observations: "观测"
        case .paleoclimate: "古气候"
        case .computation: "计算研究"
        }
    }

    var symbol: String {
        switch self {
        case .ocean: "water.waves"
        case .iceDynamics: "mountain.2"
        case .solidEarth: "globe.asia.australia.fill"
        case .observations: "sensor.tag.radiowaves.forward"
        case .paleoclimate: "clock.arrow.circlepath"
        case .computation: "cpu"
        }
    }
}

private enum AACompassEvidence: String, CaseIterable, Identifiable {
    case satellite
    case field
    case model
    case paleoclimate

    var id: String { rawValue }

    var title: String {
        switch self {
        case .satellite: "Satellite"
        case .field: "Field observations"
        case .model: "Models"
        case .paleoclimate: "Paleo records"
        }
    }

    var chineseTitle: String {
        switch self {
        case .satellite: "卫星"
        case .field: "现场观测"
        case .model: "模型"
        case .paleoclimate: "古气候记录"
        }
    }
}

private struct AACompassDirection: Identifiable {
    let id: String
    let title: String
    let theme: AACompassTheme
    let question: String
    let whyNow: String
    let opening: String
    let hypothesis: String
    let uncertaintyNote: String
    let methods: [String]
    let evidence: [AACompassEvidence]
    let regions: [String]
    let impact: Int
    let uncertainty: Int
    let observability: Int
    let timeScale: String
    let tint: Color

    var chartTitle: String {
        switch id {
        case "ocean-heat-pathways": "Ocean heat\npathways"
        case "grounding-line-instability": "Grounding-line\ninstability"
        case "ice-shelf-fracture": "Ice-shelf fracture\nand calving"
        case "paleo-projection-constraints": "Paleo constraints\nfor projections"
        case "solid-earth-feedbacks": "Solid-Earth\nfeedbacks"
        case "subglacial-water": "Subglacial water\nand basal sliding"
        case "ai-assisted-observation": "AI-assisted\nobservation"
        default: title
        }
    }

    var starterQuestions: [String] {
        switch id {
        case "ocean-heat-pathways": [
            "Which Antarctic margins are most exposed to warm-water access under changing winds?",
            "Can satellite-observed thinning be connected to likely ocean-heat pathways?",
            "How does meltwater-driven stratification change warm-water persistence beneath ice shelves?"
        ]
        case "grounding-line-instability": [
            "Which bed geometries make retreat most sensitive to small melt-rate changes?",
            "How do pinning points delay or reorganize grounding-line retreat?",
            "Can InSAR-derived velocity changes provide early signs of buttressing loss?"
        ]
        case "ice-shelf-fracture": [
            "Which surface-hydrology patterns indicate increasing hydrofracture vulnerability?",
            "How much passive shelf area can be lost before grounded ice accelerates?",
            "Can Larsen B-like collapse logic be generalized to other Antarctic shelves?"
        ]
        case "subglacial-water": [
            "How do active subglacial lake drainage events change downstream velocity?",
            "What sensing signatures indicate a switch from distributed to channelized flow?",
            "How should basal hydrology appear in transparent ice-flow simulations?"
        ]
        case "solid-earth-feedbacks": [
            "Where is rapid bedrock uplift most likely to slow grounding-line retreat?",
            "How sensitive are GRACE-derived mass trends to different GIA assumptions?",
            "Can regional GNSS constraints improve ice-sheet projection confidence?"
        ]
        case "paleo-projection-constraints": [
            "Which past warm intervals are most useful analogues for future Antarctic change?",
            "How can paleo records test whether high-end collapse mechanisms are realistic?",
            "What uncertainty remains when sea-level records constrain Antarctic retreat?"
        ]
        case "ai-assisted-observation": [
            "Can a knowledge graph help students navigate Antarctic mechanisms more effectively than a linear PDF?",
            "How can evidence-grounded AI explain uncertainty beside a scientific claim?",
            "Can AI link satellite observations to physical ice-sheet processes without obscuring provenance?"
        ]
        default: [question]
        }
    }

    var gap: String {
        switch id {
        case "ocean-heat-pathways": "Cross-shelf heat transport is difficult to observe directly and hard to represent at the spatial scale that controls cavity access."
        case "grounding-line-instability": "The timing and reversibility of retreat depend on bed topography, basal friction, melt parameterization, and solid-Earth feedbacks."
        case "ice-shelf-fracture": "Models still struggle to predict when fractures connect, when shelves collapse, and how quickly inland glaciers respond."
        case "subglacial-water": "The subglacial system is difficult to observe directly, so models often rely on simplified sliding laws and uncertain hydrological parameters."
        case "solid-earth-feedbacks": "Antarctic mantle viscosity varies in three dimensions, but many models simplify Earth structure or lack enough geodetic constraints."
        case "paleo-projection-constraints": "Paleo sea-level and ice-extent reconstructions have large uncertainties, making it difficult to validate specific model physics."
        case "ai-assisted-observation": "AI tools must remain source-grounded, uncertainty-aware, and connected to real observation and modeling workflows."
        default: uncertaintyNote
        }
    }

    var studentAngle: String {
        switch id {
        case "ocean-heat-pathways": "Build a conceptual or data-driven map linking bathymetric troughs, winds, and glacier-thinning hotspots."
        case "grounding-line-instability": "Compare Thwaites, Pine Island, and an East Antarctic basin to show how bed geometry changes risk."
        case "ice-shelf-fracture": "Create a visual diagnostic that classifies shelves by meltwater ponding, crevasse density, and buttressing importance."
        case "subglacial-water": "Compare distributed and channelized drainage, then explain how each can stabilize or destabilize ice flow."
        case "solid-earth-feedbacks": "Show why the solid Earth is not just a correction term but an active feedback in ice-sheet stability."
        case "paleo-projection-constraints": "Build a Past–Present–Future evidence chain showing what each archive can and cannot prove."
        case "ai-assisted-observation": "Turn the Atlas into a portfolio-quality example of source-grounded scientific reasoning and visual synthesis."
        default: opening
        }
    }

    var chineseSearchTerms: String {
        switch id {
        case "ocean-heat-pathways": "海洋 热量 通道 环南极深层水 冰架"
        case "grounding-line-instability": "接地线 不稳定 海洋冰盖不稳定性 MISI 逆坡床 基岩"
        case "ice-shelf-fracture": "冰架 裂隙 崩解 水力压裂 融水"
        case "paleo-projection-constraints": "古气候 未来 预测 约束 暖期"
        case "solid-earth-feedbacks": "固体地球 基岩 回弹 接地线"
        case "subglacial-water": "冰下水 基底 滑动 冰流"
        case "ai-assisted-observation": "人工智能 AI 机器学习 观测"
        default: ""
        }
    }

    static let samples: [AACompassDirection] = [
        .init(
            id: "ocean-heat-pathways",
            title: "Ocean heat pathways",
            theme: .ocean,
            question: "How does warm Circumpolar Deep Water cross the continental shelf and reach ice-shelf cavities?",
            whyNow: "Ocean access is a central control on basal melting, yet regional pathways remain under-observed.",
            opening: "Resolve the timing and geometry of cross-shelf heat transport, then connect delivery at the cavity mouth to basal melt variability.",
            hypothesis: "Bathymetric troughs and wind-driven circulation create episodic heat-delivery corridors that explain a large share of melt variability.",
            uncertaintyNote: "Test sensitivity to unresolved bathymetry, sparse winter observations, and freshwater-modified stratification.",
            methods: ["Ocean moorings", "AUV surveys", "CTD sections", "Regional models"],
            evidence: [.field, .satellite, .model],
            regions: ["Amundsen Sea", "Totten sector", "Weddell Sea"],
            impact: 94, uncertainty: 92, observability: 58, timeScale: "days → decades", tint: .cyan
        ),
        .init(
            id: "grounding-line-instability",
            title: "Grounding-line instability",
            theme: .iceDynamics,
            question: "When does grounding-line retreat become self-sustaining on retrograde bed topography?",
            whyNow: "Marine ice-sheet instability links bed geometry, ice-shelf buttressing, and ocean forcing; it is one of the highest-impact mechanisms for sea-level projections.",
            opening: "Compare how bed geometry, buttressing loss, and ocean-driven melt organize the threshold between reversible adjustment and sustained retreat.",
            hypothesis: "Retrograde beds with limited pinning support amplify small melt-rate changes into self-sustaining retreat, unless local resistance or rapid uplift interrupts the feedback.",
            uncertaintyNote: "Separate uncertainty in bed and basal friction from uncertainty in ocean forcing, ice-shelf buttressing, and solid-Earth response.",
            methods: ["InSAR velocity", "Satellite altimetry", "Radar sounding", "Ice-sheet models"],
            evidence: [.satellite, .field, .model],
            regions: ["Thwaites Glacier", "Pine Island Glacier", "Wilkes Basin", "Aurora Basin"],
            impact: 96, uncertainty: 88, observability: 64, timeScale: "years → centuries", tint: .mint
        ),
        .init(
            id: "ice-shelf-fracture",
            title: "Ice-shelf fracture and calving",
            theme: .iceDynamics,
            question: "Which combinations of melt, firn state, and structural weakness push an ice shelf toward rapid breakup?",
            whyNow: "Extreme surface-melt events are becoming more consequential while fracture physics remain difficult to scale.",
            opening: "Link observed ponding and crevasse networks to changes in shelf integrity and upstream flow response.",
            hypothesis: "Pre-existing damage geometry controls whether equivalent melt seasons lead to drainage, limited fracture, or cascading breakup.",
            uncertaintyNote: "Separate fracture initiation uncertainty from uncertainty in the grounded-ice response after buttressing loss.",
            methods: ["Optical imagery", "Ice-penetrating radar", "Fracture models", "InSAR velocity"],
            evidence: [.satellite, .field, .model],
            regions: ["Antarctic Peninsula", "Amundsen Sea", "Wilkes Land"],
            impact: 93, uncertainty: 90, observability: 72, timeScale: "hours → years", tint: .blue
        ),
        .init(
            id: "paleo-projection-constraints",
            title: "Paleo constraints for future projections",
            theme: .paleoclimate,
            question: "Which past warm periods most strongly constrain the sensitivity of marine-based Antarctic ice?",
            whyNow: "The observational era is short compared with the response time of the ice sheet.",
            opening: "Build like-for-like comparisons between geological evidence and model states rather than relying on global sea-level targets alone.",
            hypothesis: "Regional retreat fingerprints provide stronger constraints on process combinations than continental-scale mass-loss totals.",
            uncertaintyNote: "Propagate age-model, preservation, and proxy-interpretation uncertainty into model-data comparison.",
            methods: ["Sediment cores", "Exposure dating", "Proxy synthesis", "Ensemble models"],
            evidence: [.paleoclimate, .field, .model],
            regions: ["Ross Sea", "Weddell Sea", "Wilkes Land"],
            impact: 91, uncertainty: 86, observability: 48, timeScale: "centuries → millennia", tint: .orange
        ),
        .init(
            id: "solid-earth-feedbacks",
            title: "Solid-Earth feedbacks",
            theme: .solidEarth,
            question: "Where can rapid bedrock uplift meaningfully slow grounding-line retreat?",
            whyNow: "Earth structure varies strongly beneath Antarctica and changes local relative sea level.",
            opening: "Combine geodetic observations with ice–Earth coupling to identify regions where rebound is dynamically relevant.",
            hypothesis: "Low-viscosity mantle sectors produce fast uplift that measurably reduces retreat under intermediate forcing.",
            uncertaintyNote: "Distinguish mantle-structure uncertainty from uncertainty in past loading and bed geometry.",
            methods: ["GNSS", "Seismic inversion", "GIA models", "Coupled ice models"],
            evidence: [.field, .model, .satellite],
            regions: ["Amundsen Sea", "Antarctic Peninsula", "East Antarctica"],
            impact: 88, uncertainty: 82, observability: 61, timeScale: "years → millennia", tint: .green
        ),
        .init(
            id: "subglacial-water",
            title: "Subglacial water and basal sliding",
            theme: .observations,
            question: "How does evolving subglacial drainage reorganize fast ice flow?",
            whyNow: "Basal water is hard to observe directly but can rapidly alter the resistance beneath ice streams.",
            opening: "Detect hydrologic events across sensors and test whether they precede coherent velocity changes.",
            hypothesis: "Network connectivity, rather than total stored water alone, controls the largest transient sliding responses.",
            uncertaintyNote: "Test for observational aliasing and competing explanations such as tidal or ocean-driven forcing.",
            methods: ["Radar sounding", "GNSS", "InSAR", "Hydrology models"],
            evidence: [.field, .satellite, .model],
            regions: ["Whillans Ice Stream", "Thwaites Glacier", "Recovery Glacier"],
            impact: 84, uncertainty: 85, observability: 54, timeScale: "hours → decades", tint: .indigo
        ),
        .init(
            id: "ai-assisted-observation",
            title: "AI-assisted Antarctic observation",
            theme: .computation,
            question: "How can machine learning expose change without obscuring uncertainty or physical meaning?",
            whyNow: "Earth-observation archives are growing faster than expert annotation and synthesis capacity.",
            opening: "Design an auditable detection pipeline that pairs every learned signal with provenance, uncertainty, and physical validation.",
            hypothesis: "Physics-informed representations improve transfer across sensors and regions while reducing false change detections.",
            uncertaintyNote: "Report domain shift, label uncertainty, failure cases, and sensitivity to preprocessing alongside performance.",
            methods: ["Self-supervision", "Change detection", "Uncertainty calibration", "Expert review"],
            evidence: [.satellite, .field, .model],
            regions: ["Continent-wide", "Amundsen Sea", "Antarctic Peninsula"],
            impact: 79, uncertainty: 78, observability: 88, timeScale: "days → years", tint: .purple
        )
    ]
}

#Preview {
    CompassView()
        .environment(AppModel())
        .frame(width: 1_180, height: 860)
}
