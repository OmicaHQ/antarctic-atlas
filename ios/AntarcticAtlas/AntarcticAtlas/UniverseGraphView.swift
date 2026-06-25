import SwiftUI

struct UniverseNode: Identifiable, Hashable {
    enum Kind: Hashable {
        case center
        case area(ResearchArea)
        case topic(ResearchArea, ResearchTopic)
    }

    let id: String
    let title: String
    let subtitle: String
    let detail: String
    let status: String
    let region: String
    let kind: Kind
    let color: Color
    let radius: CGFloat
}

struct UniverseGraphView: View {
    let areas: [ResearchArea]
    let query: String
    @Binding var selectedNode: UniverseNode

    private var nodes: [UniverseNode] {
        UniverseGraphLayout.nodes(for: areas)
    }

    private var matchedNode: UniverseNode? {
        UniverseGraphLayout.match(query: query, nodes: nodes)
    }

    var body: some View {
        GeometryReader { proxy in
            let layout = UniverseGraphLayout.positions(for: areas, in: proxy.size)
            ZStack {
                Canvas { context, size in
                    drawBackground(in: &context, size: size)
                    drawEdges(in: &context, layout: layout)
                }

                ForEach(nodes) { node in
                    if let point = layout[node.id] {
                        UniverseNodeButton(
                            node: node,
                            isSelected: selectedNode.id == node.id,
                            isMatched: matchedNode?.id == node.id
                        ) {
                            selectedNode = node
                        }
                        .position(point)
                    }
                }
            }
            .contentShape(Rectangle())
            .onChange(of: matchedNode) { _, newValue in
                if let newValue {
                    selectedNode = newValue
                }
            }
        }
        .frame(height: 430)
        .background(
            LinearGradient(
                colors: [
                    Color(red: 0.01, green: 0.04, blue: 0.09),
                    Color(red: 0.02, green: 0.10, blue: 0.16)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 8)
        )
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(.white.opacity(0.12)))
    }

    private func drawBackground(in context: inout GraphicsContext, size: CGSize) {
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        let glowRect = CGRect(x: center.x - 155, y: center.y - 155, width: 310, height: 310)
        context.fill(
            Path(ellipseIn: glowRect),
            with: .radialGradient(
                Gradient(colors: [.cyan.opacity(0.24), .clear]),
                center: center,
                startRadius: 20,
                endRadius: 170
            )
        )

        for scale in [0.46, 0.70, 0.92] {
            let width = min(size.width, size.height) * scale
            let rect = CGRect(x: center.x - width / 2, y: center.y - width / 2, width: width, height: width)
            var path = Path(ellipseIn: rect)
            context.stroke(path, with: .color(.white.opacity(0.07)), lineWidth: 1)
            path = Path()
        }
    }

    private func drawEdges(in context: inout GraphicsContext, layout: [String: CGPoint]) {
        guard let center = layout[UniverseGraphLayout.centerID] else { return }
        for area in areas {
            let areaID = UniverseGraphLayout.areaID(area)
            guard let areaPoint = layout[areaID] else { continue }
            strokeLine(from: center, to: areaPoint, in: &context, opacity: 0.24, width: 1.5)

            for topic in area.topics {
                let topicID = UniverseGraphLayout.topicID(area, topic)
                guard let topicPoint = layout[topicID] else { continue }
                strokeLine(from: areaPoint, to: topicPoint, in: &context, opacity: 0.16, width: 1)
            }
        }
    }

    private func strokeLine(from start: CGPoint, to end: CGPoint, in context: inout GraphicsContext, opacity: Double, width: CGFloat) {
        var path = Path()
        path.move(to: start)
        path.addLine(to: end)
        context.stroke(path, with: .color(.cyan.opacity(opacity)), lineWidth: width)
    }
}

struct UniverseNodeButton: View {
    let node: UniverseNode
    let isSelected: Bool
    let isMatched: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                ZStack {
                    Circle()
                        .fill(node.color.opacity(isSelected ? 0.95 : 0.72))
                    Circle()
                        .stroke(.white.opacity(isSelected || isMatched ? 0.95 : 0.28), lineWidth: isMatched ? 4 : 2)
                    Circle()
                        .stroke(node.color.opacity(0.24), lineWidth: isSelected ? 10 : 4)
                        .scaleEffect(isMatched ? 1.12 : 1.0)
                }
                .frame(width: node.radius * 2, height: node.radius * 2)
                .shadow(color: node.color.opacity(isSelected ? 0.58 : 0.25), radius: isSelected ? 18 : 8)

                Text(node.title)
                    .font(node.kind == .center ? .caption.weight(.bold) : .caption2.weight(.semibold))
                    .foregroundStyle(.white)
                    .lineLimit(2)
                    .multilineTextAlignment(.center)
                    .frame(width: max(72, node.radius * 3.2))
            }
            .scaleEffect(isSelected ? 1.08 : 1.0)
            .animation(.spring(response: 0.32, dampingFraction: 0.78), value: isSelected)
            .animation(.easeInOut(duration: 0.25), value: isMatched)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(node.title)
    }
}

struct UniverseNodeDetailPanel: View {
    let node: UniverseNode

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 5) {
                    Text(node.title)
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                    Text(node.subtitle)
                        .font(.subheadline)
                        .foregroundStyle(.cyan)
                }
                Spacer()
                Text(node.status)
                    .font(.caption.weight(.bold))
                    .padding(.horizontal, 9)
                    .padding(.vertical, 6)
                    .background(node.color.opacity(0.18), in: RoundedRectangle(cornerRadius: 8))
                    .foregroundStyle(.white)
            }

            Text(node.detail)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.78))

            if !node.region.isEmpty {
                Label(node.region, systemImage: "mappin.and.ellipse")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.62))
            }
        }
        .padding(14)
        .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(.white.opacity(0.10)))
    }
}

enum UniverseGraphLayout {
    static let centerID = "center"

    static func areaID(_ area: ResearchArea) -> String {
        "area-\(area.id)"
    }

    static func topicID(_ area: ResearchArea, _ topic: ResearchTopic) -> String {
        "topic-\(area.id)-\(topic.id)"
    }

    static func nodes(for areas: [ResearchArea]) -> [UniverseNode] {
        var all: [UniverseNode] = [
            UniverseNode(
                id: centerID,
                title: "Antarctic Ice Sheet",
                subtitle: "Core system",
                detail: "The central system linking atmosphere, ocean, ice dynamics, solid Earth, observations, paleoclimate evidence, and future sea-level risk.",
                status: "Research hub",
                region: "Antarctica and global coastlines",
                kind: .center,
                color: .white,
                radius: 28
            )
        ]

        for area in areas {
            let color = color(for: area)
            all.append(
                UniverseNode(
                    id: areaID(area),
                    title: area.name,
                    subtitle: "Research area",
                    detail: area.importance,
                    status: "Area",
                    region: "",
                    kind: .area(area),
                    color: color,
                    radius: 23
                )
            )

            for topic in area.topics {
                all.append(
                    UniverseNode(
                        id: topicID(area, topic),
                        title: topic.name,
                        subtitle: area.name,
                        detail: topic.question + " " + topic.why,
                        status: topic.status,
                        region: topic.region,
                        kind: .topic(area, topic),
                        color: color,
                        radius: 14
                    )
                )
            }
        }
        return all
    }

    static func positions(for areas: [ResearchArea], in size: CGSize) -> [String: CGPoint] {
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        let shortSide = min(size.width, size.height)
        let areaRadius = max(112, shortSide * 0.31)
        let topicRadius = max(168, shortSide * 0.43)

        var result: [String: CGPoint] = [centerID: center]
        for (areaIndex, area) in areas.enumerated() {
            let baseAngle = angle(index: areaIndex, count: areas.count) - .pi / 2
            let areaPoint = point(center: center, radius: areaRadius, angle: baseAngle)
            result[areaID(area)] = clamped(areaPoint, in: size, inset: 42)

            let spread = CGFloat.pi / 5
            let topicCount = max(area.topics.count, 1)
            for (topicIndex, topic) in area.topics.enumerated() {
                let offset = topicCount == 1 ? 0 : (CGFloat(topicIndex) / CGFloat(topicCount - 1) - 0.5) * spread
                let topicPoint = point(center: center, radius: topicRadius, angle: baseAngle + offset)
                result[topicID(area, topic)] = clamped(topicPoint, in: size, inset: 34)
            }
        }
        return result
    }

    static func match(query: String, nodes: [UniverseNode]) -> UniverseNode? {
        let terms = query.lowercased().split(separator: " ").map(String.init)
        guard !terms.isEmpty else { return nil }
        return nodes
            .filter { $0.id != centerID }
            .max { score($0, terms: terms) < score($1, terms: terms) }
    }

    private static func score(_ node: UniverseNode, terms: [String]) -> Int {
        let haystack = "\(node.title) \(node.subtitle) \(node.detail) \(node.status) \(node.region)".lowercased()
        return terms.reduce(0) { partial, term in
            partial + (haystack.contains(term) ? max(1, term.count / 2) : 0)
        }
    }

    private static func color(for area: ResearchArea) -> Color {
        switch area.colorName {
        case "blue": return .blue
        case "mint": return .mint
        case "indigo": return .indigo
        case "teal": return .teal
        default: return .cyan
        }
    }

    private static func angle(index: Int, count: Int) -> CGFloat {
        CGFloat(index) / CGFloat(max(count, 1)) * CGFloat.pi * 2
    }

    private static func point(center: CGPoint, radius: CGFloat, angle: CGFloat) -> CGPoint {
        CGPoint(x: center.x + cos(angle) * radius, y: center.y + sin(angle) * radius)
    }

    private static func clamped(_ point: CGPoint, in size: CGSize, inset: CGFloat) -> CGPoint {
        CGPoint(
            x: min(max(point.x, inset), max(inset, size.width - inset)),
            y: min(max(point.y, inset), max(inset, size.height - inset))
        )
    }
}
