import SwiftUI

struct UniverseView: View {
    @State private var query = ""
    @State private var selectedArea = AtlasData.researchAreas[0]
    @State private var selectedTopic: ResearchTopic?

    private var matchedTopic: ResearchTopic? {
        let terms = query.lowercased().split(separator: " ").map(String.init)
        guard !terms.isEmpty else { return nil }
        return AtlasData.researchAreas
            .flatMap(\.topics)
            .max { lhs, rhs in score(lhs, terms: terms) < score(rhs, terms: terms) }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HeroHeader(title: "Antarctic Research Universe", subtitle: "Explore the review paper as a native iOS knowledge map.", symbol: "sparkles")

                TextField("Ask about grounding lines, CDW, GRACE, paleo records...", text: $query)
                    .textFieldStyle(.roundedBorder)
                    .autocorrectionDisabled()

                if let match = matchedTopic, !query.isEmpty {
                    Button {
                        selectedTopic = match
                    } label: {
                        Label("Best match: \(match.name)", systemImage: "scope")
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .buttonStyle(.borderedProminent)
                }

                LazyVGrid(columns: [GridItem(.adaptive(minimum: 150), spacing: 12)], spacing: 12) {
                    ForEach(AtlasData.researchAreas) { area in
                        Button {
                            selectedArea = area
                            selectedTopic = area.topics.first
                        } label: {
                            VStack(alignment: .leading, spacing: 8) {
                                Text(area.name)
                                    .font(.headline)
                                Text(area.question)
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.72))
                                    .lineLimit(3)
                            }
                            .frame(maxWidth: .infinity, minHeight: 104, alignment: .topLeading)
                            .padding(12)
                            .background(area.id == selectedArea.id ? .cyan.opacity(0.28) : .white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(.white.opacity(0.12)))
                        }
                        .buttonStyle(.plain)
                    }
                }

                VStack(alignment: .leading, spacing: 12) {
                    Text(selectedArea.importance)
                        .foregroundStyle(.white.opacity(0.78))
                    ForEach(selectedArea.topics) { topic in
                        Button {
                            selectedTopic = topic
                        } label: {
                            TopicRow(topic: topic, isSelected: selectedTopic?.id == topic.id)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            .padding()
        }
        .atlasBackground()
        .navigationTitle("Universe")
        .sheet(item: $selectedTopic) { topic in
            TopicDetailView(topic: topic)
        }
    }

    private func score(_ topic: ResearchTopic, terms: [String]) -> Int {
        let haystack = "\(topic.name) \(topic.question) \(topic.why) \(topic.status) \(topic.region)".lowercased()
        return terms.reduce(0) { $0 + (haystack.contains($1) ? 1 : 0) }
    }
}

struct TopicRow: View {
    let topic: ResearchTopic
    let isSelected: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(topic.name)
                    .font(.headline)
                    .foregroundStyle(.white)
                Spacer()
                Text(topic.status)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.cyan)
            }
            Text(topic.question)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.76))
            Text(topic.region)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.55))
        }
        .padding(12)
        .background(isSelected ? .cyan.opacity(0.24) : .white.opacity(0.07), in: RoundedRectangle(cornerRadius: 8))
    }
}

struct TopicDetailView: View {
    let topic: ResearchTopic
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section("Key question") { Text(topic.question) }
                Section("Why it matters") { Text(topic.why) }
                Section("Status") { Text(topic.status) }
                Section("Regions") { Text(topic.region) }
            }
            .navigationTitle(topic.name)
            .toolbar { Button("Done") { dismiss() } }
        }
    }
}

struct SystemExplorerView: View {
    @State private var selectedCase = AtlasData.cases[0]
    @State private var selectedTool = AtlasData.tools[0]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HeroHeader(title: "Antarctic System Explorer", subtitle: "Compare cases and observation layers.", symbol: "map")

                Picker("Case", selection: $selectedCase) {
                    ForEach(AtlasData.cases) { Text($0.name).tag($0) }
                }
                .pickerStyle(.menu)

                VStack(alignment: .leading, spacing: 8) {
                    Text(selectedCase.name)
                        .font(.title2.bold())
                    Text(selectedCase.theme)
                        .foregroundStyle(.cyan)
                    Text(selectedCase.note)
                        .foregroundStyle(.white.opacity(0.78))
                    HStack {
                        MetricPill(title: "Region", value: selectedCase.region)
                        MetricPill(title: "Coords", value: selectedCase.coordinates)
                    }
                }
                .padding(14)
                .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))

                Picker("Observation tool", selection: $selectedTool) {
                    ForEach(AtlasData.tools) { Text($0.name).tag($0) }
                }
                .pickerStyle(.segmented)

                VStack(alignment: .leading, spacing: 12) {
                    Label(selectedTool.name, systemImage: toolSymbol(selectedTool.name))
                        .font(.title3.bold())
                    MetricPill(title: "Measures", value: selectedTool.measures)
                    Text(selectedTool.observed)
                    Text(selectedTool.interpretation)
                        .foregroundStyle(.white.opacity(0.72))
                    Text(selectedTool.process)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.cyan)
                }
                .foregroundStyle(.white)
                .padding(14)
                .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
            }
            .padding()
        }
        .atlasBackground()
        .navigationTitle("System")
    }

    private func toolSymbol(_ name: String) -> String {
        if name.contains("Radar") { return "wave.3.right" }
        if name.contains("Velocity") { return "arrow.right.circle" }
        if name.contains("GRACE") { return "circle.hexagongrid" }
        if name.contains("GPS") { return "location" }
        if name.contains("Cores") { return "archivebox" }
        return "satellite"
    }
}

struct StoryVisualizerView: View {
    @State private var selectedStory = AtlasData.stories[0]
    @State private var visibleBeats = 1

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HeroHeader(title: "Scientific Story Engine", subtitle: "Reveal Antarctic mechanisms as slide-ready story beats.", symbol: "play.rectangle")

                Picker("Story", selection: $selectedStory) {
                    ForEach(AtlasData.stories) { Text($0.name).tag($0) }
                }
                .pickerStyle(.menu)
                .onChange(of: selectedStory) { _, _ in visibleBeats = 1 }

                VStack(alignment: .leading, spacing: 8) {
                    Text(selectedStory.name)
                        .font(.title2.bold())
                    Text(selectedStory.subtitle)
                        .foregroundStyle(.cyan)
                    Text(selectedStory.opening)
                        .foregroundStyle(.white.opacity(0.78))
                    Stepper("Visible beats: \(visibleBeats)", value: $visibleBeats, in: 1...selectedStory.beats.count)
                }
                .padding(14)
                .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))

                ForEach(Array(selectedStory.beats.prefix(visibleBeats).enumerated()), id: \.element.id) { index, beat in
                    HStack(alignment: .top, spacing: 12) {
                        Text("\(index + 1)")
                            .font(.headline.monospacedDigit())
                            .frame(width: 34, height: 34)
                            .background(.cyan.opacity(0.22), in: Circle())
                        VStack(alignment: .leading, spacing: 6) {
                            Text(beat.title)
                                .font(.headline)
                            Text(beat.type)
                                .font(.caption.weight(.bold))
                                .foregroundStyle(.cyan)
                            Text(beat.note)
                                .foregroundStyle(.white.opacity(0.78))
                            Text(beat.evidence)
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.56))
                        }
                    }
                    .padding(12)
                    .background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 8))
                }
            }
            .padding()
        }
        .atlasBackground()
        .navigationTitle("Stories")
    }
}

struct MiniLabView: View {
    @State private var year = 2050.0
    @State private var oceanTemp = 1.2
    @State private var shelfThickness = 260.0
    @State private var basalFriction = 0.48
    @State private var surfaceMelt = 45.0
    @State private var misi = true

    private var vulnerability: Double {
        let ocean = (oceanTemp + 2.0) / 7.0
        let shelf = 1.0 - min(max(shelfThickness / 700.0, 0), 1)
        let friction = 1.0 - basalFriction
        let melt = surfaceMelt / 100.0
        let time = (year - 2025.0) / 75.0
        let feedback = misi ? 0.14 : 0
        return min(max((ocean * 0.30 + shelf * 0.22 + friction * 0.18 + melt * 0.16 + time * 0.12 + feedback), 0), 1)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HeroHeader(title: "Mini Research Lab", subtitle: "A compact conceptual simulator for ice-sheet response.", symbol: "slider.horizontal.3")

                Gauge(value: vulnerability) {
                    Text("Conceptual vulnerability")
                } currentValueLabel: {
                    Text("\(Int(vulnerability * 100))")
                }
                .gaugeStyle(.accessoryCircularCapacity)
                .tint(Gradient(colors: [.mint, .cyan, .orange]))
                .frame(maxWidth: .infinity)
                .padding()
                .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))

                Group {
                    SliderRow(title: "Simulation year", value: $year, range: 2025...2100, format: "%.0f")
                    SliderRow(title: "Ocean forcing", value: $oceanTemp, range: -2...5, format: "%.1f C")
                    SliderRow(title: "Ice shelf thickness", value: $shelfThickness, range: 50...700, format: "%.0f m")
                    SliderRow(title: "Basal friction", value: $basalFriction, range: 0...1, format: "%.2f")
                    SliderRow(title: "Surface melt", value: $surfaceMelt, range: 0...100, format: "%.0f %%")
                    Toggle("Enable MISI feedback", isOn: $misi)
                        .tint(.cyan)
                }
                .padding(12)
                .background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 8))

                Text(labInterpretation)
                    .foregroundStyle(.white.opacity(0.78))
                    .padding(14)
                    .background(.cyan.opacity(0.12), in: RoundedRectangle(cornerRadius: 8))
            }
            .padding()
        }
        .atlasBackground()
        .navigationTitle("Lab")
    }

    private var labInterpretation: String {
        if vulnerability > 0.72 {
            return "High vulnerability: strong ocean forcing, weak shelf support, or low basal resistance could produce rapid dynamic response in a marine-based sector."
        }
        if vulnerability > 0.44 {
            return "Moderate vulnerability: several stressors are active, but shelf strength or friction still provide stabilizing resistance."
        }
        return "Lower vulnerability: current settings retain more buttressing and basal resistance, so simulated retreat pressure is muted."
    }
}

struct SliderRow: View {
    let title: String
    @Binding var value: Double
    let range: ClosedRange<Double>
    let format: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title)
                Spacer()
                Text(String(format: format, value))
                    .foregroundStyle(.cyan)
                    .monospacedDigit()
            }
            Slider(value: $value, in: range)
                .tint(.cyan)
        }
        .foregroundStyle(.white)
    }
}

struct CompassView: View {
    @State private var selected = AtlasData.directions[0]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HeroHeader(title: "Research Compass", subtitle: "Choose a frontier direction and turn it into a research seed.", symbol: "safari")

                Picker("Direction", selection: $selected) {
                    ForEach(AtlasData.directions) { Text($0.name).tag($0) }
                }
                .pickerStyle(.menu)

                HStack {
                    MetricPill(title: "Impact", value: "\(selected.impact)/100")
                    MetricPill(title: "Uncertainty", value: "\(selected.uncertainty)/100")
                    MetricPill(title: "Observability", value: "\(selected.observability)/100")
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text(selected.name)
                        .font(.title2.bold())
                    Text(selected.system)
                        .foregroundStyle(.cyan)
                    Text(selected.coreQuestion)
                        .font(.headline)
                    Text(selected.whyNow)
                        .foregroundStyle(.white.opacity(0.76))
                    Text("Gap: \(selected.gap)")
                        .foregroundStyle(.white.opacity(0.64))
                }
                .padding(14)
                .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))

                VStack(alignment: .leading, spacing: 10) {
                    Text("Methods")
                        .font(.headline)
                    ChipFlow(items: selected.methods)
                    Text("Regions")
                        .font(.headline)
                    ChipFlow(items: selected.regions)
                }
                .padding(14)
                .background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 8))
            }
            .padding()
        }
        .atlasBackground()
        .navigationTitle("Compass")
    }
}

struct ChipFlow: View {
    let items: [String]

    var body: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 120), spacing: 8)], spacing: 8) {
            ForEach(items, id: \.self) { item in
                Text(item)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .background(.cyan.opacity(0.16), in: RoundedRectangle(cornerRadius: 8))
            }
        }
    }
}
