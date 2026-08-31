import AppKit
import Darwin
import SwiftUI

struct UniverseView: View {
    private enum LoadState {
        case idle
        case loading
        case loaded(ResearchUniverse)
        case failed(String)
    }

    @State private var loadState: LoadState = .idle
    @SceneStorage("universe.selected-node-id") private var selectedNodeID = UniverseNode.core.id
    @SceneStorage("universe.focused-node-id") private var focusedNodeID = ""
    @SceneStorage("universe.graph-scale") private var graphScale = 1.0
    @SceneStorage("universe.depth-enabled") private var isDepthEnabled = false
    @State private var backgroundImage: NSImage?
    @State private var pulsingNodeID: String?
    @State private var pendingFocusTask: Task<Void, Never>?

    @Environment(AppModel.self) private var appModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private let onOpenEvidence: ((ResearchTopic) -> Void)?

    init(onOpenEvidence: ((ResearchTopic) -> Void)? = nil) {
        self.onOpenEvidence = onOpenEvidence
    }

    var body: some View {
        ZStack {
            Color(red: 0.01, green: 0.035, blue: 0.07)
                .ignoresSafeArea()

            switch loadState {
            case .idle, .loading:
                ProgressView(appModel.text("Charting the research universe…", "正在绘制研究宇宙…"))
                    .controlSize(.large)
                    .tint(.white)
                    .foregroundStyle(.white.opacity(0.82))

            case .loaded(let universe):
                universeContent(universe)

            case .failed(let message):
                ContentUnavailableView {
                    Label(
                        appModel.text("Research data unavailable", "研究数据不可用"),
                        systemImage: "externaldrive.badge.exclamationmark"
                    )
                } description: {
                    Text(message)
                        .font(.callout)
                        .textSelection(.enabled)
                        .frame(maxWidth: 560)
                } actions: {
                    Button(appModel.text("Try Again", "重试")) {
                        Task { await loadUniverse() }
                    }
                }
            }
        }
        .task {
            guard case .idle = loadState else { return }
            await loadUniverse()
        }
        .onChange(of: appModel.searchSubmissionToken) { _, _ in
            guard case .loaded(let universe) = loadState else { return }
            focusBestMatch(in: universe, query: appModel.searchText, pulsesBeforeFocus: true)
        }
        .onDisappear {
            pendingFocusTask?.cancel()
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(appModel.text("Antarctic research universe", "南极研究宇宙"))
    }

    private func universeContent(_ universe: ResearchUniverse) -> some View {
        GeometryReader { proxy in
            let inspectorWidth = min(342.0, max(304.0, proxy.size.width * 0.31))

            ZStack {
                Color(red: 0.008, green: 0.028, blue: 0.058)

                HStack(spacing: 0) {
                    graphStage(universe)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)

                    if appModel.isInspectorPresented {
                        UniverseInspector(
                            universe: universe,
                            selectedNodeID: selectedNodeID,
                            language: appModel.language,
                            reduceMotion: reduceMotion,
                            onOpenEvidence: onOpenEvidence,
                            onSelect: { node in
                                activate(node, in: universe)
                            }
                        )
                        .frame(width: inspectorWidth)
                        .padding(.leading, 6)
                        .padding(.trailing, 14)
                        .padding(.vertical, 14)
                        .transition(
                            reduceMotion
                                ? .opacity
                                : .move(edge: .trailing).combined(with: .opacity)
                        )
                    }
                }
            }
            .animation(
                reduceMotion ? nil : .smooth(duration: 0.28),
                value: appModel.isInspectorPresented
            )
        }
    }

    private func graphStage(_ universe: ResearchUniverse) -> some View {
        ZStack(alignment: .bottom) {
            UniverseBackdrop(image: backgroundImage)

            UniverseGraphCanvas(
                universe: universe,
                selectedNodeID: selectedNodeID,
                focusedNodeID: focusedNodeID,
                pulsingNodeID: pulsingNodeID,
                graphScale: graphScale,
                isDepthEnabled: isDepthEnabled,
                reduceMotion: reduceMotion,
                onSelect: { node in
                    activate(node, in: universe)
                },
                onReset: {
                    resetUniverse()
                }
            )
            .padding(.top, 10)
            .padding(.leading, 8)
            .padding(.trailing, 58)
            .padding(.bottom, 78)

            VStack {
                HStack {
                    Spacer()
                    UniverseControlDock(
                        isDepthEnabled: isDepthEnabled,
                        canZoomIn: graphScale < 1.24,
                        canZoomOut: graphScale > 0.80,
                        language: appModel.language,
                        onHome: {
                            resetUniverse()
                            withOptionalAnimation {
                                graphScale = 1
                                isDepthEnabled = false
                            }
                        },
                        onZoomIn: {
                            withOptionalAnimation {
                                graphScale = min(1.24, graphScale + 0.10)
                            }
                        },
                        onZoomOut: {
                            withOptionalAnimation {
                                graphScale = max(0.80, graphScale - 0.10)
                            }
                        },
                        onToggleDepth: {
                            withOptionalAnimation {
                                isDepthEnabled.toggle()
                            }
                        }
                    )
                }
                Spacer()
            }
            .padding(.top, 18)
            .padding(.trailing, 14)

            AskPaperComposer(
                text: searchBinding,
                selectedProvider: providerBinding,
                language: appModel.language,
                reduceMotion: reduceMotion,
                onSubmit: {
                    focusBestMatch(
                        in: universe,
                        query: appModel.searchText,
                        pulsesBeforeFocus: true
                    )
                }
            )
            .padding(.horizontal, 24)
            .padding(.bottom, 18)
        }
        .contentShape(Rectangle())
        .focusable()
        // Keep keyboard exploration, but do not let AppKit's default focus halo
        // cut a bright rectangular seam through the immersive graph workspace.
        .focusEffectDisabled()
        .onKeyPress(.leftArrow) {
            moveSelection(by: -1, in: universe)
            return .handled
        }
        .onKeyPress(.rightArrow) {
            moveSelection(by: 1, in: universe)
            return .handled
        }
        .onKeyPress(.upArrow) {
            moveToParent(in: universe)
            return .handled
        }
        .onKeyPress(.downArrow) {
            moveToFirstChild(in: universe)
            return .handled
        }
        .accessibilityHint(
            appModel.text(
                "Use the arrow keys to move between connected research nodes",
                "使用方向键在关联研究节点之间移动"
            )
        )
    }

    @MainActor
    private func loadUniverse() async {
        loadState = .loading

        if let backgroundURL = ResourceLocator.locateUniverseBackground() {
            backgroundImage = NSImage(contentsOf: backgroundURL)
        }

        do {
            let universe = try await Task.detached(priority: .userInitiated) {
                try ResourceLocator.loadResearchUniverse()
            }.value
            loadState = .loaded(universe)
            if !universe.nodes.contains(where: { $0.id == selectedNodeID }) {
                selectedNodeID = UniverseNode.core.id
            }
            if !focusedNodeID.isEmpty,
               !universe.nodes.contains(where: { $0.id == focusedNodeID }) {
                focusedNodeID = ""
            }
        } catch is CancellationError {
            return
        } catch {
            loadState = .failed(error.localizedDescription)
        }
    }

    private func focusBestMatch(
        in universe: ResearchUniverse,
        query: String,
        pulsesBeforeFocus: Bool
    ) {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty,
              let match = UniverseSearch.bestMatch(for: trimmed, in: universe) else { return }

        pendingFocusTask?.cancel()
        withAnimation(reduceMotion ? nil : .easeInOut(duration: 0.24)) {
            selectedNodeID = match.id
            pulsingNodeID = pulsesBeforeFocus && !reduceMotion ? match.id : nil
        }

        guard pulsesBeforeFocus, !reduceMotion else {
            animateUniverseFocus {
                focusedNodeID = match.id
            }
            return
        }

        let expectedID = match.id
        pendingFocusTask = Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(1_250))
            guard !Task.isCancelled, pulsingNodeID == expectedID else { return }
            animateUniverseFocus {
                focusedNodeID = expectedID
                pulsingNodeID = nil
            }
        }
    }

    private var searchBinding: Binding<String> {
        Binding(
            get: { appModel.searchText },
            set: { appModel.searchText = $0 }
        )
    }

    private var providerBinding: Binding<AIProvider> {
        Binding(
            get: { appModel.aiProvider },
            set: { appModel.aiProvider = $0 }
        )
    }

    private func moveSelection(by offset: Int, in universe: ResearchUniverse) {
        let nodes = universe.nodes
        guard !nodes.isEmpty else { return }
        let currentIndex = nodes.firstIndex(where: { $0.id == selectedNodeID }) ?? 0
        let target = (currentIndex + offset + nodes.count) % nodes.count
        activate(nodes[target], in: universe)
    }

    private func moveToParent(in universe: ResearchUniverse) {
        guard let selected = universe.nodes.first(where: { $0.id == selectedNodeID }) else { return }
        switch selected {
        case .core:
            break
        case .area:
            activate(.core, in: universe)
        case .topic(let topic):
            if let area = universe.area(named: topic.areaName) {
                activate(.area(area), in: universe)
            }
        }
    }

    private func moveToFirstChild(in universe: ResearchUniverse) {
        guard let selected = universe.nodes.first(where: { $0.id == selectedNodeID }) else { return }
        switch selected {
        case .core:
            if let area = universe.areas.first {
                activate(.area(area), in: universe)
            }
        case .area(let area):
            if let topic = area.topics.first {
                activate(.topic(topic), in: universe)
            }
        case .topic:
            break
        }
    }

    private func activate(_ node: UniverseNode, in universe: ResearchUniverse) {
        pendingFocusTask?.cancel()
        pulsingNodeID = nil

        if focusedNodeID == node.id {
            resetUniverse()
            return
        }

        animateUniverseFocus {
            selectedNodeID = node.id
            focusedNodeID = node.id
        }
    }

    private func resetUniverse() {
        pendingFocusTask?.cancel()
        animateUniverseFocus {
            selectedNodeID = UniverseNode.core.id
            focusedNodeID = ""
            pulsingNodeID = nil
        }
    }

    private func animateUniverseFocus(_ updates: () -> Void) {
        withAnimation(
            reduceMotion ? nil : .timingCurve(0.20, 0.80, 0.20, 1.00, duration: 0.85),
            updates
        )
    }

    private func withOptionalAnimation(_ updates: () -> Void) {
        withAnimation(reduceMotion ? nil : .easeInOut(duration: 0.22), updates)
    }
}

private struct UniverseBackdrop: View {
    let image: NSImage?

    var body: some View {
        ZStack {
            Color(red: 0.01, green: 0.035, blue: 0.07)

            if let image {
                Image(nsImage: image)
                    .resizable()
                    .scaledToFill()
                    .transition(.opacity)

                Color.black.opacity(0.12)
            }
        }
        .clipped()
        .ignoresSafeArea()
        .accessibilityHidden(true)
    }
}

private struct UniverseGraphCanvas: View {
    private struct NodeHitCandidate {
        let node: UniverseNode
        let normalizedDistance: CGFloat
        let layer: Double
    }

    let universe: ResearchUniverse
    let selectedNodeID: String
    let focusedNodeID: String
    let pulsingNodeID: String?
    let graphScale: Double
    let isDepthEnabled: Bool
    let reduceMotion: Bool
    let onSelect: (UniverseNode) -> Void
    let onReset: () -> Void

    // The original Universe updates nodes and link endpoints in the same frame.
    // These layouts are interpolated once and consumed by both render paths.
    @State private var transitionSource: [String: CGPoint] = [:]
    @State private var transitionTarget: [String: CGPoint] = [:]
    @State private var transitionStartedAt: Date?
    @State private var hoveredNodeID: String?

    var body: some View {
        GeometryReader { proxy in
            let relatedIDs = relatedNodeIDs(to: focusedNodeID)

            TimelineView(.animation(minimumInterval: 1.0 / 30.0, paused: reduceMotion)) { timeline in
                let time = timeline.date.timeIntervalSinceReferenceDate
                let positions = displayedPositions(
                    at: timeline.date,
                    fallback: graphPositions(in: proxy.size, focusedNodeID: focusedNodeID)
                )
                let breath = reduceMotion
                    ? 0.0
                    : (Darwin.sin(time * (2 * .pi / 4.2)) + 1) / 2
                let targetPulse = reduceMotion
                    ? 0.0
                    : (Darwin.sin(time * (2 * .pi / 0.78)) + 1) / 2
                let dashPhase = reduceMotion ? 0 : CGFloat((time / 1.55) * 38)

                ZStack {
                    Canvas { context, _ in
                        drawConnections(
                            context: &context,
                            positions: positions,
                            focusedNodeID: focusedNodeID,
                            dashPhase: dashPhase
                        )
                    }
                    .accessibilityHidden(true)

                    ForEach(universe.nodes) { node in
                        if let position = positions[node.id] {
                            let related = focusedNodeID.isEmpty || relatedIDs.contains(node.id)
                            UniverseNodeButton(
                                node: node,
                                selected: node.id == selectedNodeID,
                                focused: node.id == focusedNodeID,
                                related: related,
                                pulsing: node.id == pulsingNodeID,
                                breath: breath,
                                targetPulse: targetPulse,
                                reduceMotion: reduceMotion,
                                isHovering: node.id == hoveredNodeID
                            ) {
                                onSelect(node)
                            }
                            .position(position)
                            .zIndex(
                                nodeLayer(
                                    for: node,
                                    related: related,
                                    focusedNodeID: focusedNodeID
                                )
                            )
                        }
                    }

                    // This surface is above the visual button layer. The original SVG only
                    // made the painted circle clickable; label text
                    // deliberately ignored pointer events.  SwiftUI Buttons otherwise use
                    // their full layout rectangle, which made neighbouring topic labels
                    // overlap and caused a click to select the wrong node.  Resolve one
                    // hit test in graph coordinates instead, using the nearest visible orb
                    // and the same visual layer order used for drawing.
                    Color.clear
                        .contentShape(Rectangle())
                        .gesture(
                            SpatialTapGesture(coordinateSpace: .local)
                                .onEnded { value in
                                    selectNode(at: value.location, positions: positions)
                                }
                        )
                        .onContinuousHover(coordinateSpace: .local) { phase in
                            switch phase {
                            case .active(let location):
                                let nextHoveredNodeID = node(at: location, positions: positions)?.id
                                guard hoveredNodeID != nextHoveredNodeID else { return }
                                hoveredNodeID = nextHoveredNodeID
                            case .ended:
                                hoveredNodeID = nil
                            }
                        }
                        .zIndex(1_000)
                        .accessibilityHidden(true)
                }
            }
            .scaleEffect(graphScale)
            .rotation3DEffect(
                .degrees(isDepthEnabled ? 5 : 0),
                axis: (x: 1, y: -0.12, z: 0),
                anchor: .center,
                perspective: isDepthEnabled ? 0.24 : 0
            )
            .animation(
                reduceMotion ? nil : .smooth(duration: 0.36),
                value: isDepthEnabled
            )
            .frame(width: proxy.size.width, height: proxy.size.height)
            .clipped()
            .onAppear {
                establishLayout(in: proxy.size, focusedNodeID: focusedNodeID, animated: false)
            }
            .onChange(of: focusedNodeID) { _, newFocusedNodeID in
                establishLayout(in: proxy.size, focusedNodeID: newFocusedNodeID, animated: true)
            }
            .onChange(of: proxy.size) { _, newSize in
                establishLayout(in: newSize, focusedNodeID: focusedNodeID, animated: false)
            }
            .onChange(of: reduceMotion) { _, _ in
                establishLayout(in: proxy.size, focusedNodeID: focusedNodeID, animated: false)
            }
        }
    }

    private func establishLayout(
        in size: CGSize,
        focusedNodeID: String,
        animated: Bool
    ) {
        guard size.width > 0, size.height > 0 else { return }

        let now = Date()
        let target = graphPositions(in: size, focusedNodeID: focusedNodeID)
        let source = displayedPositions(at: now, fallback: target)
        var transaction = Transaction(animation: nil)
        transaction.disablesAnimations = true

        withTransaction(transaction) {
            transitionSource = source
            transitionTarget = target
            transitionStartedAt = animated && !reduceMotion ? now : nil
        }
    }

    private func displayedPositions(
        at date: Date,
        fallback: [String: CGPoint]
    ) -> [String: CGPoint] {
        guard !transitionTarget.isEmpty else { return fallback }
        guard !reduceMotion,
              let transitionStartedAt,
              !transitionSource.isEmpty else {
            return transitionTarget
        }

        let progress = min(
            max(date.timeIntervalSince(transitionStartedAt) / 0.85, 0),
            1
        )
        guard progress < 1 else { return transitionTarget }
        let eased = 1 - Darwin.pow(1 - progress, 3)

        var interpolated = transitionTarget
        for (id, destination) in transitionTarget {
            guard let origin = transitionSource[id] else { continue }
            interpolated[id] = CGPoint(
                x: origin.x + (destination.x - origin.x) * eased,
                y: origin.y + (destination.y - origin.y) * eased
            )
        }
        return interpolated
    }

    private func graphPositions(in size: CGSize, focusedNodeID: String) -> [String: CGPoint] {
        let center = CGPoint(x: size.width * 0.52, y: size.height * 0.50)
        guard !focusedNodeID.isEmpty,
              let focused = universe.nodes.first(where: { $0.id == focusedNodeID }) else {
            return homePositions(in: size, center: center)
        }

        var positions: [String: CGPoint] = [focused.id: center]
        let shown: [UniverseNode]

        switch focused {
        case .core:
            shown = universe.areas.map(UniverseNode.area)
        case .area(let area):
            shown = area.topics.map(UniverseNode.topic)
        case .topic(let topic):
            shown = universe.area(named: topic.areaName)?.topics
                .filter { UniverseNode.topic($0).id != focused.id }
                .map(UniverseNode.topic) ?? []
        }

        let availableRingRadius = min(
            center.x - 54,
            size.width - 54 - center.x,
            center.y - 46,
            size.height - 54 - center.y
        )
        let ringRadius = min(
            min(size.width, size.height) * (focused.graphLevel == 2 ? 0.245 : 0.30),
            max(0, availableRingRadius)
        )
        for (index, node) in shown.enumerated() {
            let angle = (2 * Double.pi * Double(index) / Double(max(shown.count, 1))) - .pi / 2
            positions[node.id] = clamped(
                CGPoint(
                    x: center.x + CGFloat(Darwin.cos(angle) * Double(ringRadius)),
                    y: center.y + CGFloat(Darwin.sin(angle) * Double(ringRadius))
                ),
                in: size
            )
        }

        if let parent = parent(of: focused) {
            positions[parent.id] = clamped(
                CGPoint(
                    x: center.x - min(size.width * 0.31, 178),
                    y: center.y - min(size.height * 0.29, 150)
                ),
                in: size
            )
        }

        let remaining = universe.nodes.filter { positions[$0.id] == nil }
        let outerHorizontalRadius = max(
            0,
            min(center.x - 54, size.width - 54 - center.x) * 0.90
        )
        let outerVerticalRadius = max(
            0,
            min(center.y - 46, size.height - 54 - center.y) * 0.90
        )
        for (index, node) in remaining.enumerated() {
            // A slight phase offset keeps the dimmed outer constellation from
            // landing directly on a focused node's inner orbit.
            let angle = 2 * Double.pi * Double(index) / Double(max(remaining.count, 1)) + 0.17
            positions[node.id] = clamped(
                CGPoint(
                    x: center.x + CGFloat(Darwin.cos(angle) * Double(outerHorizontalRadius)),
                    y: center.y + CGFloat(Darwin.sin(angle) * Double(outerVerticalRadius))
                ),
                in: size
            )
        }

        return resolveOrbCollisions(
            positions,
            in: size,
            anchoredNodeIDs: [focused.id]
        )
    }

    private func homePositions(in size: CGSize, center: CGPoint) -> [String: CGPoint] {
        let areaAngles: [String: Double] = [
            "Ocean": 160,
            "Ice Dynamics": 25,
            "Solid Earth": 270,
            "Observations": 90,
            "Paleoclimate": 215,
            "Future Projections": 325,
        ]
        let areaRadius = min(size.width * 0.29, size.height * 0.29)
        // Keep each research area's fan inside its own angular sector. The
        // earlier 23° spacing caused the Future and Ice fans to overlap at the
        // top of a wide macOS window, including stacked nodes and unreadable
        // labels. Alternating near/far rings preserve the constellation feel
        // while giving each topic its own visual lane.
        let topicAngleStep = 12.0
        let radialOffsets: [Double] = [-20, 22, -8, 28, -16]
        let outerHorizontalLimit = min(center.x - 54, size.width - 54 - center.x)
        let outerVerticalLimit = min(center.y - 46, size.height - 54 - center.y)
        let maximumStagger = radialOffsets.map(abs).max() ?? 0
        let topicRadius = min(
            min(size.width * 0.405, size.height * 0.405),
            max(0, min(outerHorizontalLimit, outerVerticalLimit) - maximumStagger)
        )
        var positions: [String: CGPoint] = [UniverseNode.core.id: center]

        for (areaIndex, area) in universe.areas.enumerated() {
            let areaDegrees = areaAngles[area.name]
                ?? (Double(areaIndex) / Double(max(universe.areas.count, 1)) * 360)
            positions[UniverseNode.area(area).id] = clamped(
                polar(center: center, degrees: areaDegrees, radius: areaRadius),
                in: size
            )

            let areaRadialOffsets = area.name == "Ocean"
                ? [-22.0, 42, -38, 24]
                : radialOffsets

            for (topicIndex, topic) in area.topics.enumerated() {
                let localDegrees = areaDegrees
                    + (Double(topicIndex) - Double(area.topics.count - 1) / 2) * topicAngleStep
                let stagger = areaRadialOffsets[topicIndex % areaRadialOffsets.count]
                positions[UniverseNode.topic(topic).id] = clamped(
                    polar(center: center, degrees: localDegrees, radius: topicRadius + stagger),
                    in: size
                )
            }
        }

        return resolveOrbCollisions(
            positions,
            in: size,
            anchoredNodeIDs: [UniverseNode.core.id]
        )
    }

    private func polar(center: CGPoint, degrees: Double, radius: Double) -> CGPoint {
        let angle = (degrees - 90) * .pi / 180
        return CGPoint(
            x: center.x + CGFloat(Darwin.cos(angle) * radius),
            y: center.y + CGFloat(Darwin.sin(angle) * radius)
        )
    }

    private func clamped(_ point: CGPoint, in size: CGSize) -> CGPoint {
        CGPoint(
            x: min(max(point.x, 54), max(54, size.width - 54)),
            y: min(max(point.y, 40), max(40, size.height - 48))
        )
    }

    private func selectNode(
        at point: CGPoint,
        positions: [String: CGPoint]
    ) {
        if let node = node(at: point, positions: positions) {
            onSelect(node)
        } else {
            onReset()
        }
    }

    private func node(
        at point: CGPoint,
        positions: [String: CGPoint]
    ) -> UniverseNode? {
        let candidates = universe.nodes.compactMap { node -> NodeHitCandidate? in
            guard let position = positions[node.id] else { return nil }

            let radius = UniverseNodeButton.interactionRadius(
                for: node,
                selected: node.id == selectedNodeID,
                focused: node.id == focusedNodeID,
                pulsing: node.id == pulsingNodeID
            )
            let distance = hypot(point.x - position.x, point.y - position.y)
            guard distance <= radius else { return nil }

            return NodeHitCandidate(
                node: node,
                normalizedDistance: distance / radius,
                layer: nodeLayer(
                    for: node,
                    related: focusedNodeID.isEmpty || relatedNodeIDs(to: focusedNodeID).contains(node.id),
                    focusedNodeID: focusedNodeID
                )
            )
        }

        return candidates.sorted { lhs, rhs in
            // If two practical hit targets overlap, prefer the closest sphere.
            // Within a tiny visual tie, use the same z-order that the user sees.
            if abs(lhs.normalizedDistance - rhs.normalizedDistance) < 0.08 {
                return lhs.layer > rhs.layer
            }
            return lhs.normalizedDistance < rhs.normalizedDistance
        }.first?.node
    }

    private func nodeLayer(
        for node: UniverseNode,
        related: Bool,
        focusedNodeID: String
    ) -> Double {
        if node.id == focusedNodeID { return 300 }
        if node.id == selectedNodeID { return 220 }
        if related { return 120 + Double(node.graphLevel) }
        // Small topic spheres should remain legible above their larger parents
        // in the rare case that the graph temporarily overlaps during a move.
        return Double(node.graphLevel)
    }

    private func resolveOrbCollisions(
        _ positions: [String: CGPoint],
        in size: CGSize,
        anchoredNodeIDs: Set<String>
    ) -> [String: CGPoint] {
        var resolved = positions
        let nodes = universe.nodes.filter { resolved[$0.id] != nil }

        // Keep the original radial graph, but resolve only the genuinely tight
        // overlaps that arise on narrow stages or at the outer clamp boundary.
        // This is deterministic and runs only when calculating a layout target,
        // so the existing shared 850 ms node/link interpolation stays intact.
        for _ in 0..<10 {
            var adjusted = false

            for leftIndex in nodes.indices {
                for rightIndex in nodes.indices.dropFirst(leftIndex + 1) {
                    let leftNode = nodes[leftIndex]
                    let rightNode = nodes[rightIndex]
                    guard let left = resolved[leftNode.id],
                          let right = resolved[rightNode.id] else { continue }

                    let minimumDistance = UniverseNodeButton.collisionRadius(
                        for: leftNode,
                        selected: leftNode.id == selectedNodeID,
                        focused: leftNode.id == focusedNodeID
                    ) + UniverseNodeButton.collisionRadius(
                        for: rightNode,
                        selected: rightNode.id == selectedNodeID,
                        focused: rightNode.id == focusedNodeID
                    ) + 8
                    let distance = hypot(right.x - left.x, right.y - left.y)
                    guard distance < minimumDistance else { continue }

                    let direction: CGPoint
                    if distance > 0.001 {
                        direction = CGPoint(
                            x: (right.x - left.x) / distance,
                            y: (right.y - left.y) / distance
                        )
                    } else {
                        let angle = Double(leftIndex * 53 + rightIndex * 97) * .pi / 180
                        direction = CGPoint(
                            x: CGFloat(Darwin.cos(angle)),
                            y: CGFloat(Darwin.sin(angle))
                        )
                    }

                    let separation = minimumDistance - max(distance, 0.001)
                    let leftAnchored = anchoredNodeIDs.contains(leftNode.id)
                    let rightAnchored = anchoredNodeIDs.contains(rightNode.id)
                    let leftMultiplier: CGFloat
                    let rightMultiplier: CGFloat

                    switch (leftAnchored, rightAnchored) {
                    case (true, false):
                        leftMultiplier = 0
                        rightMultiplier = 1
                    case (false, true):
                        leftMultiplier = 1
                        rightMultiplier = 0
                    case (true, true):
                        continue
                    case (false, false):
                        leftMultiplier = 0.5
                        rightMultiplier = 0.5
                    }

                    resolved[leftNode.id] = clamped(
                        CGPoint(
                            x: left.x - direction.x * separation * leftMultiplier,
                            y: left.y - direction.y * separation * leftMultiplier
                        ),
                        in: size
                    )
                    resolved[rightNode.id] = clamped(
                        CGPoint(
                            x: right.x + direction.x * separation * rightMultiplier,
                            y: right.y + direction.y * separation * rightMultiplier
                        ),
                        in: size
                    )
                    adjusted = true
                }
            }

            if !adjusted { break }
        }

        return resolved
    }

    private func parent(of node: UniverseNode) -> UniverseNode? {
        switch node {
        case .core:
            nil
        case .area:
            .core
        case .topic(let topic):
            universe.area(named: topic.areaName).map(UniverseNode.area)
        }
    }

    private func relatedNodeIDs(to focusedNodeID: String) -> Set<String> {
        guard !focusedNodeID.isEmpty,
              let focused = universe.nodes.first(where: { $0.id == focusedNodeID }) else {
            return Set(universe.nodes.map(\.id))
        }

        var related: Set<String> = [focused.id]
        switch focused {
        case .core:
            related.formUnion(universe.areas.map { UniverseNode.area($0).id })
        case .area(let area):
            related.insert(UniverseNode.core.id)
            related.formUnion(area.topics.map { UniverseNode.topic($0).id })
        case .topic(let topic):
            if let area = universe.area(named: topic.areaName) {
                related.insert(UniverseNode.area(area).id)
                related.formUnion(area.topics.map { UniverseNode.topic($0).id })
            }
        }
        return related
    }

    private func drawConnections(
        context: inout GraphicsContext,
        positions: [String: CGPoint],
        focusedNodeID: String,
        dashPhase: CGFloat
    ) {
        guard let corePoint = positions[UniverseNode.core.id] else { return }
        let related = relatedNodeIDs(to: focusedNodeID)

        for area in universe.areas {
            let areaNode = UniverseNode.area(area)
            guard let areaPoint = positions[areaNode.id] else { continue }
            let areaColor = AtlasHexColor.color(area.colorHex)

            drawLink(
                from: corePoint,
                to: areaPoint,
                color: areaColor,
                baseWidth: 1.45,
                active: !focusedNodeID.isEmpty
                    && related.contains(UniverseNode.core.id)
                    && related.contains(areaNode.id),
                dashPhase: dashPhase,
                context: &context
            )

            for topic in area.topics {
                let topicID = UniverseNode.topic(topic).id
                guard let topicPoint = positions[topicID] else { continue }
                drawLink(
                    from: areaPoint,
                    to: topicPoint,
                    color: areaColor,
                    baseWidth: 0.94,
                    active: !focusedNodeID.isEmpty
                        && related.contains(areaNode.id)
                        && related.contains(topicID),
                    dashPhase: dashPhase,
                    context: &context
                )
            }
        }
    }

    private func drawLink(
        from start: CGPoint,
        to end: CGPoint,
        color: Color,
        baseWidth: CGFloat,
        active: Bool,
        dashPhase: CGFloat,
        context: inout GraphicsContext
    ) {
        var path = Path()
        path.move(to: start)
        path.addLine(to: end)
        context.stroke(
            path,
            with: .linearGradient(
                Gradient(colors: [
                    .white.opacity(active ? 0.78 : 0.16),
                    color.opacity(active ? 0.96 : 0.46),
                ]),
                startPoint: start,
                endPoint: end
            ),
            style: StrokeStyle(
                lineWidth: active ? 3.2 : baseWidth,
                lineCap: .round,
                dash: active ? [9, 10] : [],
                dashPhase: active ? -dashPhase : 0
            )
        )
    }
}

private struct UniverseNodeButton: View {
    let node: UniverseNode
    let selected: Bool
    let focused: Bool
    let related: Bool
    let pulsing: Bool
    let breath: Double
    let targetPulse: Double
    let reduceMotion: Bool
    let isHovering: Bool
    let action: () -> Void

    private var diameter: Double {
        Self.orbDiameter(for: node)
    }

    static func orbDiameter(for node: UniverseNode) -> Double {
        switch node.graphLevel {
        case 0: 82
        case 1: 48
        default: 29
        }
    }

    static func interactionRadius(
        for node: UniverseNode,
        selected: Bool,
        focused: Bool,
        pulsing: Bool
    ) -> CGFloat {
        let focusScale = focused ? 1.22 : selected ? 1.08 : 1.0
        let pulseScale = pulsing ? 1.12 : 1.0
        // A 44 pt minimum makes the small topic spheres comfortable to target
        // without ever expanding to the surrounding label's old rectangle.
        return CGFloat(max(22, orbDiameter(for: node) / 2 * focusScale * pulseScale + 4))
    }

    static func collisionRadius(
        for node: UniverseNode,
        selected: Bool,
        focused: Bool
    ) -> CGFloat {
        let scale = focused ? 1.22 : selected ? 1.08 : 1.0
        return CGFloat(orbDiameter(for: node) / 2 * scale)
    }

    private var visualOpacity: Double {
        related ? 1.0 : 0.24
    }

    private var visualScale: Double {
        let focusScale = focused ? 1.22 : selected ? 1.08 : 1.0
        let hoverScale = isHovering ? 1.045 : 1.0
        let pulseScale = pulsing ? 1.0 + targetPulse * 0.12 : 1.0
        return focusScale * hoverScale * pulseScale
    }

    var body: some View {
        Button(action: action) {
            ZStack {
                nodeOrb

                // The Windows graph puts each title in the same SVG group as
                // its circle: it is centred over the coloured orb, follows the
                // orb during focus, and never becomes a separate floating label.
                // Keep that relationship intact here.
                Text(sourceWrappedTitle)
                    .font(labelFont)
                    .tracking(node.graphLevel == 0 ? 0.4 : 0.1)
                    .foregroundStyle(.white.opacity(0.94))
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
                    .fixedSize(horizontal: true, vertical: false)
                    .shadow(color: .black.opacity(0.98), radius: 2.2, y: 1)
                    .shadow(color: .black.opacity(0.72), radius: 4.5)
                    .allowsHitTesting(false)
            }
            .scaleEffect(visualScale)
            .frame(width: diameter, height: diameter)
            .contentShape(Circle())
            .opacity(visualOpacity)
        }
        .buttonStyle(.plain)
        .animation(
            reduceMotion ? nil : .easeInOut(duration: 0.55),
            value: related
        )
        .animation(reduceMotion ? nil : .easeInOut(duration: 0.55), value: selected)
        .animation(reduceMotion ? nil : .easeOut(duration: 0.16), value: isHovering)
        .help("\(node.eyebrow.capitalized): \(node.keyQuestion)")
        .accessibilityLabel(node.title)
        .accessibilityValue(node.eyebrow.capitalized)
        .accessibilityHint(
            focused
                ? "Return to the complete research universe"
                : "Focus the universe on this research node"
        )
    }

    private var nodeOrb: some View {
        let color = AtlasHexColor.color(node.colorHex)
        let sourceFillOpacity = node.graphLevel == 2 ? 0.70 : 0.88

        return ZStack {
            Circle()
                .fill(.clear)
                .frame(
                    width: max(44, diameter + 20),
                    height: max(44, diameter + 20)
                )

            if selected || pulsing {
                Circle()
                    .stroke(
                        pulsing
                            ? .white.opacity(0.60 + targetPulse * 0.40)
                            : AtlasHexColor.color(node.colorHex).opacity(0.50 + breath * 0.30),
                        lineWidth: pulsing ? 2.8 + targetPulse * 3.2 : 1.8
                    )
                    .frame(
                        width: diameter + 14 + (pulsing ? targetPulse * 10 : breath * 4),
                        height: diameter + 14 + (pulsing ? targetPulse * 10 : breath * 4)
                    )
            }

            // This deliberately keeps the original Windows universe language:
            // a translucent semantic-color orb, its soft white core, and a crisp
            // white outline. The surrounding macOS shell is native; the scientific
            // spheres themselves remain the recognisable atlas objects.
            Circle()
                .fill(color.opacity(sourceFillOpacity))
                .overlay {
                    Circle()
                        .strokeBorder(
                            selected ? .white.opacity(0.96) : .white.opacity(0.76),
                            lineWidth: focused ? 4.4 : selected ? 2.8 : node.graphLevel == 0 ? 2.6 : 1.5
                        )
                }
                .frame(width: diameter, height: diameter)
                .shadow(
                    color: Color(red: 0.51, green: 0.82, blue: 1.0).opacity(
                        focused ? 0.96 : selected ? 0.74 : 0.52 + breath * 0.12
                    ),
                    radius: focused ? 34 : selected ? 21 : 14 + breath * 5
                )

            Circle()
                .fill(.white.opacity(0.22))
                .frame(width: diameter * 0.58, height: diameter * 0.58)
        }
    }

    private var sourceWrappedTitle: String {
        let words = node.title.split(separator: " ").map(String.init)
        guard node.title.count > 15, words.count > 1 else { return node.title }

        let splitIndex = (words.count + 1) / 2
        return [
            words[..<splitIndex].joined(separator: " "),
            words[splitIndex...].joined(separator: " "),
        ].joined(separator: "\n")
    }

    private var labelFont: Font {
        switch node.graphLevel {
        case 0:
            .system(size: 10.5, weight: .semibold)
        case 1:
            .system(size: 8.5, weight: .semibold)
        default:
            .system(size: 6.6, weight: .semibold)
        }
    }
}

private struct UniverseControlDock: View {
    let isDepthEnabled: Bool
    let canZoomIn: Bool
    let canZoomOut: Bool
    let language: AppLanguage
    let onHome: () -> Void
    let onZoomIn: () -> Void
    let onZoomOut: () -> Void
    let onToggleDepth: () -> Void

    var body: some View {
        VStack(spacing: 6) {
            dockButton("location.north.line.fill", hint: "Center", action: onHome)

            Divider()
                .frame(width: 28)
                .overlay(.white.opacity(0.12))

            dockButton("plus", hint: "Zoom in", action: onZoomIn)
                .disabled(!canZoomIn)
            dockButton("minus", hint: "Zoom out", action: onZoomOut)
                .disabled(!canZoomOut)

            Divider()
                .frame(width: 28)
                .overlay(.white.opacity(0.12))

            Button(action: onToggleDepth) {
                VStack(spacing: 2) {
                    Image(systemName: isDepthEnabled ? "cube.fill" : "cube.transparent")
                    Text("3D")
                        .font(.system(size: 8, weight: .bold))
                }
                .frame(width: 32, height: 34)
                .foregroundStyle(isDepthEnabled ? .cyan : .white.opacity(0.84))
            }
            .buttonStyle(.plain)
            .help(AtlasCopy.text("Toggle depth", "切换立体视图", language: language))
            .accessibilityLabel(
                AtlasCopy.text("Toggle three-dimensional view", "切换三维视图", language: language)
            )
        }
        .padding(.horizontal, 7)
        .padding(.vertical, 8)
        .fixedSize()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 17, style: .continuous))
        .background(
            Color(red: 0.015, green: 0.08, blue: 0.14).opacity(0.58),
            in: RoundedRectangle(cornerRadius: 17, style: .continuous)
        )
        .overlay {
            RoundedRectangle(cornerRadius: 17, style: .continuous)
                .strokeBorder(.white.opacity(0.16), lineWidth: 0.8)
        }
        .shadow(color: .black.opacity(0.34), radius: 14, y: 6)
    }

    private func dockButton(
        _ symbol: String,
        hint: String,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Image(systemName: symbol)
                .font(.caption.weight(.semibold))
                .frame(width: 26, height: 26)
                .foregroundStyle(.white.opacity(0.88))
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .help(AtlasCopy.text(hint, localizedControlHint(hint), language: language))
        .accessibilityLabel(AtlasCopy.text(hint, localizedControlHint(hint), language: language))
    }

    private func localizedControlHint(_ hint: String) -> String {
        switch hint {
        case "Parent": "上一级"
        case "Previous": "上一个"
        case "Center": "回到中心"
        case "Next": "下一个"
        case "Child": "下一级"
        case "Zoom in": "放大"
        case "Zoom out": "缩小"
        default: hint
        }
    }
}

private struct AskPaperComposer: View {
    @Binding var text: String
    @Binding var selectedProvider: AIProvider
    let language: AppLanguage
    let reduceMotion: Bool
    let onSubmit: () -> Void

    @FocusState private var isFocused: Bool

    private var canSubmit: Bool {
        !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "sparkles")
                .font(.title3.weight(.semibold))
                .foregroundStyle(.cyan.opacity(0.90))
                .symbolEffect(
                    .pulse,
                    options: .repeating.speed(0.28),
                    isActive: isFocused && !reduceMotion
                )

            TextField(
                AtlasCopy.text("Ask the paper…", "向论文提问…", language: language),
                text: $text
            )
            .textFieldStyle(.plain)
            .foregroundStyle(.white)
            .focused($isFocused)
            .onSubmit {
                guard canSubmit else { return }
                onSubmit()
            }
            .accessibilityLabel(AtlasCopy.text("Ask the paper", "向论文提问", language: language))

            Menu {
                ForEach(AIProvider.allCases) { provider in
                    Button {
                        selectedProvider = provider
                    } label: {
                        Label(
                            provider.title(language: language),
                            systemImage: provider == selectedProvider
                                ? "checkmark"
                                : provider.symbolName
                        )
                    }
                }
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: selectedProvider.symbolName)
                    Text(selectedProvider.title(language: language))
                        .lineLimit(1)
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.system(size: 8, weight: .semibold))
                        .foregroundStyle(.secondary)
                }
                .font(.caption.weight(.medium))
                .foregroundStyle(.white.opacity(0.88))
            }
            .menuStyle(.borderlessButton)
            .fixedSize()
            .accessibilityLabel(AtlasCopy.text("Answer mode", "回答模式", language: language))

            Button {
                onSubmit()
            } label: {
                Image(systemName: "arrow.up")
                    .font(.callout.weight(.bold))
                    .frame(width: 30, height: 30)
                    .foregroundStyle(
                        canSubmit
                            ? Color(red: 0.02, green: 0.12, blue: 0.18)
                            : .white.opacity(0.34)
                    )
                    .background(
                        canSubmit ? Color.cyan.opacity(0.92) : Color.white.opacity(0.08),
                        in: Circle()
                    )
            }
            .buttonStyle(.plain)
            .disabled(!canSubmit)
            .keyboardShortcut(.return, modifiers: [.command])
            .help(AtlasCopy.text("Find paper evidence", "查找论文证据", language: language))
            .accessibilityLabel(
                AtlasCopy.text("Find paper evidence", "查找论文证据", language: language)
            )
        }
        .padding(.leading, 14)
        .padding(.trailing, 8)
        .frame(maxWidth: 690, minHeight: 48)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 17, style: .continuous))
        .background(
            Color(red: 0.015, green: 0.07, blue: 0.12).opacity(0.72),
            in: RoundedRectangle(cornerRadius: 17, style: .continuous)
        )
        .overlay {
            RoundedRectangle(cornerRadius: 17, style: .continuous)
                .strokeBorder(isFocused ? .cyan.opacity(0.62) : .white.opacity(0.18), lineWidth: 0.9)
        }
        .shadow(color: .black.opacity(0.38), radius: 18, y: 8)
    }
}

private struct UniverseInspector: View {
    let universe: ResearchUniverse
    let selectedNodeID: String
    let language: AppLanguage
    let reduceMotion: Bool
    let onOpenEvidence: ((ResearchTopic) -> Void)?
    let onSelect: (UniverseNode) -> Void

    @State private var displayedNodeID = ""
    @State private var contentVisible = true
    @State private var cardTransitionTask: Task<Void, Never>?

    private var effectiveNodeID: String {
        displayedNodeID.isEmpty ? selectedNodeID : displayedNodeID
    }

    private var selectedNode: UniverseNode {
        universe.nodes.first(where: { $0.id == effectiveNodeID }) ?? .core
    }

    private var relatedNodes: [UniverseNode] {
        switch selectedNode {
        case .core:
            universe.areas.map(UniverseNode.area)
        case .area(let area):
            area.topics.map(UniverseNode.topic)
        case .topic(let topic):
            universe.area(named: topic.areaName)?.topics
                .filter { $0.id != topic.id }
                .map(UniverseNode.topic) ?? []
        }
    }

    var body: some View {
        ScrollView {
            inspectorContent
                .id(effectiveNodeID)
                .opacity(contentVisible ? 1 : 0)
                .offset(y: contentVisible ? 0 : 10)
                .scaleEffect(contentVisible ? 1 : 0.985, anchor: .top)
        }
        .scrollIndicators(.hidden)
        .padding(20)
        .background(
            Color(red: 0.018, green: 0.065, blue: 0.11).opacity(0.93),
            in: RoundedRectangle(cornerRadius: 22, style: .continuous)
        )
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .strokeBorder(.white.opacity(0.15), lineWidth: 0.8)
        }
        .shadow(color: .black.opacity(0.45), radius: 22, x: 0, y: 10)
        .animation(
            reduceMotion ? nil : .easeInOut(duration: 0.24),
            value: contentVisible
        )
        .task {
            displayedNodeID = selectedNodeID
        }
        .onChange(of: selectedNodeID) { _, newID in
            cardTransitionTask?.cancel()
            guard !reduceMotion else {
                displayedNodeID = newID
                return
            }
            contentVisible = false
            cardTransitionTask = Task { @MainActor in
                try? await Task.sleep(for: .milliseconds(180))
                guard !Task.isCancelled else { return }
                displayedNodeID = newID
                contentVisible = true
            }
        }
        .onDisappear {
            cardTransitionTask?.cancel()
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(
            AtlasCopy.text("Evidence inspector", "证据检查器", language: language)
        )
    }

    private var inspectorContent: some View {
        VStack(alignment: .leading, spacing: 18) {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 8) {
                    Image(systemName: selectedNode.symbolName)
                        .foregroundStyle(AtlasHexColor.color(selectedNode.colorHex))
                    Text(selectedNode.eyebrow)
                        .font(.caption2.weight(.semibold))
                        .tracking(1.3)
                        .foregroundStyle(AtlasHexColor.color(selectedNode.colorHex))
                }

                Text(selectedNode.title)
                    .font(.title2.weight(.semibold))
                    .foregroundStyle(.white)
                    .textSelection(.enabled)

                Text(selectedNode.status)
                    .font(.caption.weight(.medium))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(
                        AtlasHexColor.color(selectedNode.colorHex).opacity(0.18),
                        in: Capsule()
                    )
                    .foregroundStyle(AtlasHexColor.color(selectedNode.colorHex))
            }

            Divider().overlay(.white.opacity(0.12))

            InspectorSection(
                title: AtlasCopy.text("KEY QUESTION", "核心问题", language: language),
                symbol: "questionmark.circle"
            ) {
                Text(selectedNode.keyQuestion)
            }

            InspectorSection(
                title: AtlasCopy.text("WHY IT MATTERS", "为何重要", language: language),
                symbol: "sparkles"
            ) {
                Text(selectedNode.evidenceSummary)
            }

            InspectorSection(
                title: AtlasCopy.text("SCIENTIFIC CAVEATS", "科学注意事项", language: language),
                symbol: "info.circle"
            ) {
                Text(scientificCaveat)
            }

            if let topic = selectedNode.topic, let onOpenEvidence {
                Divider().overlay(.white.opacity(0.12))

                VStack(alignment: .leading, spacing: 8) {
                    Text(AtlasCopy.text("SOURCE EVIDENCE", "来源证据", language: language))
                        .font(.caption2.weight(.semibold))
                        .tracking(1.2)
                        .foregroundStyle(.white.opacity(0.48))

                    Button {
                        onOpenEvidence(topic)
                    } label: {
                        HStack(spacing: 9) {
                            Image(systemName: "doc.text.magnifyingglass")
                            Text(AtlasCopy.text("Find in included paper", "在内置论文中查找", language: language))
                            Spacer()
                            Image(systemName: "arrow.up.right")
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.46))
                        }
                        .padding(10)
                        .foregroundStyle(.white.opacity(0.88))
                        .background(.white.opacity(0.055), in: RoundedRectangle(cornerRadius: 10))
                    }
                    .buttonStyle(.plain)
                }
            }

            Divider().overlay(.white.opacity(0.12))

            VStack(alignment: .leading, spacing: 8) {
                Text(AtlasCopy.text("RELATED REGIONS", "相关区域", language: language))
                    .font(.caption2.weight(.semibold))
                    .tracking(1.2)
                    .foregroundStyle(.white.opacity(0.48))

                ForEach(regionLabels, id: \.self) { region in
                    HStack(spacing: 9) {
                        Image(systemName: "map.fill")
                            .foregroundStyle(.white.opacity(0.46))
                        Text(region)
                            .lineLimit(2)
                        Spacer(minLength: 4)
                    }
                    .font(.callout)
                    .foregroundStyle(.white.opacity(0.82))
                    .padding(.vertical, 3)
                }
            }

            if !relatedNodes.isEmpty {
                Divider().overlay(.white.opacity(0.12))

                VStack(alignment: .leading, spacing: 8) {
                    Text(
                        selectedNode.graphLevel == 0
                            ? AtlasCopy.text("RESEARCH AREAS", "研究领域", language: language)
                            : AtlasCopy.text("CONNECTED NODES", "关联节点", language: language)
                    )
                    .font(.caption2.weight(.semibold))
                    .tracking(1.2)
                    .foregroundStyle(.white.opacity(0.48))

                    ForEach(relatedNodes) { node in
                        Button {
                            onSelect(node)
                        } label: {
                            HStack(spacing: 9) {
                                Circle()
                                    .fill(AtlasHexColor.color(node.colorHex))
                                    .frame(width: 7, height: 7)
                                Text(node.title)
                                    .lineLimit(1)
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .font(.caption2)
                                    .foregroundStyle(.white.opacity(0.34))
                            }
                            .foregroundStyle(.white.opacity(0.84))
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityHint("Select connected research node")
                    }
                }
            }

            Text(
                AtlasCopy.text(
                    "Descriptions organize the research index. Validate scientific claims against linked paper passages and methods.",
                    "这些说明用于组织研究索引；科学结论仍应以关联的论文段落与研究方法为准。",
                    language: language
                )
            )
            .font(.caption)
            .foregroundStyle(.white.opacity(0.40))
            .padding(.top, 2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var regionLabels: [String] {
        selectedNode.regions
            .components(separatedBy: CharacterSet(charactersIn: ",·"))
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
    }

    private var scientificCaveat: String {
        AtlasCopy.text(
            "\(selectedNode.status). Compare methods, spatial coverage, and uncertainty in the linked paper passages before treating this relationship as a standalone conclusion.",
            "\(selectedNode.status)。请结合论文中的研究方法、空间覆盖与不确定性理解这一关系，不应把图谱节点当作独立结论。",
            language: language
        )
    }
}

private struct InspectorSection<Content: View>: View {
    let title: String
    let symbol: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            Label(title, systemImage: symbol)
                .font(.caption2.weight(.semibold))
                .tracking(1.1)
                .foregroundStyle(.white.opacity(0.48))

            content()
                .font(.callout)
                .foregroundStyle(.white.opacity(0.84))
                .fixedSize(horizontal: false, vertical: true)
                .textSelection(.enabled)
        }
    }
}

private enum UniverseSearch {
    private static let aliases: [String: [String]] = [
        "Antarctic Ice Sheet": ["南极冰盖", "南极洲冰盖"],
        "CDW Intrusion": ["环南极深层水", "绕极深层水", "温水入侵", "暖水入侵", "cdw"],
        "Cross-shelf Heat Transport": ["跨陆架热输送", "跨冰架热输送", "热量输送"],
        "Ice-shelf Basal Melt": ["冰架基底融化", "基底融化", "冰架融化", "冰架底融"],
        "Freshwater Feedback": ["淡水反馈", "融水反馈", "淡化反馈"],
        "Buttressing": ["冰架支撑", "支撑效应", "背应力"],
        "Grounding Line Retreat": ["接地线后退", "接地线退缩", "接地线迁移", "接地线"],
        "MISI": ["海洋冰盖不稳定", "海洋冰盖不稳定性", "逆坡床", "misi"],
        "MICI": ["海洋冰崖不稳定", "水力压裂", "冰崖失稳", "mici"],
        "Basal Sliding": ["基底滑动", "冰底滑动", "底部摩擦"],
        "GIA": ["冰川均衡调整", "冰后回弹", "基岩回弹", "gia"],
        "Bed Topography": ["床面地形", "冰下地形", "基岩地形"],
        "Geothermal Heat Flux": ["地热通量", "地热热流"],
        "Subglacial Hydrology": ["冰下水文", "冰下湖", "冰下排水"],
        "Satellite Altimetry": ["卫星测高", "高度计", "表面高程"],
        "InSAR Velocity": ["insar", "雷达干涉", "冰流速度"],
        "GRACE / GRACE-FO": ["grace", "grace-fo", "卫星重力", "重力测量", "质量平衡"],
        "Radar & Field Data": ["雷达与野外数据", "探冰雷达", "野外观测"],
        "Pliocene": ["上新世", "中上新世"],
        "Last Interglacial": ["末次间冰期", "伊敏间冰期"],
        "Ice Cores": ["冰芯", "冰核"],
        "Marine Sediments": ["海洋沉积物", "海底沉积物", "沉积岩芯"],
        "Sea-level Contribution": ["海平面贡献", "海平面上升", "全球平均海平面"],
        "Coupled Models": ["耦合模型", "冰海耦合", "地球系统模型"],
        "Uncertainty Quantification": ["不确定性量化", "概率预测", "集合模拟"],
        "AI for Earth Observation": ["地球观测人工智能", "机器学习", "深度学习"],
    ]

    static func bestMatch(for query: String, in universe: ResearchUniverse) -> UniverseNode? {
        let normalizedQuery = normalize(query)
        guard !normalizedQuery.isEmpty else { return .core }

        return universe.nodes.max { left, right in
            score(left, for: normalizedQuery) < score(right, for: normalizedQuery)
        }.flatMap { score($0, for: normalizedQuery) > 0 ? $0 : .core }
    }

    static func directlyMatches(_ node: UniverseNode, query: String) -> Bool {
        let normalizedQuery = normalize(query)
        guard !normalizedQuery.isEmpty else { return true }
        return score(node, for: normalizedQuery) > 0
    }

    private static func score(_ node: UniverseNode, for normalizedQuery: String) -> Int {
        let phrases = [node.title] + (aliases[node.title] ?? [])
        let normalizedPhrases = phrases.map(normalize)
        var result = 0

        for phrase in normalizedPhrases where !phrase.isEmpty {
            if phrase == normalizedQuery {
                result = max(result, 1_000 + phrase.count)
            } else if normalizedQuery.contains(phrase) || phrase.contains(normalizedQuery) {
                result = max(result, 180 + min(80, phrase.count))
            }
        }

        let ownText = normalize([
            node.title,
            node.keyQuestion,
            node.evidenceSummary,
            node.status,
            node.regions,
            node.areaName ?? "",
        ].joined(separator: " "))
        if ownText.contains(normalizedQuery) {
            result += 120
        }

        let queryTokens = tokens(normalizedQuery)
        let candidateTokens = tokens(ownText + " " + normalizedPhrases.joined(separator: " "))
        result += queryTokens.intersection(candidateTokens).count * 18

        switch node.graphLevel {
        case 2: result += result > 0 ? 12 : 0
        case 1: result += result > 0 ? 6 : 0
        default: break
        }
        return result
    }

    private static func normalize(_ text: String) -> String {
        text.folding(
            options: [.caseInsensitive, .diacriticInsensitive, .widthInsensitive],
            locale: Locale(identifier: "en_US_POSIX")
        )
        .lowercased()
        .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func tokens(_ text: String) -> Set<String> {
        Set(
            text.split { !$0.isLetter && !$0.isNumber }
                .map(String.init)
                .filter { $0.count > 1 }
        )
    }
}

private extension UniverseNode {
    func directlyMatches(_ query: String) -> Bool {
        UniverseSearch.directlyMatches(self, query: query)
    }
}
