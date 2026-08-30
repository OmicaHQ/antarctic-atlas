import Foundation

struct ResearchTopic: Identifiable, Hashable {
    var id: String { name }
    let name: String
    let question: String
    let why: String
    let status: String
    let region: String
}

struct ResearchArea: Identifiable, Hashable {
    var id: String { name }
    let name: String
    let question: String
    let importance: String
    let colorName: String
    let topics: [ResearchTopic]
}

struct ObservationCase: Identifiable, Hashable {
    var id: String { name }
    let name: String
    let region: String
    let type: String
    let theme: String
    let coordinates: String
    let note: String
}

struct ObservationTool: Identifiable, Hashable {
    var id: String { name }
    let name: String
    let measures: String
    let observed: String
    let interpretation: String
    let process: String
}

struct Story: Identifiable, Hashable {
    var id: String { name }
    let name: String
    let subtitle: String
    let opening: String
    let beats: [StoryBeat]
}

struct StoryBeat: Identifiable, Hashable {
    var id: String { title }
    let title: String
    let type: String
    let note: String
    let evidence: String
}

struct Direction: Identifiable, Hashable {
    var id: String { name }
    let name: String
    let system: String
    let uncertainty: Int
    let impact: Int
    let observability: Int
    let timeScale: String
    let regions: [String]
    let methods: [String]
    let coreQuestion: String
    let whyNow: String
    let gap: String
}

enum AtlasData {
    static let researchAreas: [ResearchArea] = [
        ResearchArea(name: "Ocean", question: "How does Southern Ocean heat reach the ice?", importance: "Ocean forcing controls basal melt and ice-shelf thinning.", colorName: "cyan", topics: [
            ResearchTopic(name: "CDW Intrusion", question: "Where does warm Circumpolar Deep Water reach ice-shelf cavities?", why: "It links ocean circulation to rapid thinning.", status: "Central process", region: "Amundsen, Bellingshausen, Totten"),
            ResearchTopic(name: "Cross-shelf Heat Transport", question: "What routes heat across the continental shelf?", why: "Winds, eddies, tides, and bathymetry decide access.", status: "Observation frontier", region: "Shelf breaks and troughs"),
            ResearchTopic(name: "Ice-shelf Basal Melt", question: "How quickly does ocean heat melt shelves from below?", why: "Shelf thinning weakens buttressing.", status: "High impact", region: "Floating ice shelves")
        ]),
        ResearchArea(name: "Ice Dynamics", question: "How does grounded ice respond when support is lost?", importance: "Dynamics connects shelf change to sea-level rise.", colorName: "blue", topics: [
            ResearchTopic(name: "Buttressing", question: "How much back stress do ice shelves provide?", why: "Loss of support can accelerate outlet glaciers.", status: "Observable", region: "Major ice shelves"),
            ResearchTopic(name: "Grounding Line Retreat", question: "When does retreat become self-sustaining?", why: "The grounding line gates discharge to the ocean.", status: "Projection-critical", region: "Marine-based basins"),
            ResearchTopic(name: "MISI", question: "Can retrograde beds amplify retreat?", why: "Marine ice sheet instability is a high-risk mechanism.", status: "Uncertain but crucial", region: "WAIS and parts of EAIS")
        ]),
        ResearchArea(name: "Solid Earth", question: "How does the bed beneath the ice shape change?", importance: "Bed topography, heat, hydrology, and uplift are boundary conditions.", colorName: "mint", topics: [
            ResearchTopic(name: "GIA", question: "Can bedrock uplift slow retreat?", why: "Solid-Earth response affects local sea level and mass estimates.", status: "Model frontier", region: "West Antarctica"),
            ResearchTopic(name: "Bed Topography", question: "Which basins are marine based and vulnerable?", why: "Hidden geometry controls retreat pathways.", status: "Foundational data", region: "Subglacial basins"),
            ResearchTopic(name: "Subglacial Hydrology", question: "How does water alter basal friction?", why: "Basal water can lubricate ice flow.", status: "Hard to observe", region: "Interior and outlet glaciers")
        ]),
        ResearchArea(name: "Observations", question: "Which tools reveal ice-sheet change?", importance: "Satellites and field records turn mechanisms into evidence.", colorName: "indigo", topics: [
            ResearchTopic(name: "Satellite Altimetry", question: "Where is the surface rising or lowering?", why: "Elevation change maps thinning and accumulation.", status: "Mature satellite record", region: "Continent scale"),
            ResearchTopic(name: "InSAR Velocity", question: "Where is ice accelerating?", why: "Velocity reveals discharge pathways.", status: "Powerful diagnostic", region: "Outlet glaciers"),
            ResearchTopic(name: "GRACE / GRACE-FO", question: "How much mass is changing?", why: "Gravity detects regional mass balance.", status: "Needs GIA correction", region: "Large basins")
        ]),
        ResearchArea(name: "Future Projections", question: "How much sea-level rise could Antarctica add?", importance: "Projection uncertainty connects science to coastal risk.", colorName: "teal", topics: [
            ResearchTopic(name: "Sea-level Contribution", question: "How large and how fast could the contribution be?", why: "This is the central societal impact.", status: "Uncertain but crucial", region: "Global coastlines"),
            ResearchTopic(name: "Coupled Models", question: "How do ice, ocean, atmosphere, and Earth interact?", why: "Feedbacks require coupled modeling.", status: "Major frontier", region: "Earth system"),
            ResearchTopic(name: "AI for Earth Observation", question: "Can AI organize observations and literature?", why: "Useful for knowledge maps and satellite reasoning.", status: "Emerging opportunity", region: "Remote sensing")
        ])
    ]

    static let cases: [ObservationCase] = [
        ObservationCase(name: "Thwaites Glacier", region: "West Antarctica / Amundsen Sea", type: "Fast outlet glacier", theme: "Ocean-driven thinning, grounding-line retreat, and MISI-like vulnerability", coordinates: "~75S, 106W", note: "Often discussed as one of the most vulnerable WAIS glaciers because warm ocean water can thin its shelf and reduce buttressing."),
        ObservationCase(name: "Pine Island Glacier", region: "West Antarctica / Amundsen Sea", type: "Fast outlet glacier", theme: "CDW intrusion, shelf thinning, and grounding-line retreat", coordinates: "~75S, 100W", note: "A classic example of rapid retreat linked to warm Circumpolar Deep Water reaching an ice-shelf cavity."),
        ObservationCase(name: "Totten Glacier", region: "East Antarctica / Sabrina Coast", type: "East Antarctic outlet glacier", theme: "Warm water access to a marine-based EAIS sector", coordinates: "~67S, 116E", note: "Shows that parts of East Antarctica can also be sensitive to ocean heat and marine-based bed geometry."),
        ObservationCase(name: "Larsen B Ice Shelf", region: "Antarctic Peninsula", type: "Collapsed ice shelf", theme: "Surface meltwater, hydrofracturing, and buttressing loss", coordinates: "~65S, 61W", note: "A famous shelf-collapse example followed by acceleration of tributary glaciers after buttressing was lost."),
        ObservationCase(name: "Wilkes Subglacial Basin", region: "East Antarctica", type: "Marine-based subglacial basin", theme: "Bed topography, marine-based ice, and long-term sensitivity", coordinates: "~70S, 140E", note: "Important because marine-based East Antarctic ice could be vulnerable if retreat propagates inland.")
    ]

    static let tools: [ObservationTool] = [
        ObservationTool(name: "Satellite Altimetry", measures: "Surface elevation change", observed: "Surface lowering and dynamic thinning near glacier trunks and grounding zones.", interpretation: "Lower elevation is consistent with shelf thinning and faster discharge.", process: "Repeated elevation profiles -> thinning map -> dynamic response"),
        ObservationTool(name: "InSAR Velocity", measures: "Ice velocity and deformation", observed: "Fast flow and acceleration toward floating ice shelves.", interpretation: "Faster flow suggests reduced resistance near the grounding line.", process: "SAR phase -> displacement -> velocity field -> ice discharge"),
        ObservationTool(name: "GRACE / GRACE-FO", measures: "Regional mass change from gravity", observed: "Large-scale negative mass balance in vulnerable sectors.", interpretation: "Mass loss contributes to global sea-level rise, but needs GIA correction.", process: "Gravity change -> mass balance -> sea-level contribution"),
        ObservationTool(name: "GPS / GNSS", measures: "Point motion and bedrock response", observed: "Sparse station-style points track crustal motion and uplift.", interpretation: "Helps separate ice-mass change from solid-Earth motion.", process: "Station position -> crustal motion -> GIA correction"),
        ObservationTool(name: "Ice-penetrating Radar", measures: "Ice thickness, bed topography, internal layers", observed: "Bed geometry and possible retrograde slopes beneath glacier systems.", interpretation: "Bed shape determines whether retreat can become self-sustaining.", process: "Radar echo -> bed map -> instability assessment"),
        ObservationTool(name: "Ice / Marine Sediment Cores", measures: "Past climate and retreat history", observed: "Records help reconstruct earlier grounding-line positions and ocean conditions.", interpretation: "Past retreat gives context for future forcing.", process: "Core record -> past retreat -> future sensitivity")
    ]

    static let stories: [Story] = [
        Story(name: "Ice Sheet Stability", subtitle: "From ocean heat to ice-sheet retreat", opening: "Antarctic stability emerges from ocean forcing, shelf buttressing, grounding-line geometry, and Earth-system feedbacks.", beats: [
            StoryBeat(title: "Warm Ocean Access", type: "Ocean", note: "Warm Circumpolar Deep Water can reach vulnerable ice-shelf cavities.", evidence: "Ocean observations and shelf-break bathymetry"),
            StoryBeat(title: "Basal Melting", type: "Ice shelf", note: "Ocean heat melts the underside of floating ice shelves.", evidence: "Altimetry, moorings, and melt-rate estimates"),
            StoryBeat(title: "Reduced Buttressing", type: "Ice dynamics", note: "Thinner or damaged shelves provide less back stress to grounded ice.", evidence: "Ice velocity and shelf-thickness change"),
            StoryBeat(title: "Grounding Line Retreat", type: "Ice dynamics", note: "The grounding line controls how much ice discharges into the ocean.", evidence: "InSAR, altimetry, and tidal flexure"),
            StoryBeat(title: "Sea-level Risk", type: "Impact", note: "Antarctica remains a major uncertainty in future sea-level projections.", evidence: "Projection ensembles")
        ]),
        Story(name: "Hydrofracture Risk", subtitle: "Atmospheric melt, shelf collapse, and high-end risk", opening: "Surface meltwater can pond on shelves, deepen crevasses, and reduce shelf integrity.", beats: [
            StoryBeat(title: "Surface Melt", type: "Atmosphere", note: "Surface melt is prominent around the Antarctic Peninsula and shelf margins.", evidence: "Satellite melt detection"),
            StoryBeat(title: "Melt Ponds", type: "Hydrology", note: "Ponded water adds weight and can fill crevasses.", evidence: "Optical imagery"),
            StoryBeat(title: "Hydrofracturing", type: "Fracture", note: "Water pressure can drive cracks deeper into the shelf.", evidence: "Larsen-style collapse interpretation"),
            StoryBeat(title: "Shelf Collapse", type: "Instability", note: "Shelf breakup reduces buttressing and can accelerate tributary glaciers.", evidence: "Larsen B observations")
        ])
    ]

    static let directions: [Direction] = [
        Direction(name: "Ocean heat pathways", system: "Ocean-ice shelf interaction", uncertainty: 92, impact: 94, observability: 58, timeScale: "days to decades", regions: ["Amundsen Sea", "Bellingshausen Sea", "Totten Glacier"], methods: ["Ocean moorings", "AUV", "CTD", "High-resolution models"], coreQuestion: "How does warm Circumpolar Deep Water cross the shelf and reach ice-shelf cavities?", whyNow: "Warm ocean access is a central control on basal melt, but the pathways depend on winds, eddies, tides, bathymetry, and freshwater feedbacks.", gap: "Cross-shelf heat transport is hard to observe directly and difficult to represent at the right spatial scale."),
        Direction(name: "Grounding-line instability", system: "Ice dynamics", uncertainty: 88, impact: 96, observability: 64, timeScale: "years to centuries", regions: ["Thwaites", "Pine Island", "Wilkes Basin"], methods: ["InSAR", "Satellite altimetry", "Radar sounding", "Ice-sheet models"], coreQuestion: "When does grounding-line retreat become self-sustaining on retrograde bed topography?", whyNow: "MISI links bed geometry, shelf buttressing, and ocean forcing.", gap: "Timing and reversibility depend on bed topography, friction, melt parameterization, and solid-Earth feedbacks."),
        Direction(name: "Ice-shelf fracture and calving", system: "Atmosphere-ice shelf coupling", uncertainty: 85, impact: 90, observability: 70, timeScale: "days to years", regions: ["Antarctic Peninsula", "Larsen B", "Wilkins"], methods: ["Optical imagery", "SAR", "Surface melt mapping", "Fracture models"], coreQuestion: "How do surface melt, hydrofracture, and calving change buttressing?", whyNow: "Surface hydrology and hydrofracture are crucial for rapid shelf collapse and high-end risk.", gap: "Models struggle to predict when fractures connect and how quickly inland glaciers respond."),
        Direction(name: "AI-assisted Antarctic research", system: "AI + Earth observation", uncertainty: 74, impact: 78, observability: 86, timeScale: "now to next decade", regions: ["Remote sensing", "Literature synthesis", "Education"], methods: ["Knowledge graphs", "RAG", "Computer vision", "Interactive visualization"], coreQuestion: "How can AI organize observations, literature, and model uncertainty without replacing scientific reasoning?", whyNow: "The Atlas turns a dense review paper into explorable knowledge maps and simulations.", gap: "AI tools must remain source-grounded, uncertainty-aware, and connected to real workflows.")
    ]
}
