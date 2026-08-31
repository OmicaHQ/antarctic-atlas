import SwiftUI

struct MiniLabView: View {
    @Environment(AppModel.self) private var appModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var scenario: AALabScenario = .glacierFlow
    @State private var preset: AALabPreset = .thwaites

    // Glacier flow simulator
    @State private var simulationYear = 2050.0
    @State private var flowAirTemperature = 1.2
    @State private var flowOceanForcing = 1.8
    @State private var flowSnowfall = 0.6
    @State private var flowShelfThickness = 185.0
    @State private var flowBasalResistance = 42.0
    @State private var flowBedSlope = 3.1
    @State private var misiEnabled = true
    @State private var shelfCollapseEnabled = false
    @State private var warmWaterEnabled = true

    // Ice-shelf buttressing experiment
    @State private var buttressShelfThickness = 260.0
    @State private var buttressOceanForcing = 1.0
    @State private var pinningStrength = 55.0
    @State private var calvingLoss = 20.0
    @State private var lateralConfinement = 60.0
    @State private var buttressBedSlope = 1.5

    // Hydrofracture experiment
    @State private var surfaceMelt = 45.0
    @State private var firnCapacity = 45.0
    @State private var crevasseDensity = 40.0
    @State private var shelfStrength = 60.0
    @State private var oceanSwell = 35.0
    @State private var collapseStage = 2

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                header
                scenarioBar
                interpretationBanner

                ViewThatFits(in: .horizontal) {
                    HStack(alignment: .top, spacing: 20) {
                        controls.frame(width: 350)
                        results.frame(minWidth: 560)
                    }
                    VStack(spacing: 20) {
                        controls
                        results
                    }
                }
            }
            .padding(28)
            .frame(maxWidth: 1_300, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .background(Color(nsColor: .windowBackgroundColor).ignoresSafeArea())
        .onAppear { apply(preset) }
        .onChange(of: preset) { _, newPreset in
            guard scenario == .glacierFlow else { return }
            apply(newPreset)
        }
        .onChange(of: scenario) { _, _ in resetCurrentScenario() }
        .onChange(of: appModel.searchSubmissionToken) { _, _ in applySharedSearch() }
        .navigationTitle(appModel.text("Mini Research Lab", "迷你研究实验室"))
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 18) {
            Image(systemName: "testtube.2")
                .font(.system(size: 28, weight: .semibold))
                .foregroundStyle(.tint)
                .frame(width: 52, height: 52)
                .background(.tint.opacity(0.12), in: RoundedRectangle(cornerRadius: 14))
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 5) {
                Text(appModel.text("Mini Research Lab", "迷你研究实验室"))
                    .font(.largeTitle.weight(.semibold))
                Text(appModel.text(
                    "Three focused conceptual experiments for Antarctic ice dynamics.",
                    "三个聚焦于南极冰盖动力学机制的概念实验。"
                ))
                .font(.title3)
                .foregroundStyle(.secondary)
            }
        }
    }

    private var scenarioBar: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 18) {
                scenarioPicker
                scenarioAccessory
            }
            VStack(alignment: .leading, spacing: 12) {
                scenarioPicker
                scenarioAccessory
            }
        }
        .padding(14)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private var scenarioPicker: some View {
        Picker(appModel.text("Experiment", "实验"), selection: $scenario) {
            ForEach(filteredScenarios) { item in
                Label(appModel.text(item.title, item.chineseTitle), systemImage: item.symbol).tag(item)
            }
        }
        .pickerStyle(.segmented)
        .accessibilityLabel(appModel.text("Experiment", "实验"))
    }

    @ViewBuilder
    private var scenarioAccessory: some View {
        if scenario == .glacierFlow {
            Picker(appModel.text("Preset", "预设"), selection: $preset) {
                ForEach(AALabPreset.allCases) { item in
                    Text(appModel.text(item.title, item.chineseTitle)).tag(item)
                }
            }
            .pickerStyle(.menu)
            .fixedSize()
        } else {
            Label(appModel.text("Mechanism study", "机制研究"), systemImage: "scope")
                .font(.callout.weight(.medium))
                .foregroundStyle(.secondary)
                .fixedSize()
        }
    }

    private var interpretationBanner: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: scenario.symbol)
                .foregroundStyle(scenario.tint)
                .frame(width: 20)
            VStack(alignment: .leading, spacing: 3) {
                Text(appModel.text(scenario.labTitle, scenario.chineseLabTitle))
                    .font(.headline)
                Text(appModel.text(scenario.description, scenario.chineseDescription))
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(scenario.tint.opacity(0.10), in: RoundedRectangle(cornerRadius: 14))
        .accessibilityElement(children: .combine)
        .animation(responseAnimation, value: scenario)
    }

    @ViewBuilder
    private var controls: some View {
        switch scenario {
        case .glacierFlow: flowControls
        case .buttressing: buttressingControls
        case .hydrofracture: hydrofractureControls
        }
    }

    private var flowControls: some View {
        controlsCard {
            AALabSlider(
                title: appModel.text("Simulation year", "模拟年份"),
                value: $simulationYear, range: 2025...2100, step: 1, suffix: "",
                valueFormat: { String(Int($0.rounded())) },
                note: appModel.text("Later years strengthen the accumulated ocean and shelf-loss response.", "更晚的年份会增强累积的海洋与冰架损失响应。")
            )
            AALabSlider(
                title: appModel.text("Air-temperature anomaly", "气温距平"),
                value: $flowAirTemperature, range: -3...4, suffix: " °C",
                note: appModel.text("Warmer air increases conceptual surface-melt pressure.", "空气变暖会增加概念性的表面融化压力。")
            )
            AALabSlider(
                title: appModel.text("Ocean heat forcing", "海洋热强迫"),
                value: $flowOceanForcing, range: 0...3, suffix: " °C",
                note: appModel.text("Warm water below the shelf promotes thinning near the grounding line.", "冰架下方的暖水会促进接地线附近冰体变薄。")
            )
            AALabSlider(
                title: appModel.text("Snow accumulation", "降雪累积"),
                value: $flowSnowfall, range: 0...2.5, suffix: " m/yr",
                note: appModel.text("Accumulation partly offsets the conceptual loss signal.", "降雪累积会部分抵消概念性的冰损失信号。")
            )
            AALabSlider(
                title: appModel.text("Ice-shelf thickness", "冰架厚度"),
                value: $flowShelfThickness, range: 50...500, step: 5, suffix: " m",
                valueFormat: { String(Int($0.rounded())) },
                note: appModel.text("A thicker shelf retains more downstream support.", "较厚的冰架能保留更多下游支撑。")
            )
            AALabSlider(
                title: appModel.text("Basal resistance", "基底阻力"),
                value: $flowBasalResistance, range: 0...100, suffix: "%",
                note: appModel.text("Lower resistance allows grounded ice to move faster.", "阻力较低时，接地冰可以更快地流动。")
            )
            AALabSlider(
                title: appModel.text("Retrograde bed strength", "逆坡基底强度"),
                value: $flowBedSlope, range: 0...5, suffix: "°",
                note: appModel.text("A stronger inland-deepening bed increases retreat feedback.", "更强的内陆加深基底会增强后退反馈。")
            )
            flowFeedbackControls
        }
    }

    private var buttressingControls: some View {
        controlsCard {
            AALabSlider(
                title: appModel.text("Ice-shelf thickness", "冰架厚度"),
                value: $buttressShelfThickness, range: 50...500, step: 5, suffix: " m",
                valueFormat: { String(Int($0.rounded())) },
                note: appModel.text("Thicker shelves provide stronger mechanical support.", "较厚的冰架能提供更强的机械支撑。")
            )
            AALabSlider(
                title: appModel.text("Ocean temperature forcing", "海洋温度强迫"),
                value: $buttressOceanForcing, range: 0...3, suffix: " °C",
                note: appModel.text("Warmer water increases basal melt below the floating shelf.", "更暖的海水会增加浮冰架下方的基底融化。")
            )
            AALabSlider(
                title: appModel.text("Pinning-point strength", "固定点强度"),
                value: $pinningStrength, range: 0...100, suffix: "%",
                note: appModel.text("Bedrock highs hold a shelf in place and transmit back stress.", "基岩高地可以固定冰架，并传递背应力。")
            )
            AALabSlider(
                title: appModel.text("Calving / shelf loss", "崩解／冰架损失"),
                value: $calvingLoss, range: 0...100, suffix: "%",
                note: appModel.text("Removed floating area weakens the connection to grounded ice.", "损失的浮冰面积会削弱与接地冰之间的联系。")
            )
            AALabSlider(
                title: appModel.text("Lateral confinement", "侧向约束"),
                value: $lateralConfinement, range: 0...100, suffix: "%",
                note: appModel.text("Embayment walls resist shelf spreading.", "海湾侧壁会阻止冰架扩展。")
            )
            AALabSlider(
                title: appModel.text("Retrograde bed slope", "逆坡基底坡度"),
                value: $buttressBedSlope, range: 0...5, suffix: "°",
                note: appModel.text("A stronger retrograde slope increases grounding-line retreat pressure.", "更强的逆坡会增加接地线后退压力。")
            )
        }
    }

    private var hydrofractureControls: some View {
        controlsCard {
            AALabSlider(
                title: appModel.text("Surface melt intensity", "表面融化强度"),
                value: $surfaceMelt, range: 0...100, suffix: "%",
                note: appModel.text("More meltwater creates larger surface ponds.", "更多融水会形成更大的表面积水池。")
            )
            AALabSlider(
                title: appModel.text("Firn air capacity", "粒雪层储水能力"),
                value: $firnCapacity, range: 0...100, suffix: "%",
                note: appModel.text("Porous firn can absorb meltwater before it enters crevasses.", "多孔粒雪层可在融水进入裂隙前先行吸收。")
            )
            AALabSlider(
                title: appModel.text("Crevasse density", "裂隙密度"),
                value: $crevasseDensity, range: 0...100, suffix: "%",
                note: appModel.text("Existing crevasses make connected fracture pathways more likely.", "既有裂隙会让连通破裂路径更容易形成。")
            )
            AALabSlider(
                title: appModel.text("Ice-shelf strength", "冰架强度"),
                value: $shelfStrength, range: 0...100, suffix: "%",
                note: appModel.text("Stronger ice resists fracture propagation and breakup.", "更坚固的冰体能抵抗裂隙扩展与破碎。")
            )
            AALabSlider(
                title: appModel.text("Ocean swell / flexure", "海浪／弯曲作用"),
                value: $oceanSwell, range: 0...100, suffix: "%",
                note: appModel.text("Flexure can help fractures widen and connect.", "弯曲作用可以帮助裂隙变宽并相互连通。")
            )
            AALabCollapseStageControl(
                title: appModel.text("Collapse stage", "崩塌阶段"),
                stage: $collapseStage,
                stageTitle: collapseStageTitle(collapseStage),
                note: appModel.text("Move through intact shelf, ponds, cracks, fragmentation, and acceleration.", "依次查看完整冰架、积水池、裂隙、碎裂与加速阶段。")
            )
        }
    }

    private var flowFeedbackControls: some View {
        VStack(alignment: .leading, spacing: 9) {
            Text(appModel.text("Feedback pathways", "反馈路径"))
                .font(.callout.weight(.semibold))
                .padding(.top, 3)
            Toggle(appModel.text("Enable MISI feedback", "启用 MISI 反馈"), isOn: $misiEnabled)
            Toggle(appModel.text("Ice-shelf collapse", "冰架崩解"), isOn: $shelfCollapseEnabled)
            Toggle(appModel.text("CDW warm-water intrusion", "CDW 暖水入侵"), isOn: $warmWaterEnabled)
        }
        .toggleStyle(.switch)
        .font(.callout)
    }

    private func controlsCard<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Label(appModel.text("Assumptions", "场景假设"), systemImage: "slider.horizontal.3")
                    .font(.title3.weight(.semibold))
                Spacer()
                Button(appModel.text("Reset", "重置")) { resetCurrentScenario() }
                    .buttonStyle(.link)
            }
            content()
        }
        .padding(20)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(.white.opacity(0.09))
        }
    }

    private var results: some View {
        VStack(spacing: 18) {
            sceneCard
            diagnosis
            metricGrid
        }
        .animation(responseAnimation, value: scenario)
        .animation(responseAnimation, value: simulationYear)
        .animation(responseAnimation, value: flowAirTemperature)
        .animation(responseAnimation, value: flowOceanForcing)
        .animation(responseAnimation, value: flowShelfThickness)
        .animation(responseAnimation, value: flowBasalResistance)
        .animation(responseAnimation, value: buttressShelfThickness)
        .animation(responseAnimation, value: buttressOceanForcing)
        .animation(responseAnimation, value: pinningStrength)
        .animation(responseAnimation, value: calvingLoss)
        .animation(responseAnimation, value: lateralConfinement)
        .animation(responseAnimation, value: surfaceMelt)
        .animation(responseAnimation, value: firnCapacity)
        .animation(responseAnimation, value: crevasseDensity)
        .animation(responseAnimation, value: shelfStrength)
        .animation(responseAnimation, value: oceanSwell)
        .animation(responseAnimation, value: collapseStage)
    }

    private var sceneCard: some View {
        VStack(alignment: .leading, spacing: 13) {
            HStack(alignment: .firstTextBaseline) {
                Label(appModel.text(scenario.canvasTitle, scenario.chineseCanvasTitle), systemImage: scenario.symbol)
                    .font(.headline)
                    .foregroundStyle(scenario.tint)
                Spacer()
                Text(sceneStatus)
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 9)
                    .padding(.vertical, 4)
                    .background(scenario.tint.opacity(0.12), in: Capsule())
            }
            sceneCanvas
                .frame(height: 284)
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            Text(appModel.text(scenario.canvasGuide, scenario.chineseCanvasGuide))
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(scenario.tint.opacity(0.18))
        }
    }

    @ViewBuilder
    private var sceneCanvas: some View {
        switch scenario {
        case .glacierFlow:
            AALabFlowScene(
                flowSignal: metrics.flowSignal,
                retreatSignal: metrics.retreatSignal,
                shelfThickness: flowShelfThickness,
                oceanForcing: flowOceanForcing,
                warmWaterEnabled: warmWaterEnabled,
                shelfCollapseEnabled: shelfCollapseEnabled
            )
        case .buttressing:
            AALabButtressingScene(
                shelfThickness: buttressShelfThickness,
                oceanForcing: buttressOceanForcing,
                pinningStrength: pinningStrength,
                calvingLoss: calvingLoss,
                lateralConfinement: lateralConfinement,
                buttressing: metrics.buttressing,
                velocity: metrics.flowSignal
            )
        case .hydrofracture:
            AALabHydrofractureScene(
                stage: metrics.stage,
                autoStage: metrics.autoStage,
                ponding: metrics.ponding,
                fracture: metrics.fracture,
                crevasseDensity: crevasseDensity,
                collapseRisk: metrics.collapseRisk,
                buttressingRemaining: metrics.buttressing,
                velocity: metrics.flowSignal
            )
        }
    }

    private var sceneStatus: String {
        switch scenario {
        case .glacierFlow:
            let flags = [
                misiEnabled ? appModel.text("MISI", "MISI") : nil,
                warmWaterEnabled ? appModel.text("warm CDW", "暖 CDW") : nil,
                shelfCollapseEnabled ? appModel.text("shelf loss", "冰架损失") : nil
            ].compactMap { $0 }
            return flags.isEmpty ? appModel.text("baseline", "基础情景") : flags.joined(separator: " · ")
        case .buttressing:
            return appModel.text("Back stress \(Int(metrics.buttressing.rounded())) / 100", "背应力 \(Int(metrics.buttressing.rounded())) / 100")
        case .hydrofracture:
            return appModel.text("Stage \(metrics.stage) · \(collapseStageTitle(metrics.stage))", "阶段 \(metrics.stage) · \(collapseStageTitle(metrics.stage))")
        }
    }

    private var metricGrid: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 150), spacing: 12)], spacing: 12) {
            switch scenario {
            case .glacierFlow:
                AALabMetricCard(
                    title: appModel.text("Ice-loss pressure", "冰损失压力"),
                    value: metrics.lossIndex.formatted(.number.precision(.fractionLength(0))),
                    unit: "/ 100", normalizedValue: metrics.lossIndex / 100, symbol: "waveform.path.ecg"
                )
                AALabMetricCard(
                    title: appModel.text("Grounding-line retreat", "接地线后退"),
                    value: metrics.retreatSignal.formatted(.number.precision(.fractionLength(1))),
                    unit: appModel.text("concept km", "概念千米"), normalizedValue: metrics.retreatSignal / 68, symbol: "arrow.down.right"
                )
                AALabMetricCard(
                    title: appModel.text("Ice-flow velocity", "冰流速度"),
                    value: metrics.flowSignal.formatted(.number.precision(.fractionLength(2))),
                    unit: appModel.text("relative", "相对值"), normalizedValue: metrics.flowSignal / 3.6, symbol: "gauge.with.dots.needle.67percent"
                )
                AALabMetricCard(
                    title: appModel.text("Sea-level signal", "海平面信号"),
                    value: metrics.seaLevelSignal.formatted(.number.precision(.fractionLength(2))),
                    unit: appModel.text("concept m", "概念米"), normalizedValue: metrics.seaLevelSignal / 0.9, symbol: "water.waves"
                )
            case .buttressing:
                AALabMetricCard(
                    title: appModel.text("Buttressing index", "支撑指数"),
                    value: metrics.buttressing.formatted(.number.precision(.fractionLength(0))),
                    unit: "/ 100", normalizedValue: metrics.buttressing / 100, symbol: "arrow.left.and.right.righttriangle.left.righttriangle.right"
                )
                AALabMetricCard(
                    title: appModel.text("Grounded-ice velocity", "接地冰速度"),
                    value: metrics.flowSignal.formatted(.number.precision(.fractionLength(0))),
                    unit: "m/yr", normalizedValue: metrics.flowSignal / 1_350, symbol: "gauge.with.dots.needle.67percent"
                )
                AALabMetricCard(
                    title: appModel.text("Retreat pressure", "后退压力"),
                    value: metrics.retreatSignal.formatted(.number.precision(.fractionLength(1))),
                    unit: appModel.text("concept km", "概念千米"), normalizedValue: metrics.retreatSignal / 45, symbol: "arrow.down.right"
                )
                AALabMetricCard(
                    title: appModel.text("Sea-level signal", "海平面信号"),
                    value: metrics.seaLevelSignal.formatted(.number.precision(.fractionLength(2))),
                    unit: appModel.text("concept m", "概念米"), normalizedValue: metrics.seaLevelSignal / 0.55, symbol: "water.waves"
                )
            case .hydrofracture:
                AALabMetricCard(
                    title: appModel.text("Ponding index", "积水指数"),
                    value: (metrics.ponding * 100).formatted(.number.precision(.fractionLength(0))),
                    unit: "/ 100", normalizedValue: metrics.ponding, symbol: "drop.fill"
                )
                AALabMetricCard(
                    title: appModel.text("Fracture index", "裂缝指数"),
                    value: (metrics.fracture * 100).formatted(.number.precision(.fractionLength(0))),
                    unit: "/ 100", normalizedValue: metrics.fracture, symbol: "bolt.horizontal.fill"
                )
                AALabMetricCard(
                    title: appModel.text("Buttressing remaining", "剩余支撑"),
                    value: metrics.buttressing.formatted(.number.precision(.fractionLength(0))),
                    unit: "/ 100", normalizedValue: metrics.buttressing / 100, symbol: "rectangle.compress.vertical"
                )
                AALabMetricCard(
                    title: appModel.text("Post-collapse velocity", "崩塌后速度"),
                    value: metrics.flowSignal.formatted(.number.precision(.fractionLength(0))),
                    unit: "m/yr", normalizedValue: metrics.flowSignal / 2_100, symbol: "arrow.right.circle.fill"
                )
            }
        }
        .animation(responseAnimation, value: metrics.lossIndex)
    }

    private var diagnosis: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: metrics.lossIndex > 65 ? "exclamationmark.triangle.fill" : "lightbulb.fill")
                .foregroundStyle(metrics.lossIndex > 65 ? Color.orange : scenario.tint)
            VStack(alignment: .leading, spacing: 5) {
                Text(appModel.text("Reading this run", "如何解读本次运行")).font(.headline)
                Text(diagnosisText).foregroundStyle(.secondary).textSelection(.enabled)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.quaternary, in: RoundedRectangle(cornerRadius: 16))
        .accessibilityElement(children: .combine)
    }

    private var metrics: AALabMetrics {
        switch scenario {
        case .glacierFlow:
            let timeFactor = aaClamp((simulationYear - 2025) / 75)
            let effectiveOcean = flowOceanForcing + (warmWaterEnabled ? 1.2 : 0.2) * timeFactor
            let effectiveShelf = max(20, flowShelfThickness * (shelfCollapseEnabled ? (1 - 0.45 * timeFactor) : (1 - 0.12 * timeFactor)))
            let basalFriction = flowBasalResistance / 100
            var retreat = 8 + effectiveOcean * 7 + flowBedSlope * 5 - effectiveShelf * 0.045 - basalFriction * 9
            if misiEnabled && flowBedSlope > 1.5 && effectiveOcean > 0.5 {
                retreat *= 1 + 0.55 * flowBedSlope + 0.25 * effectiveOcean
            }
            if shelfCollapseEnabled { retreat *= 1.45 }
            if warmWaterEnabled { retreat *= 1.18 }
            retreat = aaClamp(retreat, to: 0...68)
            var velocityStrength = max(0.08, 0.35 + effectiveOcean * 0.30 + (1 - basalFriction) * 1.45 + flowBedSlope * 0.18 + timeFactor * 0.45)
            if misiEnabled && retreat > 20 { velocityStrength *= 1.45 }
            if shelfCollapseEnabled { velocityStrength *= 1.35 }
            let velocity = min(3.6, velocityStrength * 1.8)
            let airMeltPressure = max(0, (flowAirTemperature + 2.3) * 3.2)
            let iceLoss = ((airMeltPressure + max(effectiveOcean, 0) * 2.6) * (1.25 - basalFriction * 0.65) / (flowSnowfall + 0.5))
            let lossIndex = aaClamp(iceLoss * 14 + retreat * 0.65, to: 0...100)
            return .init(lossIndex: lossIndex, retreatSignal: retreat, flowSignal: velocity, seaLevelSignal: retreat * 0.013, buttressing: min(100, effectiveShelf / 4.2), ponding: 0, fracture: 0, collapseRisk: lossIndex, stage: 0, autoStage: 0)
        case .buttressing:
            let thicknessFactor = aaClamp(buttressShelfThickness / 700)
            let pinningFactor = aaClamp(pinningStrength / 100)
            let lateralFactor = aaClamp(lateralConfinement / 100)
            let calvingFactor = aaClamp(calvingLoss / 100)
            let oceanFactor = aaClamp(buttressOceanForcing / 3)
            var buttressing = 100 * (0.45 * thicknessFactor + 0.30 * pinningFactor + 0.25 * lateralFactor)
            buttressing *= 1 - 0.75 * calvingFactor
            buttressing *= 1 - 0.45 * oceanFactor
            buttressing = aaClamp(buttressing, to: 0...100)
            let velocity = 180 + (100 - buttressing) * 8.5 + oceanFactor * 260 + buttressBedSlope * 55
            let retreat = aaClamp((100 - buttressing) * 0.18 + oceanFactor * 8 + buttressBedSlope * 2, to: 0...45)
            return .init(lossIndex: 100 - buttressing, retreatSignal: retreat, flowSignal: velocity, seaLevelSignal: retreat * 0.011, buttressing: buttressing, ponding: 0, fracture: 0, collapseRisk: 100 - buttressing, stage: 0, autoStage: 0)
        case .hydrofracture:
            let ponding = aaClamp((surfaceMelt * 0.75 - firnCapacity * 0.45 + 20) / 100)
            let fracture = aaClamp(0.45 * ponding + 0.30 * (crevasseDensity / 100) + 0.20 * (oceanSwell / 100) - 0.25 * (shelfStrength / 100))
            let collapseRisk = aaClamp(100 * (0.55 * fracture + 0.35 * ponding + 0.10 * (oceanSwell / 100)), to: 0...100)
            let autoStage: Int
            switch collapseRisk {
            case ..<25: autoStage = 0
            case ..<45: autoStage = 1
            case ..<65: autoStage = 2
            case ..<82: autoStage = 3
            default: autoStage = 4
            }
            let stage = max(collapseStage, autoStage)
            let buttressing = aaClamp(100 - collapseRisk * 0.85 - (stage >= 3 ? 25 : 0), to: 0...100)
            let velocity = 300 + (100 - buttressing) * 18
            return .init(lossIndex: collapseRisk, retreatSignal: 0, flowSignal: velocity, seaLevelSignal: (100 - buttressing) * 0.018, buttressing: buttressing, ponding: ponding, fracture: fracture, collapseRisk: collapseRisk, stage: stage, autoStage: autoStage)
        }
    }

    private var diagnosisText: String {
        switch scenario {
        case .glacierFlow:
            let active = [
                misiEnabled ? appModel.text("MISI feedback", "MISI 反馈") : nil,
                warmWaterEnabled ? appModel.text("CDW warm-water access", "CDW 暖水进入") : nil,
                shelfCollapseEnabled ? appModel.text("ice-shelf loss", "冰架损失") : nil
            ].compactMap { $0 }.joined(separator: " · ")
            return appModel.text(
                "Orange flow arrows and moving cyan parcels show how lower basal resistance and downstream shelf loss increase ice discharge. Active pathways: \(active.isEmpty ? "baseline only" : active).",
                "橙色流动箭头与移动的青色冰体颗粒展示了较低基底阻力和下游冰架损失如何提高冰体排放。当前路径：\(active.isEmpty ? "仅基础情景" : active)。"
            )
        case .buttressing:
            return appModel.text(
                "Blue arrows are the shelf's back stress. At \(metrics.buttressing.formatted(.number.precision(.fractionLength(0)))) / 100, thickness, pinning, and lateral confinement still oppose orange inland flow; calving and warm water weaken that bridge.",
                "蓝色箭头表示冰架的背应力。当前为 \(metrics.buttressing.formatted(.number.precision(.fractionLength(0)))) / 100：厚度、固定点与侧向约束仍在抵抗橙色的内陆冰流；崩解和暖水会削弱这条支撑通路。"
            )
        case .hydrofracture:
            return appModel.text(
                "The automatic diagnosis is stage \(metrics.autoStage), while the displayed sequence is stage \(metrics.stage): \(collapseStageTitle(metrics.stage)). Melt ponds feed red water-filled cracks; after fragmentation, orange arrows show accelerated inland flow.",
                "自动诊断为第 \(metrics.autoStage) 阶段，当前展示为第 \(metrics.stage) 阶段：\(collapseStageTitle(metrics.stage))。积水池会补给红色充水裂缝；冰架碎裂后，橙色箭头展示内陆冰流的加速响应。"
            )
        }
    }

    private var filteredScenarios: [AALabScenario] {
        let query = appModel.searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return AALabScenario.allCases }
        return AALabScenario.allCases.filter {
            [$0.title, $0.chineseTitle, $0.searchTerms].joined(separator: " ").localizedCaseInsensitiveContains(query)
        }
    }

    private var responseAnimation: Animation? { reduceMotion ? nil : .smooth(duration: 0.28) }

    private func apply(_ preset: AALabPreset) {
        let values = preset.flowValues
        withAnimation(responseAnimation) {
            simulationYear = values.year
            flowAirTemperature = values.air
            flowOceanForcing = values.ocean
            flowSnowfall = values.snowfall
            flowShelfThickness = values.shelf
            flowBasalResistance = values.basal
            flowBedSlope = values.bed
            misiEnabled = values.misi
            shelfCollapseEnabled = values.collapse
            warmWaterEnabled = values.warmWater
        }
    }

    private func resetCurrentScenario() {
        switch scenario {
        case .glacierFlow:
            apply(preset)
        case .buttressing:
            withAnimation(responseAnimation) {
                buttressShelfThickness = 260
                buttressOceanForcing = 1
                pinningStrength = 55
                calvingLoss = 20
                lateralConfinement = 60
                buttressBedSlope = 1.5
            }
        case .hydrofracture:
            withAnimation(responseAnimation) {
                surfaceMelt = 45
                firnCapacity = 45
                crevasseDensity = 40
                shelfStrength = 60
                oceanSwell = 35
                collapseStage = 2
            }
        }
    }

    private func applySharedSearch() {
        guard let match = filteredScenarios.first, !filteredScenarios.contains(scenario) else { return }
        scenario = match
    }

    private func collapseStageTitle(_ stage: Int) -> String {
        let index = min(4, max(0, stage))
        let english = ["Intact shelf", "Melt ponds form", "Water-filled cracks deepen", "Shelf fragments", "Breakup and flow acceleration"]
        let chinese = ["完整冰架", "融水池形成", "充水裂缝加深", "冰架碎裂", "破碎并加速流动"]
        return appModel.text(english[index], chinese[index])
    }
}

private struct AALabSlider: View {
    let title: String
    @Binding var value: Double
    let range: ClosedRange<Double>
    var step: Double? = nil
    let suffix: String
    var valueFormat: ((Double) -> String)? = nil
    let note: String

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack {
                Text(title).font(.callout.weight(.medium))
                Spacer()
                Text(displayValue + suffix).font(.callout.monospacedDigit()).foregroundStyle(.secondary)
            }
            slider.accessibilityLabel(title).accessibilityValue(displayValue + suffix)
            Text(note).font(.caption).foregroundStyle(.tertiary).fixedSize(horizontal: false, vertical: true)
        }
    }

    @ViewBuilder
    private var slider: some View {
        if let step {
            Slider(value: $value, in: range, step: step)
        } else {
            Slider(value: $value, in: range)
        }
    }

    private var displayValue: String {
        valueFormat?(value) ?? value.formatted(.number.precision(.fractionLength(1)))
    }
}

private struct AALabCollapseStageControl: View {
    let title: String
    @Binding var stage: Int
    let stageTitle: String
    let note: String

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack {
                Text(title).font(.callout.weight(.medium))
                Spacer()
                Text("\(stage) · \(stageTitle)").font(.caption.monospacedDigit()).foregroundStyle(.secondary).lineLimit(1)
            }
            Slider(
                value: Binding(get: { Double(stage) }, set: { stage = min(4, max(0, Int($0.rounded()))) }),
                in: 0...4,
                step: 1
            )
            .accessibilityLabel(title)
            .accessibilityValue("Stage \(stage): \(stageTitle)")
            HStack {
                ForEach(0...4, id: \.self) { value in
                    Text("\(value)").font(.caption2.monospacedDigit()).foregroundStyle(value == stage ? .primary : .tertiary).frame(maxWidth: .infinity)
                }
            }
            Text(note).font(.caption).foregroundStyle(.tertiary).fixedSize(horizontal: false, vertical: true)
        }
    }
}

private struct AALabMetricCard: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let title: String
    let value: String
    let unit: String
    let normalizedValue: Double
    let symbol: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label(title, systemImage: symbol).font(.caption.weight(.medium)).foregroundStyle(.secondary)
                Spacer()
            }
            HStack(alignment: .firstTextBaseline, spacing: 5) {
                metricValue
                Text(unit).font(.caption).foregroundStyle(.secondary)
            }
            Gauge(value: aaClamp(normalizedValue)) { EmptyView() }
                .gaugeStyle(.accessoryLinearCapacity)
                .tint(normalizedValue > 0.72 ? Color.orange : Color.accentColor)
                .accessibilityHidden(true)
        }
        .padding(15)
        .frame(maxWidth: .infinity, minHeight: 120, alignment: .leading)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title), \(value) \(unit)")
    }

    @ViewBuilder
    private var metricValue: some View {
        if reduceMotion {
            Text(value).font(.title2.weight(.semibold).monospacedDigit())
        } else {
            Text(value).font(.title2.weight(.semibold).monospacedDigit()).contentTransition(.numericText())
        }
    }
}

private struct AALabFlowScene: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let flowSignal: Double
    let retreatSignal: Double
    let shelfThickness: Double
    let oceanForcing: Double
    let warmWaterEnabled: Bool
    let shelfCollapseEnabled: Bool

    var body: some View {
        TimelineView(.periodic(from: .now, by: reduceMotion ? 60 : 1.0 / 24.0)) { timeline in
            let phase = reduceMotion ? 0.18 : timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 4.2) / 4.2
            Canvas { context, size in draw(in: &context, size: size, phase: phase) }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Conceptual glacier-flow cross-section")
        .accessibilityValue("Moving ice parcels show a flow signal of \(flowSignal.formatted(.number.precision(.fractionLength(2)))) and grounding-line retreat of \(retreatSignal.formatted(.number.precision(.fractionLength(1)))) concept kilometres.")
    }

    private func draw(in context: inout GraphicsContext, size: CGSize, phase: Double) {
        let width = size.width
        let height = size.height
        guard width > 10, height > 10 else { return }

        context.fill(Path(CGRect(origin: .zero, size: size)), with: .linearGradient(
            Gradient(colors: [Color(red: 0.018, green: 0.075, blue: 0.15), Color(red: 0.025, green: 0.14, blue: 0.24)]),
            startPoint: .zero, endPoint: CGPoint(x: width, y: height)
        ))

        let groundingX = width * (0.59 - aaClamp(retreatSignal / 68) * 0.13)
        let waterLine = height * 0.69
        var water = Path()
        water.addRect(CGRect(x: 0, y: waterLine, width: width, height: height - waterLine))
        context.fill(water, with: .linearGradient(
            Gradient(colors: [.cyan.opacity(0.30), .blue.opacity(0.08)]),
            startPoint: CGPoint(x: 0, y: waterLine), endPoint: CGPoint(x: width, y: height)
        ))

        var bed = Path()
        bed.move(to: CGPoint(x: 0, y: height * 0.80))
        bed.addCurve(to: CGPoint(x: width, y: height * 0.91), control1: CGPoint(x: width * 0.28, y: height * 0.67), control2: CGPoint(x: width * 0.72, y: height * 0.98))
        bed.addLine(to: CGPoint(x: width, y: height))
        bed.addLine(to: CGPoint(x: 0, y: height))
        bed.closeSubpath()
        context.fill(bed, with: .color(Color(red: 0.20, green: 0.15, blue: 0.11).opacity(0.78)))

        var groundedIce = Path()
        groundedIce.move(to: CGPoint(x: 0, y: height * 0.27))
        groundedIce.addCurve(to: CGPoint(x: groundingX, y: height * 0.53), control1: CGPoint(x: width * 0.18, y: height * 0.23), control2: CGPoint(x: groundingX * 0.70, y: height * 0.38))
        groundedIce.addLine(to: CGPoint(x: groundingX, y: waterLine))
        groundedIce.addLine(to: CGPoint(x: 0, y: height * 0.80))
        groundedIce.closeSubpath()
        context.fill(groundedIce, with: .linearGradient(
            Gradient(colors: [.white.opacity(0.96), .cyan.opacity(0.48), .blue.opacity(0.54)]),
            startPoint: CGPoint(x: width * 0.15, y: height * 0.20), endPoint: CGPoint(x: groundingX, y: height * 0.76)
        ))
        context.stroke(groundedIce, with: .color(.white.opacity(0.68)), lineWidth: 1.3)

        let shelfDepth = 0.08 + aaClamp(shelfThickness / 500) * 0.10
        let shelfEnd = shelfCollapseEnabled ? width * 0.78 : width * 0.94
        var shelf = Path()
        shelf.move(to: CGPoint(x: groundingX, y: height * 0.53))
        shelf.addLine(to: CGPoint(x: shelfEnd, y: height * (0.54 + shelfDepth * 0.20)))
        shelf.addLine(to: CGPoint(x: shelfEnd, y: height * (0.63 + shelfDepth)))
        shelf.addLine(to: CGPoint(x: groundingX, y: waterLine))
        shelf.closeSubpath()
        context.fill(shelf, with: .color(.cyan.opacity(shelfCollapseEnabled ? 0.44 : 0.65)))
        context.stroke(shelf, with: .color(.white.opacity(0.50)), lineWidth: 1)

        if shelfCollapseEnabled {
            let removed = Path(CGRect(x: shelfEnd, y: height * 0.54, width: width * 0.15, height: height * 0.16))
            context.stroke(removed, with: .color(.gray.opacity(0.7)), style: StrokeStyle(lineWidth: 1.2, dash: [5, 4]))
            aaDrawTag(&context, "lost shelf area", at: CGPoint(x: width * 0.87, y: height * 0.48), color: .orange)
        }

        var groundingLine = Path()
        groundingLine.move(to: CGPoint(x: groundingX, y: height * 0.43))
        groundingLine.addLine(to: CGPoint(x: groundingX, y: height * 0.79))
        context.stroke(groundingLine, with: .color(.red.opacity(0.92)), style: StrokeStyle(lineWidth: 2.4, dash: [5, 4]))

        if warmWaterEnabled || oceanForcing > 0.4 {
            let intensity = aaClamp(oceanForcing / 3)
            let warm = Path(ellipseIn: CGRect(x: groundingX + width * 0.02, y: waterLine - 10, width: width * (0.16 + 0.12 * intensity), height: height * (0.12 + 0.08 * intensity)))
            context.fill(warm, with: .color(.orange.opacity(0.10 + 0.20 * intensity)))
            aaDrawTag(&context, "warm CDW", at: CGPoint(x: groundingX + width * 0.16, y: waterLine + height * 0.17), color: .orange)
        }

        let speed = aaClamp(flowSignal / 3.6, to: 0.10...1)
        for row in 0..<5 {
            let y = height * (0.39 + Double(row) * 0.062)
            for index in 0..<12 {
                let offset = (Double(index) / 12 + Double(row) * 0.065 + phase * (0.28 + 0.62 * speed)).truncatingRemainder(dividingBy: 1)
                let x = width * 0.06 + offset * max(30, groundingX - width * 0.12)
                let dotSize = 3.2 + 1.5 * speed
                context.fill(Path(ellipseIn: CGRect(x: x - dotSize, y: y - dotSize, width: dotSize * 2, height: dotSize * 2)), with: .color(.cyan.opacity(0.82)))
            }
        }
        for index in 0..<5 {
            let y = height * (0.38 + Double(index) * 0.074)
            let start = CGPoint(x: width * (0.08 + Double(index % 2) * 0.04), y: y)
            aaDrawArrow(&context, from: start, to: CGPoint(x: min(groundingX - 10, start.x + width * (0.10 + 0.10 * speed)), y: y - 1), color: .orange.opacity(0.92), width: 1.8 + 2.4 * speed)
        }

        aaDrawTag(&context, "grounded ice", at: CGPoint(x: width * 0.22, y: height * 0.22), color: .white)
        aaDrawTag(&context, "floating shelf", at: CGPoint(x: (groundingX + shelfEnd) / 2, y: height * 0.46), color: .cyan)
        aaDrawTag(&context, "grounding line", at: CGPoint(x: groundingX, y: height * 0.86), color: .red)
        aaDrawTag(&context, "moving ice parcels", at: CGPoint(x: width * 0.25, y: height * 0.93), color: .cyan)
    }
}

private struct AALabButtressingScene: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let shelfThickness: Double
    let oceanForcing: Double
    let pinningStrength: Double
    let calvingLoss: Double
    let lateralConfinement: Double
    let buttressing: Double
    let velocity: Double

    var body: some View {
        TimelineView(.periodic(from: .now, by: reduceMotion ? 60 : 1.0 / 20.0)) { timeline in
            let phase = reduceMotion ? 0.5 : timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 2.8) / 2.8
            Canvas { context, size in draw(in: &context, size: size, phase: phase) }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Conceptual ice-shelf buttressing experiment")
        .accessibilityValue("Back stress \(buttressing.formatted(.number.precision(.fractionLength(0)))) out of 100; calving loss \(calvingLoss.formatted(.number.precision(.fractionLength(0)))) percent.")
    }

    private func draw(in context: inout GraphicsContext, size: CGSize, phase: Double) {
        let width = size.width
        let height = size.height
        guard width > 10, height > 10 else { return }

        context.fill(Path(CGRect(origin: .zero, size: size)), with: .linearGradient(
            Gradient(colors: [Color(red: 0.02, green: 0.10, blue: 0.18), Color(red: 0.05, green: 0.18, blue: 0.28)]),
            startPoint: .zero, endPoint: CGPoint(x: width, y: height)
        ))

        let groundingX = width * 0.39
        let shelfMid = height * 0.53
        let fullShelfLength = width * 0.48
        let remainingLength = fullShelfLength * (1 - aaClamp(calvingLoss / 100))
        let shelfHeight = height * (0.10 + 0.17 * aaClamp(shelfThickness / 500))
        let shelfEnd = groundingX + remainingLength
        let oceanTop = height * 0.30
        var ocean = Path()
        ocean.addRect(CGRect(x: groundingX, y: oceanTop, width: width - groundingX, height: height * 0.48))
        context.fill(ocean, with: .color(.cyan.opacity(0.12)))

        var bed = Path()
        bed.move(to: CGPoint(x: 0, y: height * 0.79))
        bed.addCurve(to: CGPoint(x: width, y: height * 0.70), control1: CGPoint(x: width * 0.28, y: height * 0.76), control2: CGPoint(x: width * 0.72, y: height * 0.90))
        bed.addLine(to: CGPoint(x: width, y: height))
        bed.addLine(to: CGPoint(x: 0, y: height))
        bed.closeSubpath()
        context.fill(bed, with: .color(Color(red: 0.27, green: 0.18, blue: 0.11).opacity(0.86)))

        let grounded = Path(roundedRect: CGRect(x: width * 0.07, y: shelfMid - height * 0.20, width: groundingX - width * 0.07, height: height * 0.39), cornerRadius: 8)
        context.fill(grounded, with: .color(.blue.opacity(0.82)))
        context.stroke(grounded, with: .color(.cyan.opacity(0.75)), lineWidth: 1.4)

        let shelfRect = CGRect(x: groundingX, y: shelfMid - shelfHeight / 2, width: max(6, remainingLength), height: shelfHeight)
        let shelf = Path(roundedRect: shelfRect, cornerRadius: 7)
        context.fill(shelf, with: .color(.cyan.opacity(0.72)))
        context.stroke(shelf, with: .color(.white.opacity(0.58)), lineWidth: 1.2)
        if calvingLoss > 1 {
            let removed = Path(roundedRect: CGRect(x: shelfEnd, y: shelfMid - shelfHeight * 0.58, width: max(8, fullShelfLength - remainingLength), height: shelfHeight * 1.16), cornerRadius: 5)
            context.stroke(removed, with: .color(.gray.opacity(0.78)), style: StrokeStyle(lineWidth: 1.5, dash: [6, 5]))
            aaDrawTag(&context, "calved / lost shelf", at: CGPoint(x: min(width * 0.86, shelfEnd + width * 0.09), y: shelfMid - shelfHeight), color: .gray)
        }
        if lateralConfinement > 2 {
            let alpha = 0.10 + 0.28 * aaClamp(lateralConfinement / 100)
            let upperWall = Path(roundedRect: CGRect(x: groundingX, y: shelfRect.minY - height * 0.09, width: max(10, remainingLength), height: height * 0.045), cornerRadius: 5)
            let lowerWall = Path(roundedRect: CGRect(x: groundingX, y: shelfRect.maxY + height * 0.045, width: max(10, remainingLength), height: height * 0.045), cornerRadius: 5)
            context.fill(upperWall, with: .color(.indigo.opacity(alpha)))
            context.fill(lowerWall, with: .color(.indigo.opacity(alpha)))
            aaDrawTag(&context, "lateral confinement", at: CGPoint(x: groundingX + max(55, remainingLength * 0.45), y: shelfRect.minY - height * 0.14), color: .indigo)
        }
        if remainingLength > 28 && pinningStrength > 1 {
            let pinX = groundingX + remainingLength * 0.58
            let radius = 12 + 24 * aaClamp(pinningStrength / 100)
            let pin = Path(ellipseIn: CGRect(x: pinX - radius, y: shelfRect.maxY + height * 0.10 - radius * 0.58, width: radius * 2, height: radius * 1.16))
            context.fill(pin, with: .color(.brown.opacity(0.92)))
            context.stroke(pin, with: .color(.orange.opacity(0.72)), lineWidth: 1.2)
            aaDrawTag(&context, "pinning point", at: CGPoint(x: pinX, y: shelfRect.maxY + height * 0.24), color: .orange)
        }

        var groundingLine = Path()
        groundingLine.move(to: CGPoint(x: groundingX, y: shelfRect.minY - height * 0.13))
        groundingLine.addLine(to: CGPoint(x: groundingX, y: shelfRect.maxY + height * 0.19))
        context.stroke(groundingLine, with: .color(.red.opacity(0.92)), style: StrokeStyle(lineWidth: 2.5, dash: [5, 4]))

        let speed = aaClamp((velocity - 180) / 1_150, to: 0.10...1)
        for index in 0..<5 {
            let y = shelfMid - height * 0.13 + Double(index) * height * 0.065
            aaDrawArrow(&context, from: CGPoint(x: width * (0.10 + Double(index % 2) * 0.045), y: y), to: CGPoint(x: groundingX - width * 0.025, y: y), color: .orange.opacity(0.92), width: 1.8 + 2.5 * speed)
        }
        let support = aaClamp(buttressing / 100)
        let pulse = 0.82 + 0.18 * sin(phase * .pi * 2)
        for index in 0..<4 {
            let y = shelfMid - height * 0.10 + Double(index) * height * 0.068
            aaDrawArrow(&context, from: CGPoint(x: groundingX + width * (0.04 + 0.17 * support), y: y), to: CGPoint(x: groundingX - width * (0.018 + 0.11 * support), y: y), color: .blue.opacity(0.50 + 0.40 * pulse), width: 1.8 + 3.0 * support)
        }
        if oceanForcing > 0.04 {
            let warm = Path(ellipseIn: CGRect(x: groundingX + width * 0.13, y: shelfRect.maxY + height * 0.02, width: width * (0.16 + 0.08 * aaClamp(oceanForcing / 3)), height: height * 0.16))
            context.fill(warm, with: .color(.orange.opacity(0.10 + 0.18 * aaClamp(oceanForcing / 3))))
            aaDrawTag(&context, "ocean melt", at: CGPoint(x: groundingX + width * 0.26, y: shelfRect.maxY + height * 0.26), color: .orange)
        }

        aaDrawTag(&context, "grounded ice", at: CGPoint(x: width * 0.19, y: shelfRect.minY - height * 0.16), color: .white)
        aaDrawTag(&context, "floating ice shelf", at: CGPoint(x: groundingX + max(58, remainingLength * 0.45), y: shelfRect.minY - height * 0.04), color: .cyan)
        aaDrawTag(&context, "blue = back stress", at: CGPoint(x: width * 0.21, y: height * 0.92), color: .blue)
        aaDrawTag(&context, "orange = inland flow", at: CGPoint(x: width * 0.63, y: height * 0.92), color: .orange)
    }
}

private struct AALabHydrofractureScene: View, Animatable {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let autoStage: Int
    var stageProgress: Double
    var ponding: Double
    var fracture: Double
    let crevasseDensity: Double
    let collapseRisk: Double
    let buttressingRemaining: Double
    let velocity: Double

    init(stage: Int, autoStage: Int, ponding: Double, fracture: Double, crevasseDensity: Double, collapseRisk: Double, buttressingRemaining: Double, velocity: Double) {
        self.autoStage = autoStage
        stageProgress = Double(stage)
        self.ponding = ponding
        self.fracture = fracture
        self.crevasseDensity = crevasseDensity
        self.collapseRisk = collapseRisk
        self.buttressingRemaining = buttressingRemaining
        self.velocity = velocity
    }

    var animatableData: AnimatablePair<Double, AnimatablePair<Double, Double>> {
        get { AnimatablePair(stageProgress, AnimatablePair(ponding, fracture)) }
        set {
            stageProgress = newValue.first
            ponding = newValue.second.first
            fracture = newValue.second.second
        }
    }

    var body: some View {
        TimelineView(.periodic(from: .now, by: reduceMotion ? 60 : 1.0 / 20.0)) { timeline in
            let phase = reduceMotion ? 0.25 : timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 3.2) / 3.2
            Canvas { context, size in draw(in: &context, size: size, phase: phase) }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Hydrofracture and ice-shelf collapse sequence")
        .accessibilityValue("Displayed stage \(displayedStage), automatic diagnosis \(autoStage), collapse risk \(collapseRisk.formatted(.number.precision(.fractionLength(0)))) out of 100.")
    }

    private var displayedStage: Int { min(4, max(0, Int(stageProgress.rounded()))) }

    private func draw(in context: inout GraphicsContext, size: CGSize, phase: Double) {
        let width = size.width
        let height = size.height
        guard width > 10, height > 10 else { return }

        context.fill(Path(CGRect(origin: .zero, size: size)), with: .linearGradient(
            Gradient(colors: [Color(red: 0.015, green: 0.09, blue: 0.20), Color(red: 0.02, green: 0.18, blue: 0.31)]),
            startPoint: .zero, endPoint: CGPoint(x: width, y: height)
        ))
        for index in 0..<6 {
            let y = height * (0.15 + Double(index) * 0.13)
            var wave = Path()
            wave.move(to: CGPoint(x: width * 0.04, y: y))
            wave.addCurve(to: CGPoint(x: width * 0.96, y: y + 8), control1: CGPoint(x: width * 0.35, y: y - 5), control2: CGPoint(x: width * 0.65, y: y + 14))
            context.stroke(wave, with: .color(.white.opacity(0.07)), lineWidth: 0.8)
        }

        let shelf = CGRect(x: width * 0.16, y: height * 0.35, width: width * 0.74, height: height * 0.25)
        let grounded = Path(roundedRect: CGRect(x: width * 0.06, y: shelf.minY - height * 0.05, width: width * 0.13, height: shelf.height + height * 0.10), cornerRadius: 7)
        context.fill(grounded, with: .color(.blue.opacity(0.84)))
        context.stroke(grounded, with: .color(.cyan.opacity(0.68)), lineWidth: 1.2)

        let fragmentation = aaClamp((stageProgress - 2.45) / 1.05)
        let breakup = aaClamp((stageProgress - 3.45) / 0.55)
        if fragmentation < 0.01 {
            let intact = Path(roundedRect: shelf, cornerRadius: 10)
            context.fill(intact, with: .color(.cyan.opacity(0.77)))
            context.stroke(intact, with: .color(.white.opacity(0.66)), lineWidth: 1.4)
        } else {
            let blocks: [(CGFloat, CGFloat, CGFloat, CGFloat)] = [(0.00, 0.18, 0.02, -0.04), (0.22, 0.18, -0.03, 0.06), (0.45, 0.18, 0.05, -0.03), (0.68, 0.16, -0.04, 0.05), (0.87, 0.13, 0.04, -0.06)]
            for (index, block) in blocks.enumerated() {
                let oscillation = reduceMotion ? 0 : 0.008 * sin(phase * .pi * 2 + Double(index))
                let drift = (Double(index.isMultiple(of: 2) ? 1 : -1) * (0.02 + 0.04 * breakup) + oscillation) * width
                let rect = CGRect(x: shelf.minX + shelf.width * block.0 + drift, y: shelf.minY + shelf.height * block.2, width: shelf.width * block.1, height: shelf.height * (0.87 + block.3))
                let shelfBlock = Path(roundedRect: rect, cornerRadius: 6)
                context.fill(shelfBlock, with: .color(.cyan.opacity(0.60 + 0.16 * (1 - breakup))))
                context.stroke(shelfBlock, with: .color(.white.opacity(0.64)), lineWidth: 1.2)
            }
        }

        let pondOpacity = aaClamp((stageProgress - 0.55) / 0.55)
        if pondOpacity > 0.01 {
            let ponds: [(CGFloat, CGFloat, CGFloat, CGFloat)] = [(0.20, 0.22, 0.055, 0.15), (0.36, 0.43, 0.068, 0.17), (0.53, 0.25, 0.061, 0.15), (0.69, 0.47, 0.070, 0.18), (0.83, 0.28, 0.056, 0.14)]
            let visibleCount = min(ponds.count, max(1, Int((ponding * Double(ponds.count) + 1).rounded())))
            for pond in ponds.prefix(visibleCount) {
                let rect = CGRect(x: shelf.minX + shelf.width * pond.0, y: shelf.minY + shelf.height * pond.1, width: shelf.width * pond.2, height: shelf.height * pond.3)
                context.fill(Path(ellipseIn: rect), with: .color(.blue.opacity(0.35 + 0.55 * pondOpacity)))
                context.stroke(Path(ellipseIn: rect), with: .color(.cyan.opacity(0.7)), lineWidth: 0.9)
            }
        }

        let crackOpacity = aaClamp((stageProgress - 1.45) / 0.55)
        if crackOpacity > 0.01 {
            let crackCount = min(5, max(2, Int((2 + crevasseDensity / 25).rounded())))
            let crackDepth = shelf.height * (0.35 + 0.60 * fracture) + stageProgress * 4
            for index in 0..<crackCount {
                let x = shelf.minX + shelf.width * (0.22 + Double(index) * 0.16)
                var crack = Path()
                crack.move(to: CGPoint(x: x, y: shelf.minY + 8))
                crack.addLine(to: CGPoint(x: x + 7 * sin(Double(index) + 1), y: shelf.minY + 18 + crackDepth * 0.38))
                crack.addLine(to: CGPoint(x: x - 6 * cos(Double(index) + 0.5), y: min(shelf.maxY + 18, shelf.minY + 15 + crackDepth)))
                context.stroke(crack, with: .color(.red.opacity(0.45 + 0.55 * crackOpacity)), lineWidth: 1.8 + 2.4 * crackOpacity)
            }
        }

        if breakup > 0.01 {
            let center = CGPoint(x: shelf.midX, y: shelf.midY)
            for index in 0..<16 {
                let angle = Double(index) * 2 * .pi / 16
                let inner = CGPoint(x: center.x + 8 * cos(angle), y: center.y + 8 * sin(angle))
                let radius = (24 + 28 * breakup + 6 * sin(Double(index) * 1.7)) * (reduceMotion ? 0.65 : 1)
                aaDrawArrow(&context, from: inner, to: CGPoint(x: center.x + radius * cos(angle), y: center.y + radius * 0.60 * sin(angle)), color: .white.opacity(0.38 + 0.48 * breakup), width: 0.9 + breakup)
            }
            aaDrawTag(&context, "ICE SHELF BREAKUP", at: CGPoint(x: shelf.midX, y: shelf.midY), color: .red)
        }

        let speed = aaClamp((velocity - 300) / 1_800, to: 0.15...1)
        for index in 0..<5 {
            let y = grounded.boundingRect.midY - height * 0.13 + Double(index) * height * 0.065
            aaDrawArrow(&context, from: CGPoint(x: width * 0.08, y: y), to: CGPoint(x: width * (0.19 + 0.14 * speed + 0.06 * breakup), y: y), color: .orange.opacity(0.86), width: 1.9 + 3.2 * speed)
        }

        aaDrawTag(&context, "\(displayedStage)  \(stageCaption(displayedStage))", at: CGPoint(x: width * 0.52, y: height * 0.13), color: .white)
        aaDrawTag(&context, "grounded ice", at: CGPoint(x: width * 0.12, y: shelf.minY - height * 0.10), color: .white)
        aaDrawTag(&context, "floating ice shelf", at: CGPoint(x: shelf.midX, y: shelf.minY - height * 0.06), color: .cyan)
        if pondOpacity > 0.01 { aaDrawTag(&context, "melt ponds", at: CGPoint(x: shelf.minX + width * 0.11, y: shelf.minY + height * 0.10), color: .cyan) }
        if crackOpacity > 0.01 { aaDrawTag(&context, "hydrofracture", at: CGPoint(x: shelf.minX + width * 0.50, y: shelf.maxY + height * 0.10), color: .red) }
        aaDrawTag(&context, "risk \(Int(collapseRisk.rounded())) / 100", at: CGPoint(x: width * 0.79, y: height * 0.91), color: .orange)
        aaDrawTag(&context, "support \(Int(buttressingRemaining.rounded())) / 100", at: CGPoint(x: width * 0.21, y: height * 0.91), color: .cyan)
    }

    private func stageCaption(_ stage: Int) -> String {
        switch stage {
        case 0: "INTACT SHELF"
        case 1: "MELT PONDS FORM"
        case 2: "CRACKS DEEPEN"
        case 3: "SHELF FRAGMENTS"
        default: "BREAKUP & ACCELERATION"
        }
    }
}

private enum AALabScenario: String, CaseIterable, Identifiable {
    case glacierFlow
    case buttressing
    case hydrofracture

    var id: String { rawValue }
    var title: String {
        switch self {
        case .glacierFlow: "Glacier Flow"
        case .buttressing: "Shelf Buttressing"
        case .hydrofracture: "Hydrofracture"
        }
    }
    var chineseTitle: String {
        switch self {
        case .glacierFlow: "冰川流动"
        case .buttressing: "冰架支撑"
        case .hydrofracture: "水力压裂"
        }
    }
    var labTitle: String {
        switch self {
        case .glacierFlow: "Interactive Antarctic Ice Sheet Simulator"
        case .buttressing: "Ice Shelf Buttressing Lab"
        case .hydrofracture: "Hydrofracture & Ice Shelf Collapse Lab"
        }
    }
    var chineseLabTitle: String {
        switch self {
        case .glacierFlow: "交互式南极冰盖模拟器"
        case .buttressing: "冰架支撑实验室"
        case .hydrofracture: "水力压裂与冰架崩塌实验室"
        }
    }
    var description: String {
        switch self {
        case .glacierFlow: "Adjust climate forcing, bed resistance, and feedback pathways to see a conceptual flow response."
        case .buttressing: "See how a floating shelf, pinning points, and embayment walls transmit back stress to grounded ice."
        case .hydrofracture: "Move through the collapse sequence as surface ponds deepen crevasses and break up an ice shelf."
        }
    }
    var chineseDescription: String {
        switch self {
        case .glacierFlow: "调整气候强迫、基底阻力与反馈路径，观察概念性的冰流响应。"
        case .buttressing: "观察浮冰架、固定点与海湾侧壁如何向接地冰传递背应力。"
        case .hydrofracture: "按崩塌序列查看表面积水如何加深裂隙并令冰架破碎。"
        }
    }
    var canvasTitle: String {
        switch self {
        case .glacierFlow: "Flow field"
        case .buttressing: "Back-stress bridge"
        case .hydrofracture: "Collapse sequence"
        }
    }
    var chineseCanvasTitle: String {
        switch self {
        case .glacierFlow: "冰流场"
        case .buttressing: "背应力桥梁"
        case .hydrofracture: "崩塌序列"
        }
    }
    var canvasGuide: String {
        switch self {
        case .glacierFlow: "Cyan parcels move with grounded ice; orange arrows show flow direction, red marks the grounding line, and warm shading marks ocean access."
        case .buttressing: "Blue arrows are shelf back stress acting against grounded-ice flow. Pinning points and lateral walls strengthen that connection; dashed gray marks lost shelf."
        case .hydrofracture: "Stage 0 is intact. Stages 1–2 add ponds and water-filled cracks; stages 3–4 fragment the shelf and reveal post-collapse acceleration."
        }
    }
    var chineseCanvasGuide: String {
        switch self {
        case .glacierFlow: "青色颗粒随接地冰移动；橙色箭头表示流向，红色表示接地线，暖色阴影表示海洋暖水进入。"
        case .buttressing: "蓝色箭头是抵抗接地冰流动的冰架背应力。固定点与侧壁会增强这条通路；灰色虚线表示损失的冰架。"
        case .hydrofracture: "阶段 0 为完整冰架；阶段 1–2 增加积水与充水裂缝；阶段 3–4 表示冰架碎裂及崩塌后的加速。"
        }
    }
    var searchTerms: String {
        switch self {
        case .glacierFlow: "flow velocity basal resistance glacier 冰流 速度 基底 阻力"
        case .buttressing: "shelf buttressing ocean melt support pinning 冰架 支撑 海洋 融化 固定点"
        case .hydrofracture: "surface melt firn crack collapse 水力压裂 表面融化 粒雪 裂隙 崩解"
        }
    }
    var symbol: String {
        switch self {
        case .glacierFlow: "arrow.right"
        case .buttressing: "rectangle.compress.vertical"
        case .hydrofracture: "bolt.horizontal"
        }
    }
    var tint: Color {
        switch self {
        case .glacierFlow: .cyan
        case .buttressing: .blue
        case .hydrofracture: .orange
        }
    }
}

private enum AALabPreset: String, CaseIterable, Identifiable {
    case thwaites
    case pineIsland
    case totten
    case coldReference

    var id: String { rawValue }
    var title: String {
        switch self {
        case .thwaites: "Thwaites-like"
        case .pineIsland: "Pine Island-like"
        case .totten: "Totten-like"
        case .coldReference: "Cold stable reference"
        }
    }
    var chineseTitle: String {
        switch self {
        case .thwaites: "类思韦茨"
        case .pineIsland: "类松岛"
        case .totten: "类托滕"
        case .coldReference: "寒冷稳定参考"
        }
    }
    var flowValues: (year: Double, air: Double, ocean: Double, snowfall: Double, shelf: Double, basal: Double, bed: Double, misi: Bool, collapse: Bool, warmWater: Bool) {
        switch self {
        case .thwaites: (2050, 1.2, 1.8, 0.6, 185, 42, 3.1, true, false, true)
        case .pineIsland: (2050, 0.9, 2.1, 0.7, 175, 48, 2.8, true, false, true)
        case .totten: (2045, 0.6, 1.5, 0.9, 240, 56, 2.0, true, false, true)
        case .coldReference: (2035, -1.5, 0.4, 1.5, 330, 78, 0.8, false, false, false)
        }
    }
}

private struct AALabMetrics {
    let lossIndex: Double
    let retreatSignal: Double
    let flowSignal: Double
    let seaLevelSignal: Double
    let buttressing: Double
    let ponding: Double
    let fracture: Double
    let collapseRisk: Double
    let stage: Int
    let autoStage: Int
}

private func aaClamp(_ value: Double, to range: ClosedRange<Double> = 0...1) -> Double {
    min(range.upperBound, max(range.lowerBound, value))
}

private func aaDrawArrow(_ context: inout GraphicsContext, from start: CGPoint, to end: CGPoint, color: Color, width: CGFloat) {
    let dx = end.x - start.x
    let dy = end.y - start.y
    let length = hypot(dx, dy)
    guard length > 0.1 else { return }
    let ux = dx / length
    let uy = dy / length
    let head = min(10, max(5, width * 2.4))
    let perpendicular = CGPoint(x: -uy, y: ux)
    var shaft = Path()
    shaft.move(to: start)
    shaft.addLine(to: end)
    context.stroke(shaft, with: .color(color), style: StrokeStyle(lineWidth: width, lineCap: .round))
    var arrow = Path()
    arrow.move(to: end)
    arrow.addLine(to: CGPoint(x: end.x - ux * head + perpendicular.x * head * 0.50, y: end.y - uy * head + perpendicular.y * head * 0.50))
    arrow.addLine(to: CGPoint(x: end.x - ux * head - perpendicular.x * head * 0.50, y: end.y - uy * head - perpendicular.y * head * 0.50))
    arrow.closeSubpath()
    context.fill(arrow, with: .color(color))
}

private func aaDrawTag(_ context: inout GraphicsContext, _ label: String, at point: CGPoint, color: Color) {
    context.draw(
        Text(label)
            .font(.system(size: 9, weight: .semibold, design: .rounded))
            .foregroundStyle(color),
        at: point,
        anchor: .center
    )
}

#Preview {
    MiniLabView()
        .environment(AppModel())
        .frame(width: 1_180, height: 900)
}
