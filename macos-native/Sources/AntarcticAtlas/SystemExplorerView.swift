import SwiftUI

struct SystemExplorerView: View {
    @State private var selectedCase: AntarcticCaseStudy = .thwaites
    @State private var selectedLayers: Set<ObservationLayer> = [.altimetry]
    @State private var primaryLayer: ObservationLayer = .altimetry
    @State private var multiLayerMode = false
    @Environment(AppModel.self) private var appModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private let onOpenEvidence: ((AntarcticCaseStudy, ObservationLayer) -> Void)?

    init(onOpenEvidence: ((AntarcticCaseStudy, ObservationLayer) -> Void)? = nil) {
        self.onOpenEvidence = onOpenEvidence
    }

    var body: some View {
        ZStack {
            systemBackground

            GeometryReader { proxy in
                if proxy.size.width >= 960 {
                    HStack(spacing: 0) {
                        mainColumn
                            .frame(maxWidth: .infinity, maxHeight: .infinity)

                        if appModel.isInspectorPresented {
                            Divider().overlay(Color.white.opacity(0.10))
                                .transition(.opacity)

                            SystemInspector(
                                selectedCase: selectedCase,
                                selectedLayers: selectedLayers,
                                primaryLayer: $primaryLayer,
                                language: appModel.language,
                                onOpenEvidence: onOpenEvidence
                            )
                            .frame(width: min(368, proxy.size.width * 0.34))
                            .transition(
                                reduceMotion
                                    ? .opacity
                                    : .move(edge: .trailing).combined(with: .opacity)
                            )
                        }
                    }
                } else {
                    VStack(spacing: 0) {
                        mainColumn
                            .frame(maxWidth: .infinity, maxHeight: .infinity)

                        if appModel.isInspectorPresented {
                            Divider().overlay(Color.white.opacity(0.10))
                                .transition(.opacity)

                            SystemInspector(
                                selectedCase: selectedCase,
                                selectedLayers: selectedLayers,
                                primaryLayer: $primaryLayer,
                                language: appModel.language,
                                onOpenEvidence: onOpenEvidence
                            )
                            .frame(height: min(284, proxy.size.height * 0.40))
                            .transition(
                                reduceMotion
                                    ? .opacity
                                    : .move(edge: .bottom).combined(with: .opacity)
                            )
                        }
                    }
                }
            }
        }
        .animation(reduceMotion ? nil : .smooth(duration: 0.26), value: appModel.isInspectorPresented)
        .animation(reduceMotion ? nil : .smooth(duration: 0.42), value: selectedCase)
        .animation(reduceMotion ? nil : .smooth(duration: 0.28), value: selectedLayers)
        .onChange(of: multiLayerMode) { _, isEnabled in
            if !isEnabled {
                selectedLayers = [primaryLayer]
            } else if selectedLayers.count == 1 {
                selectedLayers = [.altimetry, .velocity, .gravity]
                primaryLayer = .velocity
            }
        }
        // Filtering remains live, but changing the scientific scene is an explicit
        // action: otherwise each typed character restarts the case/layer transition.
        .onChange(of: appModel.searchSubmissionToken) { _, _ in
            applySearch(appModel.searchText)
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Antarctic multi-sensor system explorer")
    }

    private var systemBackground: some View {
        ZStack {
            Color(red: 0.012, green: 0.035, blue: 0.073)

            LinearGradient(
                colors: [
                    Color(red: 0.03, green: 0.18, blue: 0.28).opacity(0.74),
                    Color(red: 0.01, green: 0.05, blue: 0.10).opacity(0.32),
                    Color.indigo.opacity(0.08),
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        }
        .ignoresSafeArea()
    }

    private var mainColumn: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            layerControls

            AntarcticSceneCanvas(
                selectedCase: selectedCase,
                selectedLayers: selectedLayers,
                primaryLayer: primaryLayer,
                language: appModel.language,
                reduceMotion: reduceMotion
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .frame(minHeight: 320)
            .layoutPriority(2)
            .padding(.horizontal, 22)
            .padding(.top, 12)
            .padding(.bottom, 14)

            MetricStrip(metrics: metrics)
                .padding(.horizontal, 22)

            caveat
                .padding(.horizontal, 22)
                .padding(.top, 12)
                .padding(.bottom, 18)
        }
    }

    private var header: some View {
        HStack(alignment: .center, spacing: 18) {
            VStack(alignment: .leading, spacing: 3) {
                Text(appModel.text("ANTARCTIC SYSTEM", "南极系统"))
                    .font(.caption2.weight(.semibold))
                    .tracking(1.6)
                    .foregroundStyle(Color.cyan.opacity(0.78))

                Text(appModel.text("Multi-sensor evidence, one physical system", "多源观测，同一个物理系统"))
                    .font(.title2.weight(.semibold))
                    .foregroundStyle(.white)
            }

            Spacer(minLength: 18)

            Picker(appModel.text("Case study", "研究场景"), selection: $selectedCase) {
                ForEach(visibleCaseStudies) { study in
                    Text(study.rawValue).tag(study)
                }
            }
            .pickerStyle(.menu)
            .frame(width: 210)
            .accessibilityHint("Changes the Antarctic case shown in the scene")

            Toggle(appModel.text("Multi-layer", "多图层"), isOn: $multiLayerMode)
                .toggleStyle(.switch)
                .help("Compare several observation systems on the same conceptual scene")
        }
        .padding(.horizontal, 24)
        .padding(.top, 22)
        .padding(.bottom, 14)
    }

    private var layerControls: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(appModel.text("OBSERVATION LAYERS", "观测图层"))
                    .font(.caption2.weight(.semibold))
                    .tracking(1.2)
                    .foregroundStyle(.secondary)

                Spacer()

                Text(
                    multiLayerMode
                        ? appModel.text("Select two or more signals to compare", "选择两种或更多信号进行对照")
                        : appModel.text("Select one primary signal", "选择一个主要观测信号")
                )
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }

            if !appModel.searchText.isEmpty {
                searchSummary
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(visibleObservationLayers) { layer in
                        Toggle(isOn: layerBinding(for: layer)) {
                            Label(layer.shortName, systemImage: layer.symbolName)
                                .font(.callout.weight(.medium))
                                .lineLimit(1)
                                .symbolEffect(
                                    .pulse,
                                    options: .nonRepeating,
                                    value: reduceMotion ? false : selectedLayers.contains(layer)
                                )
                        }
                        .toggleStyle(.button)
                        .buttonStyle(.bordered)
                        .tint(layer.tint)
                        .controlSize(.regular)
                        .help("\(layer.rawValue): \(layer.measure)")
                        .accessibilityHint(layer == primaryLayer ? "Primary visible layer" : "Add or select this observation layer")
                    }
                }
            }
        }
        .padding(.horizontal, 24)
    }

    private var caveat: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(Color.orange)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 3) {
                Text(appModel.text("Scientific caveat", "科学限制"))
                    .font(.caption.weight(.semibold))

                Text(
                    appModel.text(
                        "Conceptual synthesis—not raw satellite imagery. Geometry and signal magnitude are illustrative. \(selectedCase.caveat)",
                        "这是概念性综合图，并非原始卫星影像；几何形态和信号强度仅作说明。\(selectedCase.caveat)"
                    )
                )
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .background(Color.orange.opacity(0.08), in: RoundedRectangle(cornerRadius: 9, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 9, style: .continuous)
                .stroke(Color.orange.opacity(0.18), lineWidth: 1)
        }
        .accessibilityElement(children: .combine)
    }

    private var metrics: [ScienceMetric] {
        [
            ScienceMetric(
                title: appModel.text("LOCATION", "位置"),
                value: selectedCase.coordinates,
                detail: selectedCase.region,
                symbolName: "mappin.and.ellipse"
            ),
            ScienceMetric(
                title: appModel.text("ACTIVE EVIDENCE", "当前证据"),
                value: appModel.text(
                    "\(selectedLayers.count) \(selectedLayers.count == 1 ? "layer" : "layers")",
                    "\(selectedLayers.count) 个图层"
                ),
                detail: appModel.text("\(primaryLayer.shortName) is primary", "\(primaryLayer.shortName) 为主图层"),
                symbolName: "square.3.layers.3d"
            ),
            ScienceMetric(
                title: appModel.text("SPATIAL FOCUS", "空间尺度"),
                value: selectedCase.spatialScale,
                detail: selectedCase.systemType,
                symbolName: "scope"
            ),
        ]
    }

    private var searchSummary: some View {
        let caseCount = matchingCaseStudies.count
        let layerCount = matchingObservationLayers.count
        return HStack(spacing: 6) {
            Image(systemName: caseCount + layerCount == 0 ? "magnifyingglass" : "line.3.horizontal.decrease.circle")
            Text(
                caseCount + layerCount == 0
                    ? appModel.text("No exact case or observation match", "没有匹配的场景或观测图层")
                    : appModel.text(
                        "Showing \(caseCount) case \(caseCount == 1 ? "match" : "matches") and \(layerCount) observation \(layerCount == 1 ? "match" : "matches")",
                        "显示 \(caseCount) 个场景结果和 \(layerCount) 个观测结果"
                    )
            )
        }
        .font(.caption)
        .foregroundStyle(caseCount + layerCount == 0 ? Color.orange : Color.secondary)
        .accessibilityElement(children: .combine)
    }

    private var normalizedSearch: String {
        appModel.searchText.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var matchingCaseStudies: [AntarcticCaseStudy] {
        guard !normalizedSearch.isEmpty else { return Array(AntarcticCaseStudy.allCases) }
        return AntarcticCaseStudy.allCases.filter { study in
            [study.rawValue, study.region, study.coordinates, study.systemType, study.theme, study.context, study.caveat]
                .joined(separator: " ")
                .localizedCaseInsensitiveContains(normalizedSearch)
        }
    }

    private var matchingObservationLayers: [ObservationLayer] {
        guard !normalizedSearch.isEmpty else { return Array(ObservationLayer.allCases) }
        return ObservationLayer.allCases.filter { layer in
            [layer.rawValue, layer.shortName, layer.measure, layer.interpretation]
                .joined(separator: " ")
                .localizedCaseInsensitiveContains(normalizedSearch)
        }
    }

    private var visibleCaseStudies: [AntarcticCaseStudy] {
        normalizedSearch.isEmpty || matchingCaseStudies.isEmpty
            ? Array(AntarcticCaseStudy.allCases)
            : matchingCaseStudies
    }

    private var visibleObservationLayers: [ObservationLayer] {
        normalizedSearch.isEmpty || matchingObservationLayers.isEmpty
            ? Array(ObservationLayer.allCases)
            : matchingObservationLayers
    }

    private func layerBinding(for layer: ObservationLayer) -> Binding<Bool> {
        Binding(
            get: { selectedLayers.contains(layer) },
            set: { isSelected in
                update(layer: layer, isSelected: isSelected)
            }
        )
    }

    private func update(layer: ObservationLayer, isSelected: Bool) {
        if !multiLayerMode {
            selectedLayers = [layer]
            primaryLayer = layer
            return
        }

        if isSelected {
            selectedLayers.insert(layer)
            primaryLayer = layer
        } else if selectedLayers.count > 1 {
            selectedLayers.remove(layer)
            if primaryLayer == layer,
               let replacement = ObservationLayer.allCases.first(where: selectedLayers.contains) {
                primaryLayer = replacement
            }
        }
    }

    private func applySearch(_ value: String) {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        if let study = matchingCaseStudies.first {
            selectedCase = study
        }

        if let layer = matchingObservationLayers.first {
            primaryLayer = layer
            if multiLayerMode {
                selectedLayers.insert(layer)
            } else {
                selectedLayers = [layer]
            }
        }
    }
}

private struct AntarcticSceneCanvas: View {
    let selectedCase: AntarcticCaseStudy
    let selectedLayers: Set<ObservationLayer>
    let primaryLayer: ObservationLayer
    let language: AppLanguage
    let reduceMotion: Bool

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 24.0, paused: reduceMotion)) { timeline in
            let phase = reduceMotion ? 0.35 : timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 4.5) / 4.5

            ZStack(alignment: .topLeading) {
                ZStack {
                    Canvas { context, size in
                        drawBaseScene(context: &context, size: size)
                        drawCaseSignature(context: &context, size: size)
                    }
                    .id(selectedCase)
                    .transition(
                        reduceMotion
                            ? .opacity
                            : .opacity.combined(with: .scale(scale: 1.008))
                    )

                    ForEach(ObservationLayer.allCases.filter(selectedLayers.contains)) { layer in
                        Canvas { context, size in
                            draw(layer: layer, context: &context, size: size, phase: phase)
                        }
                        .id(layer)
                        .transition(
                            reduceMotion
                                ? .opacity
                                : .opacity.combined(with: .scale(scale: 0.992))
                        )
                        .allowsHitTesting(false)
                        .accessibilityHidden(true)
                    }
                }
                .accessibilityHidden(true)
                .animation(reduceMotion ? nil : .smooth(duration: 0.45), value: selectedCase)
                .animation(reduceMotion ? nil : .smooth(duration: 0.26), value: selectedLayers)

                sceneChrome(phase: phase)

                VStack(alignment: .leading, spacing: 5) {
                    Text(AtlasCopy.text("LIVE SYSTEM VIEW", "实时系统视图", language: language))
                        .font(.caption2.weight(.semibold))
                        .tracking(1.2)
                        .foregroundStyle(Color.cyan.opacity(0.82))

                    Text(selectedCase.rawValue)
                        .font(.title2.weight(.semibold))
                        .contentTransition(.opacity)

                    Label(selectedCase.region, systemImage: "mappin.and.ellipse")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(18)
                .shadow(color: .black.opacity(0.35), radius: 10, y: 4)

                VStack {
                    HStack {
                        Spacer()
                        activeLayerLegend
                    }
                    Spacer()
                }
                .padding(16)

                VStack {
                    Spacer()
                    HStack(alignment: .bottom) {
                        VStack(alignment: .leading, spacing: 5) {
                            Label(primaryLayer.shortName.uppercased(), systemImage: primaryLayer.symbolName)
                                .font(.caption2.weight(.semibold))
                                .tracking(0.8)
                                .foregroundStyle(primaryLayer.tint)
                            Text(primaryLayer.measure)
                                .font(.caption.weight(.medium))
                                .lineLimit(1)
                        }
                        .padding(.horizontal, 11)
                        .padding(.vertical, 8)
                        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 9, style: .continuous))
                        .overlay {
                            RoundedRectangle(cornerRadius: 9, style: .continuous)
                                .stroke(primaryLayer.tint.opacity(0.22), lineWidth: 1)
                        }
                        .contentTransition(.opacity)

                        Spacer()

                        HStack(spacing: 12) {
                            Label("\(selectedLayers.count)", systemImage: "square.3.layers.3d")
                            Text(selectedCase.coordinates)
                                .monospacedDigit()
                        }
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(.ultraThinMaterial, in: Capsule())
                    }
                    .padding(16)
                }
            }
            .background(Color(red: 0.02, green: 0.07, blue: 0.13))
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(Color.white.opacity(0.11), lineWidth: 1)
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel(
                AtlasCopy.text(
                    "Conceptual sensor scene for \(selectedCase.rawValue)",
                    "\(selectedCase.rawValue) 概念传感器场景",
                    language: language
                )
            )
            .accessibilityValue(
                AtlasCopy.text(
                    "\(selectedLayers.count) visible layers. Primary layer: \(primaryLayer.rawValue). \(selectedCase.context)",
                    "当前显示 \(selectedLayers.count) 个图层，主图层为 \(primaryLayer.rawValue)。\(selectedCase.context)",
                    language: language
                )
            )
        }
    }

    private var activeLayerLegend: some View {
        HStack(spacing: 7) {
            Text(AtlasCopy.text("SENSORS", "传感器", language: language))
                .font(.caption2.weight(.semibold))
                .tracking(0.9)
                .foregroundStyle(.secondary)

            ForEach(ObservationLayer.allCases.filter(selectedLayers.contains)) { layer in
                Image(systemName: layer.symbolName)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(layer.tint)
                    .frame(width: 20, height: 20)
                    .background(layer.tint.opacity(0.12), in: Circle())
                    .transition(.opacity.combined(with: .scale(scale: 0.72)))
                    .help(layer.rawValue)
                    .accessibilityLabel(layer.rawValue)
            }
        }
        .padding(.horizontal, 9)
        .padding(.vertical, 6)
        .background(.ultraThinMaterial, in: Capsule())
        .overlay {
            Capsule().stroke(Color.white.opacity(0.10), lineWidth: 1)
        }
        .animation(reduceMotion ? nil : .smooth(duration: 0.24), value: selectedLayers)
    }

    private func sceneChrome(phase: Double) -> some View {
        GeometryReader { proxy in
            ZStack {
                LinearGradient(
                    colors: [.white.opacity(0.06), .clear, .black.opacity(0.24)],
                    startPoint: .top,
                    endPoint: .bottom
                )

                Path { path in
                    path.move(to: CGPoint(x: proxy.size.width * 0.08, y: proxy.size.height * 0.18))
                    path.addLine(to: CGPoint(x: proxy.size.width * 0.08, y: proxy.size.height * 0.12))
                    path.addLine(to: CGPoint(x: proxy.size.width * 0.15, y: proxy.size.height * 0.12))

                    path.move(to: CGPoint(x: proxy.size.width * 0.85, y: proxy.size.height * 0.12))
                    path.addLine(to: CGPoint(x: proxy.size.width * 0.92, y: proxy.size.height * 0.12))
                    path.addLine(to: CGPoint(x: proxy.size.width * 0.92, y: proxy.size.height * 0.18))

                    path.move(to: CGPoint(x: proxy.size.width * 0.08, y: proxy.size.height * 0.82))
                    path.addLine(to: CGPoint(x: proxy.size.width * 0.08, y: proxy.size.height * 0.88))
                    path.addLine(to: CGPoint(x: proxy.size.width * 0.15, y: proxy.size.height * 0.88))

                    path.move(to: CGPoint(x: proxy.size.width * 0.85, y: proxy.size.height * 0.88))
                    path.addLine(to: CGPoint(x: proxy.size.width * 0.92, y: proxy.size.height * 0.88))
                    path.addLine(to: CGPoint(x: proxy.size.width * 0.92, y: proxy.size.height * 0.82))
                }
                .stroke(Color.cyan.opacity(0.20), style: StrokeStyle(lineWidth: 1, lineCap: .round))

                // A moving sweep is meaningful for altimetry; other sensors carry
                // their own motion semantics in the layer canvas rather than sharing
                // generic scanner chrome.
                if !reduceMotion && primaryLayer == .altimetry {
                    Rectangle()
                        .fill(
                            LinearGradient(
                                colors: [.clear, primaryLayer.tint.opacity(0.10), .clear],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(height: 1)
                        .offset(y: proxy.size.height * (phase - 0.5))
                        .blendMode(.screen)
                }
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }

    private func drawBaseScene(context: inout GraphicsContext, size: CGSize) {
        let bounds = CGRect(origin: .zero, size: size)
        context.fill(
            Path(bounds),
            with: .linearGradient(
                Gradient(colors: [
                    Color(red: 0.05, green: 0.17, blue: 0.25),
                    Color(red: 0.02, green: 0.09, blue: 0.16),
                    Color(red: 0.01, green: 0.04, blue: 0.09),
                ]),
                startPoint: CGPoint(x: 0, y: 0),
                endPoint: CGPoint(x: size.width, y: size.height)
            )
        )

        let horizonGlow = CGRect(
            x: -size.width * 0.12,
            y: size.height * 0.06,
            width: size.width * 1.22,
            height: size.height * 0.72
        )
        context.fill(
            Path(ellipseIn: horizonGlow),
            with: .radialGradient(
                Gradient(colors: [Color.cyan.opacity(0.14), Color.blue.opacity(0.05), .clear]),
                center: CGPoint(x: horizonGlow.midX, y: horizonGlow.midY),
                startRadius: 3,
                endRadius: horizonGlow.width * 0.52
            )
        )

        for index in 0..<34 {
            let x = Double((index * 89 + 17) % 997) / 997 * size.width
            let y = Double((index * 53 + 29) % 991) / 991 * size.height * 0.48
            let diameter = index.isMultiple(of: 7) ? 1.3 : 0.7
            context.fill(
                Path(ellipseIn: CGRect(x: x, y: y, width: diameter, height: diameter)),
                with: .color(.white.opacity(index.isMultiple(of: 6) ? 0.38 : 0.18))
            )
        }

        for index in 0..<11 {
            var path = Path()
            let x = size.width * Double(index) / 10
            path.move(to: CGPoint(x: x, y: 0))
            path.addLine(to: CGPoint(x: x - size.width * 0.14, y: size.height))
            context.stroke(path, with: .color(.white.opacity(0.035)), lineWidth: 0.6)
        }
        for index in 0..<8 {
            var path = Path()
            let y = size.height * Double(index) / 7
            path.move(to: CGPoint(x: 0, y: y))
            path.addLine(to: CGPoint(x: size.width, y: y - size.height * 0.08))
            context.stroke(path, with: .color(.cyan.opacity(0.045)), lineWidth: 0.6)
        }

        var ocean = Path()
        ocean.move(to: CGPoint(x: 0, y: size.height * 0.70))
        ocean.addCurve(
            to: CGPoint(x: size.width, y: size.height * 0.62),
            control1: CGPoint(x: size.width * 0.28, y: size.height * 0.61),
            control2: CGPoint(x: size.width * 0.70, y: size.height * 0.76)
        )
        ocean.addLine(to: CGPoint(x: size.width, y: size.height))
        ocean.addLine(to: CGPoint(x: 0, y: size.height))
        ocean.closeSubpath()
        context.fill(
            ocean,
            with: .linearGradient(
                Gradient(colors: [Color.cyan.opacity(0.17), Color.blue.opacity(0.34), Color.black.opacity(0.20)]),
                startPoint: CGPoint(x: size.width * 0.5, y: size.height * 0.60),
                endPoint: CGPoint(x: size.width * 0.5, y: size.height)
            )
        )

        for index in 0..<6 {
            let baseY = size.height * (0.70 + Double(index) * 0.047)
            var contour = Path()
            contour.move(to: CGPoint(x: 0, y: baseY))
            contour.addCurve(
                to: CGPoint(x: size.width, y: baseY - size.height * 0.035),
                control1: CGPoint(x: size.width * 0.28, y: baseY - size.height * 0.052),
                control2: CGPoint(x: size.width * 0.72, y: baseY + size.height * 0.032)
            )
            context.stroke(contour, with: .color(.cyan.opacity(0.07 + Double(index) * 0.012)), lineWidth: 0.8)
        }

        if selectedCase == .thwaites || selectedCase == .pineIsland || selectedCase == .totten {
            var heatPath = Path()
            heatPath.move(to: CGPoint(x: size.width * 0.96, y: size.height * 0.84))
            heatPath.addCurve(
                to: CGPoint(x: size.width * 0.63, y: size.height * 0.69),
                control1: CGPoint(x: size.width * 0.84, y: size.height * 0.74),
                control2: CGPoint(x: size.width * 0.74, y: size.height * 0.80)
            )
            context.stroke(
                heatPath,
                with: .linearGradient(
                    Gradient(colors: [.orange.opacity(0.06), .orange.opacity(0.46)]),
                    startPoint: CGPoint(x: size.width * 0.96, y: size.height * 0.84),
                    endPoint: CGPoint(x: size.width * 0.63, y: size.height * 0.69)
                ),
                style: StrokeStyle(lineWidth: 3.2, lineCap: .round)
            )
        }

        let profile = iceProfile(in: size)
        context.fill(
            profile,
            with: .linearGradient(
                Gradient(colors: [.white.opacity(0.76), Color.cyan.opacity(0.34), Color.blue.opacity(0.22)]),
                startPoint: CGPoint(x: 0, y: size.height * 0.22),
                endPoint: CGPoint(x: size.width * 0.76, y: size.height * 0.80)
            )
        )
        context.stroke(profile, with: .color(.white.opacity(0.52)), lineWidth: 1.2)

        for index in 0..<4 {
            let fraction = Double(index) * 0.045
            var flowLine = Path()
            flowLine.move(to: CGPoint(x: size.width * 0.13, y: size.height * (0.58 + fraction)))
            flowLine.addCurve(
                to: CGPoint(x: size.width * 0.68, y: size.height * (0.66 + fraction * 0.32)),
                control1: CGPoint(x: size.width * 0.30, y: size.height * (0.37 + fraction)),
                control2: CGPoint(x: size.width * 0.52, y: size.height * (0.43 + fraction))
            )
            context.stroke(flowLine, with: .color(.white.opacity(0.10)), lineWidth: 0.8)
        }
    }

    private func iceProfile(in size: CGSize) -> Path {
        var path = Path()
        let startY = selectedCase == .larsenB ? size.height * 0.38 : size.height * 0.30
        path.move(to: CGPoint(x: size.width * 0.04, y: size.height * 0.74))
        path.addCurve(
            to: CGPoint(x: size.width * 0.66, y: size.height * 0.63),
            control1: CGPoint(x: size.width * 0.16, y: startY),
            control2: CGPoint(x: size.width * 0.47, y: size.height * 0.25)
        )
        path.addCurve(
            to: CGPoint(x: size.width * 0.82, y: size.height * 0.72),
            control1: CGPoint(x: size.width * 0.72, y: size.height * 0.65),
            control2: CGPoint(x: size.width * 0.76, y: size.height * 0.70)
        )
        path.addLine(to: CGPoint(x: size.width * 0.67, y: size.height * 0.83))
        path.addCurve(
            to: CGPoint(x: size.width * 0.04, y: size.height * 0.74),
            control1: CGPoint(x: size.width * 0.44, y: size.height * 0.89),
            control2: CGPoint(x: size.width * 0.18, y: size.height * 0.90)
        )
        path.closeSubpath()
        return path
    }

    private func drawCaseSignature(context: inout GraphicsContext, size: CGSize) {
        switch selectedCase {
        case .larsenB:
            for index in 0..<5 {
                var fracture = Path()
                let x = size.width * (0.34 + Double(index) * 0.075)
                fracture.move(to: CGPoint(x: x, y: size.height * 0.38))
                fracture.addLine(to: CGPoint(x: x + size.width * 0.035, y: size.height * 0.71))
                context.stroke(fracture, with: .color(.red.opacity(0.72)), lineWidth: 2.2)
            }

        case .wilkes:
            let basin = CGRect(
                x: size.width * 0.27,
                y: size.height * 0.58,
                width: size.width * 0.42,
                height: size.height * 0.27
            )
            context.fill(
                Path(ellipseIn: basin),
                with: .radialGradient(
                    Gradient(colors: [Color.blue.opacity(0.43), .clear]),
                    center: CGPoint(x: basin.midX, y: basin.midY),
                    startRadius: 2,
                    endRadius: basin.width * 0.55
                )
            )

        case .totten:
            for offset in [0.0, 0.055] {
                var channel = Path()
                channel.move(to: CGPoint(x: size.width * 0.18, y: size.height * (0.78 - offset)))
                channel.addLine(to: CGPoint(x: size.width * 0.58, y: size.height * (0.44 - offset)))
                context.stroke(channel, with: .color(.cyan.opacity(0.48)), lineWidth: 2.8)
            }

        case .pineIsland:
            let heat = CGRect(x: size.width * 0.48, y: size.height * 0.49, width: size.width * 0.24, height: size.height * 0.28)
            context.fill(
                Path(ellipseIn: heat),
                with: .radialGradient(
                    Gradient(colors: [Color.orange.opacity(0.34), .clear]),
                    center: CGPoint(x: heat.midX, y: heat.midY),
                    startRadius: 1,
                    endRadius: heat.width * 0.52
                )
            )

        case .thwaites:
            var groundingLine = Path()
            groundingLine.move(to: CGPoint(x: size.width * 0.59, y: size.height * 0.56))
            groundingLine.addLine(to: CGPoint(x: size.width * 0.70, y: size.height * 0.75))
            context.stroke(groundingLine, with: .color(.white.opacity(0.62)), style: StrokeStyle(lineWidth: 1.6, dash: [5, 5]))
        }
    }

    private func draw(
        layer: ObservationLayer,
        context: inout GraphicsContext,
        size: CGSize,
        phase: Double
    ) {
        switch layer {
        case .altimetry:
            for fraction in [0.27, 0.43, 0.59, 0.73] {
                var track = Path()
                let x = size.width * fraction
                track.move(to: CGPoint(x: x, y: size.height * 0.15))
                track.addLine(to: CGPoint(x: x - size.width * 0.08, y: size.height * 0.82))
                context.stroke(track, with: .color(layer.tint.opacity(0.56)), style: StrokeStyle(lineWidth: 1, dash: [4, 5]))
            }
            var scan = Path()
            let y = size.height * (0.24 + phase * 0.50)
            scan.move(to: CGPoint(x: size.width * 0.11, y: y))
            scan.addLine(to: CGPoint(x: size.width * 0.78, y: y - size.height * 0.05))
            context.stroke(scan, with: .color(layer.tint.opacity(0.74)), lineWidth: 2)

        case .velocity:
            for (index, fraction) in [0.43, 0.50, 0.57, 0.64].enumerated() {
                let start = CGPoint(x: size.width * (0.18 + Double(index) * 0.035), y: size.height * fraction)
                let baseLength = size.width * (0.17 + Double(index % 3) * 0.035)
                // Keep the field legible as a still illustration with Reduce Motion,
                // while each InSAR vector lengthens and relaxes at its own phase.
                let flow = reduceMotion
                    ? 0.0
                    : sin((phase * .pi * 2) + fraction * 8)
                let length = baseLength + size.width * 0.026 * flow
                let end = CGPoint(x: start.x + length, y: start.y + size.height * 0.035)
                let intensity = reduceMotion ? 0.84 : 0.80 + 0.14 * ((flow + 1) * 0.5)
                drawArrow(context: &context, from: start, to: end, color: layer.tint.opacity(intensity))
            }

        case .gravity:
            let field = CGRect(x: size.width * 0.22, y: size.height * 0.24, width: size.width * 0.50, height: size.height * 0.52)
            let massBreath = reduceMotion
                ? 0.5
                : 0.5 + 0.5 * sin(phase * .pi * 2)
            context.fill(
                Path(ellipseIn: field),
                with: .radialGradient(
                    Gradient(colors: [
                        layer.tint.opacity(0.36 + 0.20 * massBreath),
                        Color.orange.opacity(0.10 + 0.12 * massBreath),
                        .clear,
                    ]),
                    center: CGPoint(x: field.midX, y: field.midY),
                    startRadius: 2,
                    endRadius: field.width * 0.54
                )
            )

        case .geodesy:
            let stations = [(0.28, 0.54), (0.44, 0.64), (0.62, 0.47), (0.70, 0.67)]
            for (index, station) in stations.enumerated() {
                let point = CGPoint(x: size.width * station.0, y: size.height * station.1)
                let radius = 4.0 + (index.isMultiple(of: 2) ? phase * 2 : (1 - phase) * 2)
                context.fill(Path(ellipseIn: CGRect(x: point.x - radius, y: point.y - radius, width: radius * 2, height: radius * 2)), with: .color(layer.tint.opacity(0.92)))
                drawArrow(context: &context, from: point, to: CGPoint(x: point.x, y: point.y - 21), color: layer.tint.opacity(0.72))
            }

        case .radar:
            for (index, fraction) in [0.43, 0.56, 0.68].enumerated() {
                let echoBreath = reduceMotion
                    ? 0.5
                    : 0.5 + 0.5 * sin((phase * .pi * 2) + Double(index))
                var echo = Path()
                echo.move(to: CGPoint(x: size.width * 0.18, y: size.height * fraction))
                echo.addCurve(
                    to: CGPoint(x: size.width * 0.68, y: size.height * (fraction - 0.08)),
                    control1: CGPoint(x: size.width * 0.34, y: size.height * (fraction - 0.03)),
                    control2: CGPoint(x: size.width * 0.52, y: size.height * (fraction + 0.04))
                )
                context.stroke(
                    echo,
                    with: .color(layer.tint.opacity(0.58 + 0.30 * echoBreath)),
                    lineWidth: 1.5
                )
            }

        case .cores:
            let sites = [(0.69, 0.73), (0.76, 0.63), (0.83, 0.78)]
            for (index, site) in sites.enumerated() {
                let point = CGPoint(x: size.width * site.0, y: size.height * site.1)
                let radius = 5.0 + (index == 1 ? phase : 1 - phase) * 2
                context.fill(Path(ellipseIn: CGRect(x: point.x - radius, y: point.y - radius, width: radius * 2, height: radius * 2)), with: .color(layer.tint.opacity(0.92)))
                var core = Path()
                core.move(to: point)
                core.addLine(to: CGPoint(x: point.x, y: point.y + size.height * 0.11))
                context.stroke(core, with: .color(layer.tint.opacity(0.70)), lineWidth: 2.4)
            }
        }
    }

    private func drawArrow(
        context: inout GraphicsContext,
        from start: CGPoint,
        to end: CGPoint,
        color: Color
    ) {
        var path = Path()
        path.move(to: start)
        path.addLine(to: end)
        path.move(to: end)
        path.addLine(to: CGPoint(x: end.x - 10, y: end.y - 6))
        path.move(to: end)
        path.addLine(to: CGPoint(x: end.x - 10, y: end.y + 6))
        context.stroke(path, with: .color(color), style: StrokeStyle(lineWidth: 2.2, lineCap: .round, lineJoin: .round))
    }
}

private struct MetricStrip: View {
    let metrics: [ScienceMetric]

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            ForEach(Array(metrics.enumerated()), id: \.element.id) { index, metric in
                if index > 0 {
                    Divider()
                        .frame(height: 54)
                        .padding(.horizontal, 16)
                }

                HStack(alignment: .top, spacing: 9) {
                    Image(systemName: metric.symbolName)
                        .font(.callout)
                        .foregroundStyle(Color.cyan.opacity(0.80))
                        .frame(width: 18)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(metric.title)
                            .font(.caption2.weight(.semibold))
                            .tracking(0.9)
                            .foregroundStyle(.tertiary)
                        Text(metric.value)
                            .font(.callout.weight(.semibold))
                            .lineLimit(1)
                        Text(metric.detail)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .accessibilityElement(children: .combine)
            }
        }
        .padding(.vertical, 11)
        .padding(.horizontal, 14)
        .background(Color.black.opacity(0.15), in: RoundedRectangle(cornerRadius: 11, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 11, style: .continuous)
                .stroke(Color.white.opacity(0.08), lineWidth: 1)
        }
    }
}

private struct SystemInspector: View {
    let selectedCase: AntarcticCaseStudy
    let selectedLayers: Set<ObservationLayer>
    @Binding var primaryLayer: ObservationLayer
    let language: AppLanguage
    let onOpenEvidence: ((AntarcticCaseStudy, ObservationLayer) -> Void)?

    private var orderedLayers: [ObservationLayer] {
        ObservationLayer.allCases.filter(selectedLayers.contains)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                VStack(alignment: .leading, spacing: 7) {
                    Text(AtlasCopy.text("CASE STUDY", "研究场景", language: language))
                        .font(.caption2.weight(.semibold))
                        .tracking(1.3)
                        .foregroundStyle(Color.cyan.opacity(0.78))

                    Text(selectedCase.rawValue)
                        .font(.title2.weight(.semibold))
                        .textSelection(.enabled)

                    Text(selectedCase.systemType)
                        .font(.caption.weight(.medium))
                        .foregroundStyle(.secondary)

                    Text(selectedCase.context)
                        .font(.callout)
                        .foregroundStyle(.primary.opacity(0.88))
                        .fixedSize(horizontal: false, vertical: true)
                        .textSelection(.enabled)
                }

                Divider()

                VStack(alignment: .leading, spacing: 9) {
                    Label(
                        AtlasCopy.text("ACTIVE OBSERVATIONS", "当前观测", language: language),
                        systemImage: "square.3.layers.3d"
                    )
                        .font(.caption2.weight(.semibold))
                        .tracking(1.1)
                        .foregroundStyle(.secondary)

                    ForEach(orderedLayers) { layer in
                        Button {
                            primaryLayer = layer
                        } label: {
                            HStack(spacing: 9) {
                                Image(systemName: layer.symbolName)
                                    .foregroundStyle(layer.tint)
                                    .frame(width: 18)
                                Text(layer.shortName)
                                Spacer()
                                if layer == primaryLayer {
                                    Text(AtlasCopy.text("PRIMARY", "主图层", language: language))
                                        .font(.caption2.weight(.semibold))
                                        .foregroundStyle(layer.tint)
                                }
                            }
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityHint("Make this the primary observation in the inspector")
                    }
                }

                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Label(primaryLayer.rawValue.uppercased(), systemImage: primaryLayer.symbolName)
                            .font(.caption2.weight(.semibold))
                            .tracking(1.0)
                            .foregroundStyle(primaryLayer.tint)
                        Spacer()
                    }

                    Text(primaryLayer.measure)
                        .font(.headline)

                    Text(selectedCase.observation(for: primaryLayer))
                        .font(.callout)
                        .fixedSize(horizontal: false, vertical: true)
                        .textSelection(.enabled)

                    Text(primaryLayer.interpretation)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                        .textSelection(.enabled)
                }

                if orderedLayers.count > 1 {
                    Divider()

                    VStack(alignment: .leading, spacing: 8) {
                        Label(
                            AtlasCopy.text("SYNTHESIS", "综合解读", language: language),
                            systemImage: "point.3.connected.trianglepath.dotted"
                        )
                            .font(.caption2.weight(.semibold))
                            .tracking(1.1)
                            .foregroundStyle(.secondary)

                        Text(
                            AtlasCopy.text(
                                "Together, \(orderedLayers.map(\.shortName).joined(separator: ", ")) connect \(selectedCase.theme.lowercased()).",
                                "\(orderedLayers.map(\.shortName).joined(separator: "、")) 共同连接了这一科学主题：\(selectedCase.theme)。",
                                language: language
                            )
                        )
                            .font(.callout)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                if let onOpenEvidence {
                    Button {
                        onOpenEvidence(selectedCase, primaryLayer)
                    } label: {
                        Label(
                            AtlasCopy.text("Open supporting evidence", "打开支持证据", language: language),
                            systemImage: "doc.text.magnifyingglass"
                        )
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                    .tint(primaryLayer.tint)
                }

                Text(
                    AtlasCopy.text(
                        "Observation summaries explain what each sensor contributes; they do not replace calibrated products, uncertainty estimates, or source methods.",
                        "观测摘要用于说明各传感器提供的证据维度，不能替代完成标定的数据产品、不确定性估计或原始方法。",
                        language: language
                    )
                )
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .padding(22)
        }
        .background(.regularMaterial)
        .accessibilityElement(children: .contain)
        .accessibilityLabel(AtlasCopy.text("System evidence inspector", "系统证据检查器", language: language))
    }
}
