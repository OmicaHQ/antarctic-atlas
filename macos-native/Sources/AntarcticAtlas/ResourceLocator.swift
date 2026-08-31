import Foundation

enum ResourceLocatorError: LocalizedError {
    case missingResource(String, searched: [URL])
    case unreadableResource(URL, Error)
    case malformedResource(URL, Error)

    var errorDescription: String? {
        switch self {
        case .missingResource(let name, let searched):
            let locations = searched.map(\.path).joined(separator: "\n")
            return "Could not find \(name). Searched:\n\(locations)"
        case .unreadableResource(let url, let error):
            return "Could not read \(url.lastPathComponent): \(error.localizedDescription)"
        case .malformedResource(let url, let error):
            return "Could not decode \(url.lastPathComponent): \(error.localizedDescription)"
        }
    }
}

enum ResourceLocator {
    private struct AreaPayload: Decodable {
        let color: String
        let question: String
        let why: String
        let topics: [String: String]
    }

    private struct TopicPayload: Decodable {
        let keyQuestion: String
        let status: String
        let regions: String

        private enum CodingKeys: String, CodingKey {
            case keyQuestion = "key_question"
            case status
            case regions
        }
    }

    static func loadResearchUniverse() throws -> ResearchUniverse {
        let areaURL = try locateJSON(named: "research_areas")
        let topicURL = try locateJSON(named: "topics")
        let decoder = JSONDecoder()

        let areaPayloads: [String: AreaPayload]
        let topicPayloads: [String: TopicPayload]

        do {
            areaPayloads = try decoder.decode(
                [String: AreaPayload].self,
                from: try Data(contentsOf: areaURL)
            )
        } catch let error as CocoaError where error.code == .fileReadNoSuchFile {
            throw ResourceLocatorError.unreadableResource(areaURL, error)
        } catch {
            throw ResourceLocatorError.malformedResource(areaURL, error)
        }

        do {
            topicPayloads = try decoder.decode(
                [String: TopicPayload].self,
                from: try Data(contentsOf: topicURL)
            )
        } catch let error as CocoaError where error.code == .fileReadNoSuchFile {
            throw ResourceLocatorError.unreadableResource(topicURL, error)
        } catch {
            throw ResourceLocatorError.malformedResource(topicURL, error)
        }

        let preferredOrder = [
            "Ocean",
            "Ice Dynamics",
            "Solid Earth",
            "Observations",
            "Paleoclimate",
            "Future Projections",
        ]
        let preferredTopicOrder: [String: [String]] = [
            "Ocean": [
                "CDW Intrusion",
                "Cross-shelf Heat Transport",
                "Ice-shelf Basal Melt",
                "Freshwater Feedback",
            ],
            "Ice Dynamics": [
                "Buttressing",
                "Grounding Line Retreat",
                "MISI",
                "MICI",
                "Basal Sliding",
            ],
            "Solid Earth": [
                "GIA",
                "Bed Topography",
                "Geothermal Heat Flux",
                "Subglacial Hydrology",
            ],
            "Observations": [
                "Satellite Altimetry",
                "InSAR Velocity",
                "GRACE / GRACE-FO",
                "Radar & Field Data",
            ],
            "Paleoclimate": [
                "Pliocene",
                "Last Interglacial",
                "Ice Cores",
                "Marine Sediments",
            ],
            "Future Projections": [
                "Sea-level Contribution",
                "Coupled Models",
                "Uncertainty Quantification",
                "AI for Earth Observation",
            ],
        ]

        let orderedAreaNames = areaPayloads.keys.sorted { left, right in
            let leftIndex = preferredOrder.firstIndex(of: left) ?? .max
            let rightIndex = preferredOrder.firstIndex(of: right) ?? .max
            return leftIndex == rightIndex ? left.localizedStandardCompare(right) == .orderedAscending : leftIndex < rightIndex
        }

        let areas = orderedAreaNames.compactMap { areaName -> ResearchArea? in
            guard let payload = areaPayloads[areaName] else { return nil }
            let curatedOrder = preferredTopicOrder[areaName] ?? []
            let topics = payload.topics
                .map { topicName, summary -> ResearchTopic in
                    let detail = topicPayloads[topicName]
                    return ResearchTopic(
                        name: topicName,
                        areaName: areaName,
                        summary: summary,
                        keyQuestion: detail?.keyQuestion ?? summary,
                        status: detail?.status ?? "Research frontier",
                        regions: detail?.regions ?? areaName,
                        colorHex: payload.color
                    )
                }
                .sorted { left, right in
                    let leftIndex = curatedOrder.firstIndex(of: left.name) ?? .max
                    let rightIndex = curatedOrder.firstIndex(of: right.name) ?? .max
                    return leftIndex == rightIndex
                        ? left.name.localizedStandardCompare(right.name) == .orderedAscending
                        : leftIndex < rightIndex
                }

            return ResearchArea(
                name: areaName,
                colorHex: payload.color,
                question: payload.question,
                importance: payload.why,
                topics: topics
            )
        }

        return ResearchUniverse(areas: areas)
    }

    static func locateJSON(named name: String) throws -> URL {
        let filename = "\(name).json"
        let candidates = resourceCandidates(filename: filename)

        if let existing = candidates.first(where: { FileManager.default.fileExists(atPath: $0.path) }) {
            return existing.standardizedFileURL
        }

        throw ResourceLocatorError.missingResource(filename, searched: candidates)
    }

    static func locateUniverseBackground() -> URL? {
        let filename = "AntarcticUniverseBackground.png"

        if let bundled = Bundle.main.url(
            forResource: "AntarcticUniverseBackground",
            withExtension: "png"
        ) {
            return bundled
        }
        if let bundled = Bundle.main.url(
            forResource: "AntarcticUniverseBackground",
            withExtension: "png",
            subdirectory: "Resources"
        ) {
            return bundled
        }

        var candidates: [URL] = []
        if let resourceURL = Bundle.main.resourceURL {
            candidates.append(resourceURL.appendingPathComponent(filename))
            candidates.append(
                resourceURL
                    .appendingPathComponent("Resources", isDirectory: true)
                    .appendingPathComponent(filename)
            )
        }

        var workingURL = URL(
            fileURLWithPath: FileManager.default.currentDirectoryPath,
            isDirectory: true
        )
        for _ in 0..<6 {
            candidates.append(
                workingURL
                    .appendingPathComponent("macos-native", isDirectory: true)
                    .appendingPathComponent("Sources", isDirectory: true)
                    .appendingPathComponent("AntarcticAtlas", isDirectory: true)
                    .appendingPathComponent("Resources", isDirectory: true)
                    .appendingPathComponent(filename)
            )
            workingURL.deleteLastPathComponent()
        }

        let sourceDirectory = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        candidates.append(
            sourceDirectory
                .appendingPathComponent("Resources", isDirectory: true)
                .appendingPathComponent(filename)
        )

        return candidates.first {
            FileManager.default.fileExists(atPath: $0.path)
        }?.standardizedFileURL
    }

    private static func resourceCandidates(filename: String) -> [URL] {
        var candidates: [URL] = []

        if let bundled = Bundle.main.url(
            forResource: filename.replacingOccurrences(of: ".json", with: ""),
            withExtension: "json",
            subdirectory: "data"
        ) {
            candidates.append(bundled)
        }
        if let bundledAtRoot = Bundle.main.url(
            forResource: filename.replacingOccurrences(of: ".json", with: ""),
            withExtension: "json"
        ) {
            candidates.append(bundledAtRoot)
        }
        if let resourceURL = Bundle.main.resourceURL {
            candidates.append(resourceURL.appendingPathComponent("data", isDirectory: true).appendingPathComponent(filename))
            candidates.append(resourceURL.appendingPathComponent(filename))
        }

        var workingURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath, isDirectory: true)
        for _ in 0..<6 {
            candidates.append(workingURL.appendingPathComponent("data", isDirectory: true).appendingPathComponent(filename))
            workingURL.deleteLastPathComponent()
        }

        // #filePath remains useful for command-line development runs launched
        // from outside the repository. Installed builds should resolve from the
        // app bundle before reaching this fallback.
        let sourceFile = URL(fileURLWithPath: #filePath)
        let repositoryRoot = sourceFile
            .deletingLastPathComponent() // AntarcticAtlas
            .deletingLastPathComponent() // Sources
            .deletingLastPathComponent() // macos-native
            .deletingLastPathComponent() // repository
        candidates.append(repositoryRoot.appendingPathComponent("data", isDirectory: true).appendingPathComponent(filename))

        var seen = Set<String>()
        return candidates.filter { seen.insert($0.standardizedFileURL.path).inserted }
    }
}
