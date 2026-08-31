import AppKit
import Combine
import SwiftUI

struct VisualizerView: View {
    @Environment(AppModel.self) private var appModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var selectedStory: AAVisualizerStory = .iceSheetStability
    @State private var selectedLens: AAVisualizerLens = .present
    // The source experience begins in a calm, explorable overview. A beat is only
    // revealed after the reader presses Begin Story or chooses a glowing node.
    @State private var currentBeat = -1
    @State private var isPlaying = false
    @State private var copyFeedback = false

    private let playbackClock = Timer.publish(every: 1.15, on: .main, in: .common).autoconnect()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                header
                controls
                storyboard
                timeline
                contextNote
            }
            .padding(28)
            .frame(maxWidth: 1_280, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .background {
            LinearGradient(
                colors: [
                    Color(nsColor: .windowBackgroundColor),
                    Color.accentColor.opacity(0.055),
                    Color(nsColor: .windowBackgroundColor)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()
        }
        .onChange(of: selectedStory) { _, _ in resetPlayback() }
        .onChange(of: selectedLens) { _, _ in resetPlayback() }
        .onChange(of: appModel.searchSubmissionToken) { _, _ in applySharedSearch() }
        .onReceive(playbackClock) { _ in advancePlayback() }
        .navigationTitle(appModel.text("Scientific Stories", "科学故事"))
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 18) {
            Image(systemName: "sparkles.rectangle.stack")
                .font(.system(size: 28, weight: .semibold))
                .foregroundStyle(.tint)
                .frame(width: 52, height: 52)
                .background(.tint.opacity(0.12), in: RoundedRectangle(cornerRadius: 14))
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 5) {
                Text(appModel.text("Scientific Stories", "科学故事"))
                    .font(.largeTitle.weight(.semibold))
                Text(appModel.text(
                    "Move through a curated chain of mechanisms and evidence, one beat at a time.",
                    "沿着精选的机制与证据链，逐步推进科学叙事。"
                ))
                    .font(.title3)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var controls: some View {
        HStack(spacing: 18) {
            Picker(appModel.text("Story", "故事"), selection: $selectedStory) {
                ForEach(filteredStories) { story in
                    Text(appModel.text(story.title, story.chineseTitle)).tag(story)
                }
            }
            .pickerStyle(.menu)
            .frame(maxWidth: 320)

            if filteredStories.isEmpty {
                Label(appModel.text("No matching story", "没有匹配的故事"), systemImage: "magnifyingglass")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }

            Picker(appModel.text("Lens", "视角"), selection: $selectedLens) {
                ForEach(AAVisualizerLens.allCases) { lens in
                    Text(appModel.text(lens.title, lens.chineseTitle)).tag(lens)
                }
            }
            .pickerStyle(.segmented)
            .frame(maxWidth: 360)

            Spacer(minLength: 12)

            ControlGroup {
                Button(action: beginOrTogglePlayback) {
                    Label(
                        playbackLabel,
                        systemImage: isPlaying ? "pause.fill" : "play.fill"
                    )
                }
                .keyboardShortcut(.space, modifiers: [])
                .help(isPlaying ? appModel.text("Pause the story", "暂停故事") : appModel.text("Reveal the story one beat at a time", "逐个展开故事节点"))

                Button(action: resetPlayback) {
                    Label(appModel.text("Reset", "重置"), systemImage: "backward.end.fill")
                }
                .help(appModel.text("Return to the story overview", "返回故事概览"))

                Button(action: copyStory) {
                    Label(
                        copyFeedback ? appModel.text("Copied", "已复制") : appModel.text("Copy Story", "复制故事"),
                        systemImage: copyFeedback ? "checkmark" : "doc.on.doc"
                    )
                }
                .help(appModel.text("Copy the selected scientific chain for notes or slides", "复制当前科学链路到笔记或幻灯片"))
            }
        }
        .padding(14)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private var storyboard: some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .top, spacing: 18) {
                storyMap
                    .frame(minWidth: 560, minHeight: 420)
                beatInspector
                    .frame(width: 300)
            }

            VStack(spacing: 18) {
                storyMap
                    .frame(minHeight: 390)
                beatInspector
            }
        }
    }

    private var storyMap: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(.ultraThinMaterial)

            LinearGradient(
                colors: [Color.accentColor.opacity(0.13), .clear, Color.cyan.opacity(0.08)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))

            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 7) {
                    Text(appModel.text(selectedLens.kicker, selectedLens.chineseKicker).uppercased())
                        .font(.caption.weight(.semibold))
                        .tracking(1.3)
                        .foregroundStyle(.tint)
                    Text(appModel.text(selectedStory.title, selectedStory.chineseTitle))
                        .font(.system(.title, design: .rounded, weight: .semibold))
                    Text(selectedStory.summary(for: selectedLens))
                        .font(.body)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                AAVisualizerPathView(
                    beats: storyBeats,
                    activeIndex: currentBeat,
                    isPlaying: isPlaying,
                    onSelect: selectBeat
                )
                .frame(maxWidth: .infinity, maxHeight: .infinity)

                HStack(spacing: 9) {
                    Image(systemName: activeBeat?.symbol ?? "sparkles")
                        .foregroundStyle(.tint)
                    Text(activeBeat?.message ?? appModel.text(
                        "Begin the story to reveal each mechanism, or choose any glowing node to inspect its evidence.",
                        "开始故事以逐步展开机制，或直接选择任一发光节点查看其证据。"
                    ))
                        .font(.headline)
                        .id(activeBeat?.id ?? "story-overview")
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 11)
                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
                .animation(beatAnimation, value: currentBeat)
            }
            .padding(24)
        }
        .overlay {
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .strokeBorder(.white.opacity(0.10))
        }
    }

    private var beatInspector: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                if currentBeat >= 0 {
                    Label(
                        appModel.text(
                            "Beat \(currentBeat + 1) of \(storyBeats.count)",
                            "第 \(currentBeat + 1) 个节点，共 \(storyBeats.count) 个"
                        ),
                        systemImage: "waveform.path.ecg"
                    )
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                } else {
                    Label(appModel.text("Story overview", "故事概览"), systemImage: "sparkles")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text(appModel.text(selectedLens.title, selectedLens.chineseTitle))
                    .font(.caption.weight(.medium))
                    .padding(.horizontal, 9)
                    .padding(.vertical, 4)
                    .background(.tint.opacity(0.12), in: Capsule())
            }

            if let activeBeat {
                VStack(alignment: .leading, spacing: 7) {
                    Text(activeBeat.title)
                        .font(.title2.weight(.semibold))
                    Text(activeBeat.explanation(for: selectedLens))
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Divider()

                LabeledContent(appModel.text("Evidence", "证据")) {
                    Label(activeBeat.evidence, systemImage: "checkmark.seal")
                        .multilineTextAlignment(.trailing)
                }

                LabeledContent(appModel.text("System", "系统")) {
                    Text(activeBeat.system)
                        .foregroundStyle(.secondary)
                }

                Spacer(minLength: 8)

                VStack(alignment: .leading, spacing: 7) {
                    Label(appModel.text("Speaker note", "讲述提示"), systemImage: "text.bubble")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    Text(activeBeat.speakerNote)
                        .font(.callout)
                        .textSelection(.enabled)
                }
                .padding(12)
                .background(.quaternary, in: RoundedRectangle(cornerRadius: 12))
            } else {
                VStack(alignment: .leading, spacing: 10) {
                    Text(appModel.text(selectedStory.title, selectedStory.chineseTitle))
                        .font(.title2.weight(.semibold))
                    Text(selectedStory.summary(for: selectedLens))
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                    Divider()
                    Label(appModel.text(
                        "Press Begin Story for the timed explanation, or select a node to jump directly to its evidence card.",
                        "按“开始故事”按节奏讲述，或直接选择节点跳到对应证据卡片。"
                    ), systemImage: "cursorarrow.click")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                }
                .padding(12)
                .background(.quaternary, in: RoundedRectangle(cornerRadius: 12))
                Spacer(minLength: 8)
            }
        }
        .padding(20)
        .frame(maxHeight: .infinity, alignment: .top)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(.white.opacity(0.08))
        }
        .animation(beatAnimation, value: currentBeat)
    }

    private var timeline: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label(appModel.text("Storyboard", "故事板"), systemImage: "timeline.selection")
                    .font(.headline)
                Spacer()
                ProgressView(value: Double(max(0, currentBeat + 1)), total: Double(storyBeats.count))
                    .frame(width: 150)
                    .accessibilityLabel(appModel.text("Story progress", "故事进度"))
            }

            HStack(alignment: .top, spacing: 10) {
                ForEach(Array(storyBeats.enumerated()), id: \.element.id) { index, beat in
                    Button {
                        selectBeat(index)
                    } label: {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Image(systemName: beat.symbol)
                                Spacer()
                                Text(String(format: "%02d", index + 1))
                                    .font(.caption.monospacedDigit())
                                    .foregroundStyle(.secondary)
                            }
                            Text(beat.title)
                                .font(.callout.weight(.medium))
                                .lineLimit(2)
                                .multilineTextAlignment(.leading)
                        }
                        .frame(maxWidth: .infinity, minHeight: 72, alignment: .topLeading)
                        .padding(12)
                        .background(
                            index == currentBeat ? AnyShapeStyle(Color.accentColor.opacity(0.16)) : AnyShapeStyle(.quaternary),
                            in: RoundedRectangle(cornerRadius: 12)
                        )
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(appModel.text("Beat \(index + 1)", "第 \(index + 1) 个节点") + ", \(beat.title)")
                    .accessibilityAddTraits(index == currentBeat ? .isSelected : [])
                }
            }
        }
    }

    private var contextNote: some View {
        Label(
            appModel.text(
                "Curated from mechanisms discussed in the included review paper. This is an explanatory storyboard, not a raw-data simulation.",
                "内容依据内置综述论文中的机制整理。这是解释性故事板，并非原始数据模拟。"
            ),
            systemImage: "info.circle"
        )
        .font(.footnote)
        .foregroundStyle(.secondary)
    }

    private var activeBeat: AAVisualizerBeat? {
        guard currentBeat >= 0, storyBeats.indices.contains(currentBeat) else { return nil }
        return storyBeats[currentBeat]
    }

    private var storyBeats: [AAVisualizerBeat] {
        selectedStory.beats(for: selectedLens)
    }

    private var playbackLabel: String {
        if isPlaying { return appModel.text("Pause", "暂停") }
        if currentBeat < 0 { return appModel.text("Begin Story", "开始故事") }
        if currentBeat >= storyBeats.count - 1 { return appModel.text("Replay Story", "重新播放") }
        return appModel.text("Continue", "继续")
    }

    private var beatAnimation: Animation? {
        reduceMotion ? nil : .smooth(duration: 0.48)
    }

    private var filteredStories: [AAVisualizerStory] {
        let query = appModel.searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return AAVisualizerStory.allCases }
        return AAVisualizerStory.allCases.filter { story in
            let searchable = [
                story.title,
                story.chineseTitle,
                story.searchTerms,
                story.summary(for: .past),
                story.summary(for: .present),
                story.summary(for: .future),
                AAVisualizerLens.allCases.flatMap { story.beats(for: $0) }
                    .map { "\($0.title) \($0.message) \($0.evidence)" }
                    .joined(separator: " ")
            ].joined(separator: " ")
            return searchable.localizedCaseInsensitiveContains(query)
        }
    }

    private func beginOrTogglePlayback() {
        withAnimation(beatAnimation) {
            if isPlaying {
                isPlaying = false
                return
            }
            if currentBeat < 0 || currentBeat >= storyBeats.count - 1 {
                currentBeat = 0
            }
            isPlaying = true
        }
    }

    private func resetPlayback() {
        withAnimation(beatAnimation) {
            isPlaying = false
            currentBeat = -1
        }
    }

    private func selectBeat(_ index: Int) {
        guard storyBeats.indices.contains(index) else { return }
        withAnimation(beatAnimation) {
            currentBeat = index
            isPlaying = false
        }
    }

    private func copyStory() {
        let heading = "\(selectedStory.title) — \(selectedLens.title) lens"
        let lines = storyBeats.enumerated().map { index, beat in
            "\(index + 1). \(beat.title)\n   \(beat.message)\n   Evidence: \(beat.evidence)"
        }
        let text = ([heading, selectedStory.summary(for: selectedLens)] + lines).joined(separator: "\n\n")
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)

        withAnimation(beatAnimation) { copyFeedback = true }
        Task { @MainActor in
            try? await Task.sleep(for: .seconds(1.6))
            guard !Task.isCancelled else { return }
            withAnimation(beatAnimation) { copyFeedback = false }
        }
    }

    private func advancePlayback() {
        guard isPlaying else { return }
        if currentBeat < storyBeats.count - 1 {
            withAnimation(beatAnimation) { currentBeat += 1 }
        } else {
            isPlaying = false
        }
    }

    private func applySharedSearch() {
        guard let match = filteredStories.first, !filteredStories.contains(selectedStory) else { return }
        selectedStory = match
    }
}

private struct AAVisualizerPathView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let beats: [AAVisualizerBeat]
    let activeIndex: Int
    let isPlaying: Bool
    let onSelect: (Int) -> Void
    @State private var ambientPulse = false

    var body: some View {
        GeometryReader { proxy in
            let positions = beatPositions(in: proxy.size)

            ZStack {
                AAVisualizerConnectorShape(points: beats.map(\.relativePosition))
                    .stroke(
                        Color.secondary.opacity(0.28),
                        style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round)
                    )
                    .accessibilityHidden(true)

                AAVisualizerConnectorShape(points: beats.map(\.relativePosition))
                    .trim(from: 0, to: connectionProgress)
                    .stroke(
                        LinearGradient(colors: [.cyan, .accentColor], startPoint: .leading, endPoint: .trailing),
                        style: StrokeStyle(lineWidth: 5, lineCap: .round, lineJoin: .round)
                    )
                    .shadow(color: .accentColor.opacity(isPlaying ? 0.32 : 0.16), radius: isPlaying ? 10 : 5)
                    .animation(reduceMotion ? nil : .smooth(duration: 0.62), value: connectionProgress)
                .accessibilityHidden(true)

                ForEach(Array(beats.enumerated()), id: \.element.id) { index, beat in
                    let isRevealed = index <= activeIndex
                    let isActive = index == activeIndex
                    Button {
                        onSelect(index)
                    } label: {
                        VStack(spacing: 7) {
                            Image(systemName: beat.symbol)
                                .font(.system(size: isActive ? 22 : 17, weight: .semibold))
                                .frame(width: isActive ? 54 : 44, height: isActive ? 54 : 44)
                                .foregroundStyle(isRevealed ? Color.white : beat.kindColor.opacity(0.86))
                                .background(
                                    isRevealed ? AnyShapeStyle(beat.kindColor.gradient) : AnyShapeStyle(beat.kindColor.opacity(0.22)),
                                    in: Circle()
                                )
                                .overlay(Circle().stroke(.white.opacity(isActive ? 0.70 : 0.24), lineWidth: isActive ? 2.5 : 1.2))
                                .shadow(color: beat.kindColor.opacity(isActive ? 0.55 : (ambientPulse && !reduceMotion ? 0.27 : 0.14)), radius: isActive ? 18 : 9)
                                .scaleEffect(isActive && isPlaying && !reduceMotion ? 1.075 : (ambientPulse && !isRevealed && !reduceMotion ? 1.025 : 1))

                            Text(beat.shortTitle)
                                .font(.caption.weight(isActive ? .semibold : .regular))
                                .foregroundStyle(isRevealed ? .primary : .secondary)
                                .multilineTextAlignment(.center)
                                .lineLimit(2)
                                .frame(width: 110)
                        }
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .position(positions[index])
                    .accessibilityLabel("Beat \(index + 1): \(beat.title)")
                    .accessibilityAddTraits(isActive ? .isSelected : [])
                }
            }
            .animation(reduceMotion ? nil : .smooth(duration: 0.45), value: activeIndex)
            .animation(reduceMotion ? nil : .smooth(duration: 0.30), value: isPlaying)
            .onAppear {
                guard !reduceMotion else { return }
                withAnimation(.easeInOut(duration: 2.4).repeatForever(autoreverses: true)) {
                    ambientPulse = true
                }
            }
        }
    }

    private var connectionProgress: CGFloat {
        guard beats.count > 1 else { return activeIndex >= 0 ? 1 : 0 }
        return CGFloat(max(0, min(activeIndex, beats.count - 1))) / CGFloat(beats.count - 1)
    }

    private func beatPositions(in size: CGSize) -> [CGPoint] {
        beats.map { beat in
            CGPoint(
                x: max(54, min(size.width - 54, size.width * beat.relativePosition.x)),
                y: max(54, min(size.height - 54, size.height * beat.relativePosition.y))
            )
        }
    }
}

private struct AAVisualizerConnectorShape: Shape {
    let points: [CGPoint]

    func path(in rect: CGRect) -> Path {
        guard !points.isEmpty else { return Path() }
        let renderedPoints = points.map { point in
            CGPoint(
                x: max(rect.minX + 54, min(rect.maxX - 54, rect.minX + rect.width * point.x)),
                y: max(rect.minY + 54, min(rect.maxY - 54, rect.minY + rect.height * point.y))
            )
        }
        var path = Path()
        path.move(to: renderedPoints[0])
        for point in renderedPoints.dropFirst() {
            path.addLine(to: point)
        }
        return path
    }
}

private enum AAVisualizerLens: String, CaseIterable, Identifiable {
    case past
    case present
    case future

    var id: String { rawValue }
    var title: String { rawValue.capitalized }

    var chineseTitle: String {
        switch self {
        case .past: "过去"
        case .present: "现在"
        case .future: "未来"
        }
    }

    var kicker: String {
        switch self {
        case .past: "Evidence from past warm worlds"
        case .present: "Mechanisms observed today"
        case .future: "Questions that shape projections"
        }
    }

    var chineseKicker: String {
        switch self {
        case .past: "来自过去暖期的证据"
        case .present: "今天正在观测的机制"
        case .future: "塑造未来预测的问题"
        }
    }
}

private enum AAVisualizerStory: String, CaseIterable, Identifiable {
    case iceSheetStability
    case oceanHeatPathways
    case hydrofracture
    case solidEarthFeedbacks

    var id: String { rawValue }

    var title: String {
        switch self {
        case .iceSheetStability: "Ice Sheet Stability"
        case .oceanHeatPathways: "Ocean Heat Pathways"
        case .hydrofracture: "Hydrofracture & Ice Cliff Risk"
        case .solidEarthFeedbacks: "Solid Earth Feedbacks"
        }
    }

    var chineseTitle: String {
        switch self {
        case .iceSheetStability: "冰盖稳定性"
        case .oceanHeatPathways: "海洋热量通道"
        case .hydrofracture: "水力压裂与冰崖风险"
        case .solidEarthFeedbacks: "固体地球反馈"
        }
    }

    var searchTerms: String {
        switch self {
        case .iceSheetStability: "冰盖 稳定性 海洋 冰架 接地线 模型 约束"
        case .oceanHeatPathways: "海洋 热量 暖水 环流 冰腔 淡水"
        case .hydrofracture: "水力压裂 表面融化 积水 裂隙 冰架 支撑"
        case .solidEarthFeedbacks: "固体地球 基岩 回弹 相对海平面 稳定"
        }
    }

    func summary(for lens: AAVisualizerLens) -> String {
        let framing: String
        switch lens {
        case .past: framing = "Read the chain through paleoclimate constraints and earlier retreat episodes."
        case .present: framing = "Follow the observations and mechanisms shaping Antarctic change now."
        case .future: framing = "See where uncertain processes widen the range of future outcomes."
        }
        return "\(baseSummary) \(framing)"
    }

    private var baseSummary: String {
        switch self {
        case .iceSheetStability:
            "Antarctic stability emerges from ocean forcing, ice-shelf support, grounding-line geometry, and feedbacks across the Earth system."
        case .oceanHeatPathways:
            "Heat reaches vulnerable ice shelves through a changing chain of winds, circulation, bathymetry, and cavity exchange."
        case .hydrofracture:
            "Surface meltwater can exploit fractures, weaken ice shelves, and alter the resistance felt by grounded ice upstream."
        case .solidEarthFeedbacks:
            "Bedrock shape, mantle response, and relative sea-level change can either amplify or resist ice-sheet retreat."
        }
    }

    /// Each lens owns a distinct causal chain and spatial arrangement, as in the
    /// original Story Engine. This is intentionally not a copy-only filter over a
    /// single generic chain.
    func beats(for lens: AAVisualizerLens) -> [AAVisualizerBeat] {
        switch (self, lens) {
        case (.iceSheetStability, .past):
            makeBeats([
                ("Past Warm Periods", "Paleo", 0.18, 0.37, "Past warm intervals show that Antarctica can retreat beyond the satellite record.", "Marine sediments and sea-level archives"),
                ("Marine-based Ice", "Ice dynamics", 0.40, 0.49, "Large sectors rest below sea level and are sensitive to ocean and grounding-line feedbacks.", "Bed topography and paleo reconstruction"),
                ("Retreat Episodes", "Ice dynamics", 0.62, 0.42, "Earlier retreat gives boundary conditions for testing instability mechanisms.", "Shelf cores and geomorphic records"),
                ("Model Constraints", "Model", 0.82, 0.58, "Paleo records constrain projections by showing what the ice sheet has done before.", "Model-data comparison")
            ])
        case (.iceSheetStability, .present):
            makeBeats([
                ("Ocean Heat", "Ocean", 0.16, 0.54, "Warm Circumpolar Deep Water can reach cavities beneath vulnerable ice shelves.", "Moorings, CTD, and ocean reanalysis"),
                ("Shelf Thinning", "Ice shelf", 0.38, 0.42, "Basal melt thins shelves and weakens buttressing.", "Altimetry and melt-rate estimates"),
                ("Grounding Retreat", "Ice dynamics", 0.60, 0.51, "Grounding-line retreat links shelf thinning to inland discharge.", "InSAR grounding-zone mapping"),
                ("Sea-level Risk", "Impact", 0.80, 0.40, "Antarctica remains a major uncertainty in future sea-level projections.", "Projection ensembles")
            ])
        case (.iceSheetStability, .future):
            makeBeats([
                ("Forcing Pathways", "Forcing", 0.18, 0.46, "Future winds, stratification, and meltwater feedbacks control ocean heat access.", "Climate and ocean scenarios"),
                ("Buttressing Loss", "Ice shelf", 0.40, 0.34, "Thinner shelves provide less back stress to inland ice.", "Stress-balance models"),
                ("Instability Thresholds", "Instability", 0.62, 0.50, "MISI-like retreat may become hard to reverse on retrograde beds.", "Ice-sheet sensitivity tests"),
                ("Uncertainty Range", "Uncertainty", 0.82, 0.35, "Projection spread depends on poorly constrained process coupling.", "Uncertainty quantification")
            ])

        case (.oceanHeatPathways, .past):
            makeBeats([
                ("Shelf Break", "Ocean", 0.18, 0.44, "Bathymetric gateways shaped earlier continental-shelf heat access.", "Bathymetry and sediment archives"),
                ("Warm Intervals", "Paleo", 0.40, 0.34, "Past warm periods offer clues about persistent ocean forcing.", "Paleoceanographic proxies"),
                ("Melt Archive", "Paleo", 0.62, 0.52, "Marine records can preserve signals of grounding-zone retreat and shelf melt.", "Marine sediment cores"),
                ("Analog Limits", "Uncertainty", 0.82, 0.40, "Ancient states help, but no past interval maps perfectly onto modern forcing.", "Proxy uncertainty")
            ])
        case (.oceanHeatPathways, .present):
            makeBeats([
                ("CDW Intrusion", "Ocean", 0.18, 0.48, "Warm water follows troughs toward vulnerable shelves.", "Moorings and CTD sections"),
                ("Cavity Circulation", "Ocean", 0.40, 0.36, "Sub-ice circulation controls where basal melting concentrates.", "Ocean models"),
                ("Basal Melt", "Ice shelf", 0.62, 0.50, "Basal melt thins shelves and changes stress transmission.", "Altimetry and ice-shelf mass balance"),
                ("Discharge Signal", "Observation", 0.82, 0.38, "Velocity and elevation signals connect ocean forcing to inland response.", "InSAR and altimetry")
            ])
        case (.oceanHeatPathways, .future):
            makeBeats([
                ("Wind Shift", "Forcing", 0.18, 0.43, "Changing winds can reorganize shelf-edge heat access.", "Climate projections"),
                ("Freshwater Feedback", "Feedback", 0.40, 0.56, "Meltwater freshening can change stratification and circulation pathways.", "Coupled ocean-ice models"),
                ("Persistent Melt", "Risk", 0.62, 0.40, "Sustained heat delivery can keep shelves in a thinning regime.", "Scenario experiments"),
                ("Observation Need", "Observation", 0.82, 0.52, "Targeted observations are needed to reduce pathway uncertainty.", "Field campaigns and AUVs")
            ])

        case (.hydrofracture, .past):
            makeBeats([
                ("Collapse Analog", "Paleo", 0.18, 0.44, "Past and recent shelf collapses provide analogs for rapid structural failure.", "Larsen B and paleo shelf records"),
                ("Surface Melt", "Atmosphere", 0.40, 0.34, "Meltwater loading can deepen crevasses through hydrofracture.", "Surface melt mapping"),
                ("Shelf Breakup", "Fracture", 0.62, 0.52, "Connected fractures can convert a shelf into fragmented ice.", "Optical and SAR imagery"),
                ("Response Lag", "Ice dynamics", 0.82, 0.40, "Inland acceleration can follow after buttressing is removed.", "Post-collapse velocity change")
            ])
        case (.hydrofracture, .present):
            makeBeats([
                ("Ponding", "Hydrology", 0.18, 0.46, "Surface lakes and slush zones mark vulnerable shelves.", "Optical imagery and climate data"),
                ("Crevasse Fields", "Fracture", 0.40, 0.34, "Crevasse density shows where fracture pathways may connect.", "SAR and high-resolution imagery"),
                ("Buttressing Map", "Ice shelf", 0.62, 0.51, "Passive and active shelf zones differ in their dynamic importance.", "Stress-balance modeling"),
                ("MICI Debate", "Instability", 0.82, 0.39, "Marine ice-cliff instability is a high-end mechanism with large uncertainty.", "Model comparison")
            ])
        case (.hydrofracture, .future):
            makeBeats([
                ("Warming Summers", "Atmosphere", 0.18, 0.44, "More frequent melt seasons can increase surface-water loading.", "Climate projections"),
                ("Shelf Collapse", "Risk", 0.40, 0.55, "Rapid shelf loss removes back stress from tributary glaciers.", "Collapse scenario experiments"),
                ("Cliff Exposure", "Instability", 0.62, 0.39, "Tall exposed ice cliffs may fail rapidly in some model formulations.", "MICI sensitivity tests"),
                ("Constraint Need", "Observation", 0.82, 0.52, "Future risk depends on better fracture physics and shelf-strength constraints.", "Observation and modeling")
            ])

        case (.solidEarthFeedbacks, .past):
            makeBeats([
                ("Ice Load Memory", "Feedback", 0.18, 0.44, "Past ice loading still shapes modern bedrock motion.", "GIA theory and paleo ice history"),
                ("Raised Shores", "Paleo", 0.40, 0.34, "Relative sea-level markers help constrain uplift and former ice extent.", "Geomorphic records"),
                ("Mantle Structure", "Solid Earth", 0.62, 0.52, "Viscosity variations govern how fast bedrock responds.", "Seismology and GIA models"),
                ("Model Input", "Model", 0.82, 0.40, "Past constraints improve present mass-balance corrections.", "Model calibration")
            ])
        case (.solidEarthFeedbacks, .present):
            makeBeats([
                ("GRACE Signal", "Observation", 0.18, 0.45, "Gravity change combines ice mass loss and solid-Earth motion.", "GRACE / GRACE-FO"),
                ("GNSS Uplift", "Solid Earth", 0.40, 0.34, "Stations measure bedrock motion that helps separate ice and Earth signals.", "GPS/GNSS networks"),
                ("GIA Correction", "Observation", 0.62, 0.52, "Mass trends need solid-Earth correction to avoid biased estimates.", "GIA model ensembles"),
                ("Grounding Feedback", "Feedback", 0.82, 0.40, "Bedrock uplift and local sea-level fall can alter retreat dynamics.", "Coupled ice-solid Earth models")
            ])
        case (.solidEarthFeedbacks, .future):
            makeBeats([
                ("Bedrock Uplift", "Feedback", 0.18, 0.46, "Ice loss can trigger uplift that changes grounding-zone geometry.", "Coupled sea-level models"),
                ("Relative Sea Level", "Feedback", 0.40, 0.31, "Local sea-level fall may slow retreat in some settings.", "Sea-level fingerprint models"),
                ("3D Earth Structure", "Uncertainty", 0.62, 0.49, "Viscosity varies strongly across Antarctica, affecting feedback timing.", "Seismology and geodesy"),
                ("Coupled Projection", "Model", 0.82, 0.35, "Future projections need ice, ocean, atmosphere, and solid-Earth coupling.", "Coupled model development")
            ])
        }
    }

    private func makeBeats(_ rows: [(String, String, CGFloat, CGFloat, String, String)]) -> [AAVisualizerBeat] {
        rows.map { row in
            AAVisualizerBeat(
                title: row.0,
                kind: row.1,
                x: row.2,
                y: row.3,
                message: row.4,
                evidence: row.5
            )
        }
    }
}

private struct AAVisualizerBeat: Identifiable {
    let id: String
    let title: String
    let shortTitle: String
    let symbol: String
    let system: String
    let message: String
    let evidence: String
    let speakerNote: String
    let relativePosition: CGPoint

    init(title: String, kind: String, x: CGFloat, y: CGFloat, message: String, evidence: String) {
        self.id = "\(kind)|\(title)"
        self.title = title
        self.shortTitle = title
        self.symbol = Self.symbol(for: kind)
        self.system = kind
        self.message = message
        self.evidence = evidence
        self.speakerNote = "Evidence layer: \(evidence). Use this beat to connect the mechanism to the next link in the chain."
        self.relativePosition = CGPoint(x: x, y: y)
    }

    var kindColor: Color {
        switch system {
        case "Ocean": Color(red: 0.31, green: 0.64, blue: 0.95)
        case "Ice shelf": Color(red: 0.72, green: 0.95, blue: 1.0)
        case "Ice dynamics": Color(red: 0.48, green: 0.87, blue: 0.95)
        case "Observation": Color(red: 0.58, green: 0.46, blue: 0.80)
        case "Atmosphere": Color(red: 0.65, green: 0.78, blue: 0.91)
        case "Hydrology": Color(red: 0.35, green: 0.84, blue: 1.0)
        case "Fracture", "Risk": Color(red: 1.0, green: 0.54, blue: 0.40)
        case "Instability": Color(red: 1.0, green: 0.69, blue: 0.40)
        case "Impact", "Model": Color(red: 0.80, green: 0.71, blue: 0.86)
        case "Forcing", "Paleo", "Uncertainty": Color(red: 0.96, green: 0.78, blue: 0.37)
        case "Solid Earth": Color(red: 0.76, green: 0.60, blue: 0.42)
        case "Feedback": Color(red: 0.61, green: 0.80, blue: 0.40)
        default: Color.accentColor
        }
    }

    private static func symbol(for kind: String) -> String {
        switch kind {
        case "Ocean": "water.waves"
        case "Ice shelf": "rectangle.compress.vertical"
        case "Ice dynamics": "arrow.down.right"
        case "Observation": "eye"
        case "Atmosphere": "cloud.sun"
        case "Hydrology": "drop"
        case "Fracture": "bolt.horizontal"
        case "Instability": "exclamationmark.triangle"
        case "Impact": "chart.line.uptrend.xyaxis"
        case "Forcing": "wind"
        case "Uncertainty": "questionmark.circle"
        case "Solid Earth": "mountain.2"
        case "Feedback": "arrow.triangle.2.circlepath"
        case "Paleo": "clock.arrow.circlepath"
        case "Model": "cube.transparent"
        case "Risk": "exclamationmark.shield"
        default: "circle.hexagongrid"
        }
    }

    func explanation(for lens: AAVisualizerLens) -> String {
        switch lens {
        case .past: "Past records help test when and how this mechanism operated: \(message)"
        case .present: message
        case .future: "Future projections must represent this link and its uncertainty: \(message)"
        }
    }
}

#Preview {
    VisualizerView()
        .environment(AppModel())
        .frame(width: 1_180, height: 820)
}
