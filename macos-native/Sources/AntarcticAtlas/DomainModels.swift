import Foundation
import SwiftUI

// MARK: - Research universe

struct ResearchTopic: Identifiable, Hashable, Sendable {
    let name: String
    let areaName: String
    let summary: String
    let keyQuestion: String
    let status: String
    let regions: String
    let colorHex: String

    var id: String { "topic:\(areaName):\(name)" }
}

struct ResearchArea: Identifiable, Hashable, Sendable {
    let name: String
    let colorHex: String
    let question: String
    let importance: String
    let topics: [ResearchTopic]

    var id: String { "area:\(name)" }
}

struct ResearchUniverse: Hashable, Sendable {
    let areas: [ResearchArea]

    var topics: [ResearchTopic] {
        areas.flatMap(\.topics)
    }

    var nodes: [UniverseNode] {
        [.core] + areas.flatMap { area in
            [.area(area)] + area.topics.map(UniverseNode.topic)
        }
    }

    func area(named name: String) -> ResearchArea? {
        areas.first { $0.name == name }
    }
}

enum UniverseNode: Identifiable, Hashable, Sendable {
    case core
    case area(ResearchArea)
    case topic(ResearchTopic)

    var id: String {
        switch self {
        case .core:
            "core:antarctic-ice-sheet"
        case .area(let area):
            area.id
        case .topic(let topic):
            topic.id
        }
    }

    var title: String {
        switch self {
        case .core: "Antarctic Ice Sheet"
        case .area(let area): area.name
        case .topic(let topic): topic.name
        }
    }

    var eyebrow: String {
        switch self {
        case .core: "CORE SYSTEM"
        case .area: "RESEARCH AREA"
        case .topic(let topic): topic.areaName.uppercased()
        }
    }

    var keyQuestion: String {
        switch self {
        case .core:
            "How does the Antarctic Ice Sheet respond to climate forcing?"
        case .area(let area):
            area.question
        case .topic(let topic):
            topic.keyQuestion
        }
    }

    var evidenceSummary: String {
        switch self {
        case .core:
            "A coupled system linking atmosphere, ocean, ice dynamics, solid Earth, observations, paleoclimate evidence, and future sea-level risk."
        case .area(let area):
            area.importance
        case .topic(let topic):
            topic.summary
        }
    }

    var status: String {
        switch self {
        case .core: "Research hub"
        case .area: "Research area"
        case .topic(let topic): topic.status
        }
    }

    var regions: String {
        switch self {
        case .core:
            "Antarctica and global coastlines"
        case .area(let area):
            area.topics.map(\.name).joined(separator: " · ")
        case .topic(let topic):
            topic.regions
        }
    }

    var areaName: String? {
        switch self {
        case .core: nil
        case .area(let area): area.name
        case .topic(let topic): topic.areaName
        }
    }

    var colorHex: String {
        switch self {
        case .core: "#DDEEFF"
        case .area(let area): area.colorHex
        case .topic(let topic): topic.colorHex
        }
    }

    var graphLevel: Int {
        switch self {
        case .core: 0
        case .area: 1
        case .topic: 2
        }
    }

    var symbolName: String {
        switch self {
        case .core:
            "snowflake"
        case .topic:
            "circle.fill"
        case .area(let area):
            switch area.name {
            case "Ocean": "water.waves"
            case "Ice Dynamics": "arrow.triangle.branch"
            case "Solid Earth": "mountain.2"
            case "Observations": "sensor"
            case "Paleoclimate": "clock.arrow.circlepath"
            case "Future Projections": "chart.line.uptrend.xyaxis"
            default: "hexagon"
            }
        }
    }

    var topic: ResearchTopic? {
        guard case .topic(let topic) = self else { return nil }
        return topic
    }
}

// MARK: - Antarctic system explorer

enum ObservationLayer: String, CaseIterable, Identifiable, Hashable, Sendable {
    case altimetry = "Satellite Altimetry"
    case velocity = "InSAR Velocity"
    case gravity = "GRACE / GRACE-FO"
    case geodesy = "GPS / GNSS"
    case radar = "Ice-penetrating Radar"
    case cores = "Ice / Marine Sediment Cores"

    var id: String { rawValue }

    var shortName: String {
        switch self {
        case .altimetry: "Altimetry"
        case .velocity: "InSAR"
        case .gravity: "GRACE"
        case .geodesy: "GNSS"
        case .radar: "Radar"
        case .cores: "Cores"
        }
    }

    var symbolName: String {
        switch self {
        case .altimetry: "waveform.path.ecg"
        case .velocity: "arrow.up.right"
        case .gravity: "circle.grid.cross"
        case .geodesy: "antenna.radiowaves.left.and.right"
        case .radar: "water.waves.and.arrow.trianglehead.up"
        case .cores: "cylinder.split.1x2"
        }
    }

    var measure: String {
        switch self {
        case .altimetry: "Surface elevation change"
        case .velocity: "Ice velocity and deformation"
        case .gravity: "Regional mass change from gravity"
        case .geodesy: "Point motion and bedrock response"
        case .radar: "Ice thickness, bed topography, internal layers"
        case .cores: "Past climate and retreat history"
        }
    }

    var interpretation: String {
        switch self {
        case .altimetry: "Repeated elevation measurements locate thinning, but firn and snowfall effects must be separated from dynamic ice loss."
        case .velocity: "Velocity fields reveal discharge pathways and acceleration associated with changing buttressing."
        case .gravity: "Broad gravity changes constrain total mass balance after corrections for glacial isostatic adjustment."
        case .geodesy: "Precise but sparse station motion constrains solid-Earth response and improves gravity corrections."
        case .radar: "Subsurface echoes expose the bed geometry and internal structure that govern retreat sensitivity."
        case .cores: "Layered archives extend the evidence record beyond the short satellite era."
        }
    }

    var tint: Color {
        switch self {
        case .altimetry: Color(red: 0.37, green: 0.84, blue: 1.00)
        case .velocity: Color(red: 1.00, green: 0.58, blue: 0.22)
        case .gravity: Color(red: 1.00, green: 0.34, blue: 0.35)
        case .geodesy: Color(red: 0.38, green: 0.93, blue: 0.61)
        case .radar: Color(red: 0.98, green: 0.82, blue: 0.30)
        case .cores: Color(red: 0.73, green: 0.58, blue: 0.94)
        }
    }
}

enum AntarcticCaseStudy: String, CaseIterable, Identifiable, Hashable, Sendable {
    case thwaites = "Thwaites Glacier"
    case pineIsland = "Pine Island Glacier"
    case totten = "Totten Glacier"
    case larsenB = "Larsen B Ice Shelf"
    case wilkes = "Wilkes Subglacial Basin"

    var id: String { rawValue }

    var region: String {
        switch self {
        case .thwaites: "West Antarctica · Amundsen Sea"
        case .pineIsland: "West Antarctica · Pine Island Bay"
        case .totten: "East Antarctica · Sabrina Coast"
        case .larsenB: "Antarctic Peninsula"
        case .wilkes: "East Antarctica · Wilkes Land"
        }
    }

    var coordinates: String {
        switch self {
        case .thwaites: "75°S · 106°W"
        case .pineIsland: "75°S · 100°W"
        case .totten: "67°S · 116°E"
        case .larsenB: "65°S · 61°W"
        case .wilkes: "70°S · 140°E"
        }
    }

    var systemType: String {
        switch self {
        case .thwaites, .pineIsland: "Fast outlet glacier"
        case .totten: "East Antarctic outlet glacier"
        case .larsenB: "Collapsed ice shelf"
        case .wilkes: "Marine-based subglacial basin"
        }
    }

    var theme: String {
        switch self {
        case .thwaites: "Ocean-driven thinning, grounding-line retreat, and marine ice-sheet vulnerability"
        case .pineIsland: "Warm-water intrusion, ice-shelf thinning, and grounding-line retreat"
        case .totten: "Warm-water access to a marine-based East Antarctic sector"
        case .larsenB: "Surface meltwater, hydrofracturing, and buttressing loss"
        case .wilkes: "Bed topography, marine-based ice, and long-term sensitivity"
        }
    }

    var context: String {
        switch self {
        case .thwaites:
            "Warm ocean water can thin the floating shelf, reduce buttressing, and alter the discharge of grounded ice."
        case .pineIsland:
            "A well-observed outlet where ocean access and rapid dynamic change can be compared across sensors."
        case .totten:
            "A reminder that marine-based sectors of East Antarctica can also be sensitive to ocean heat and bed geometry."
        case .larsenB:
            "Shelf collapse was followed by acceleration of tributary glaciers, revealing the mechanical role of buttressing."
        case .wilkes:
            "Its deep marine basin makes hidden bed geometry central to long-term stability assessments."
        }
    }

    var caveat: String {
        switch self {
        case .thwaites:
            "Rapid change does not determine a single collapse timeline; ocean forcing, bed geometry, and model assumptions remain major uncertainties."
        case .pineIsland:
            "Local glacier behavior varies through time, and individual sensors do not independently establish the cause of change."
        case .totten:
            "Observations are spatially sparse and the strength and persistence of warm-water access remain uncertain."
        case .larsenB:
            "The Peninsula event is a strong process example, not a direct template for every Antarctic ice shelf."
        case .wilkes:
            "Present-day surface signals are subtle; long-term vulnerability is inferred from multiple data types and models."
        }
    }

    var spatialScale: String {
        switch self {
        case .larsenB: "Shelf + tributaries"
        case .wilkes: "Continental basin"
        default: "Glacier catchment"
        }
    }

    func observation(for layer: ObservationLayer) -> String {
        switch (self, layer) {
        case (.thwaites, .altimetry): "Surface lowering is concentrated near the trunk and grounding zone."
        case (.thwaites, .velocity): "Fast flow converges toward the floating shelf and main discharge corridor."
        case (.pineIsland, .altimetry): "Repeated tracks reveal a pronounced thinning corridor near the grounding zone."
        case (.pineIsland, .radar): "Bed and bathymetric troughs indicate possible pathways for ocean heat."
        case (.totten, .radar): "Profiles reveal marine-based geometry beneath a large East Antarctic catchment."
        case (.larsenB, .velocity): "Tributary glaciers accelerated after the floating shelf collapsed."
        case (.larsenB, .cores): "Archives help test how unusual the modern breakup is over longer timescales."
        case (.wilkes, .radar): "A deep subglacial basin is the defining hidden boundary condition."
        case (.wilkes, .gravity): "A broad, GIA-sensitive signal provides basin-scale mass context."
        case (_, .altimetry): "Elevation trends show where the surface is thinning or thickening."
        case (_, .velocity): "Flow fields trace the pathways that connect inland ice to the coast."
        case (_, .gravity): "Regional gravity change provides integrated mass-balance context."
        case (_, .geodesy): "Sparse stations constrain crustal motion and uplift corrections."
        case (_, .radar): "Subsurface echoes reveal bed geometry and ice structure."
        case (_, .cores): "Layered archives reconstruct past climate and retreat behavior."
        }
    }
}

struct ScienceMetric: Identifiable, Hashable, Sendable {
    let title: String
    let value: String
    let detail: String
    let symbolName: String

    var id: String { title }
}

// MARK: - Shared visual tokens

enum AtlasHexColor {
    static func color(_ hex: String) -> Color {
        var value = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        value.removeAll(where: { $0 == "#" })
        guard value.count == 6, let integer = UInt64(value, radix: 16) else {
            return .cyan
        }

        return Color(
            red: Double((integer >> 16) & 0xFF) / 255,
            green: Double((integer >> 8) & 0xFF) / 255,
            blue: Double(integer & 0xFF) / 255
        )
    }
}
