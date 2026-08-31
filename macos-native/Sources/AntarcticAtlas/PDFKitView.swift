import AppKit
import PDFKit
import SwiftUI

enum PDFKitCommandKind: Equatable {
    case zoomIn
    case zoomOut
    case fitPage
    case nextMatch
    case previousMatch
    case printDocument
}

struct PDFKitCommand: Equatable, Identifiable {
    let id = UUID()
    let kind: PDFKitCommandKind
}

struct PDFKitView: NSViewRepresentable {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let url: URL
    var searchQuery: String
    @Binding var currentPage: Int
    @Binding var pageCount: Int
    @Binding var matchCount: Int
    var command: PDFKitCommand?

    init(
        url: URL,
        searchQuery: String = "",
        currentPage: Binding<Int>,
        pageCount: Binding<Int>,
        matchCount: Binding<Int>,
        command: PDFKitCommand? = nil
    ) {
        self.url = url
        self.searchQuery = searchQuery
        _currentPage = currentPage
        _pageCount = pageCount
        _matchCount = matchCount
        self.command = command
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(parent: self)
    }

    func makeNSView(context: Context) -> PDFView {
        let view = PDFView()
        view.displayMode = .singlePageContinuous
        view.displayDirection = .vertical
        view.displaysPageBreaks = true
        view.pageShadowsEnabled = true
        view.autoScales = true
        view.backgroundColor = NSColor.windowBackgroundColor
        view.setAccessibilityLabel("Research paper PDF")

        context.coordinator.pdfView = view
        NotificationCenter.default.addObserver(
            context.coordinator,
            selector: #selector(Coordinator.pageDidChange(_:)),
            name: .PDFViewPageChanged,
            object: view
        )
        loadDocument(into: view, coordinator: context.coordinator)
        return view
    }

    func updateNSView(_ view: PDFView, context: Context) {
        context.coordinator.parent = self

        if context.coordinator.loadedURL != url {
            loadDocument(into: view, coordinator: context.coordinator)
        }

        if context.coordinator.lastSearchQuery != searchQuery {
            updateSearch(in: view, coordinator: context.coordinator)
        }

        if let document = view.document,
           currentPage > 0,
           currentPage <= document.pageCount,
           let desiredPage = document.page(at: currentPage - 1),
           view.currentPage !== desiredPage {
            view.go(to: desiredPage)
        }

        if let command, context.coordinator.lastCommandID != command.id {
            context.coordinator.lastCommandID = command.id
            perform(command.kind, in: view, coordinator: context.coordinator)
        }
    }

    static func dismantleNSView(_ nsView: PDFView, coordinator: Coordinator) {
        NotificationCenter.default.removeObserver(
            coordinator,
            name: .PDFViewPageChanged,
            object: nsView
        )
    }

    private func loadDocument(into view: PDFView, coordinator: Coordinator) {
        coordinator.loadedURL = url
        coordinator.lastSearchQuery = nil
        coordinator.pageResults = []
        coordinator.highlightedSelections = []
        coordinator.currentMatchIndex = -1

        let document = PDFDocument(url: url)
        view.document = document
        view.autoScales = true

        let count = document?.pageCount ?? 0
        updateBindings(page: count > 0 ? 1 : 0, count: count, matches: 0)
        updateSearch(in: view, coordinator: coordinator)
    }

    private func updateSearch(in view: PDFView, coordinator: Coordinator) {
        let trimmed = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        coordinator.lastSearchQuery = searchQuery
        coordinator.currentMatchIndex = -1

        guard !trimmed.isEmpty, let document = view.document else {
            coordinator.pageResults = []
            coordinator.highlightedSelections = []
            view.highlightedSelections = []
            updateMatchCount(0)
            return
        }

        let search = makePageSearchResults(for: trimmed, in: document)
        for selection in search.highlightedSelections {
            selection.color = NSColor.systemYellow.withAlphaComponent(0.48)
        }
        coordinator.pageResults = search.pageResults
        coordinator.highlightedSelections = search.highlightedSelections
        view.highlightedSelections = search.highlightedSelections
        updateMatchCount(search.pageResults.count)

        if let first = search.pageResults.first?.primarySelection {
            coordinator.currentMatchIndex = 0
            view.setCurrentSelection(first, animate: !reduceMotion)
            view.go(to: first)
        }
    }

    private func perform(_ command: PDFKitCommandKind, in view: PDFView, coordinator: Coordinator) {
        switch command {
        case .zoomIn:
            view.autoScales = false
            view.scaleFactor = min(view.maxScaleFactor, max(view.minScaleFactor, view.scaleFactor * 1.16))
        case .zoomOut:
            view.autoScales = false
            view.scaleFactor = max(view.minScaleFactor, view.scaleFactor / 1.16)
        case .fitPage:
            view.autoScales = true
        case .nextMatch:
            showMatch(offset: 1, in: view, coordinator: coordinator)
        case .previousMatch:
            showMatch(offset: -1, in: view, coordinator: coordinator)
        case .printDocument:
            let operation = NSPrintOperation(view: view)
            operation.showsPrintPanel = true
            operation.showsProgressPanel = true
            operation.run()
        }
    }

    private func showMatch(offset: Int, in view: PDFView, coordinator: Coordinator) {
        guard !coordinator.pageResults.isEmpty else { return }
        let count = coordinator.pageResults.count
        coordinator.currentMatchIndex = (coordinator.currentMatchIndex + offset + count) % count
        let selection = coordinator.pageResults[coordinator.currentMatchIndex].primarySelection
        view.setCurrentSelection(selection, animate: !reduceMotion)
        view.go(to: selection)
    }

    /// Mirrors the Windows reader's paper search model: resolve recognized
    /// Chinese science terms to the English terminology used in the paper,
    /// search every resolved keyword, then navigate one ranked PDF page at a
    /// time instead of treating every occurrence as an unrelated result.
    private func makePageSearchResults(
        for query: String,
        in document: PDFDocument
    ) -> PDFPageSearch {
        let keywords = PDFPaperSearchResolver.keywords(for: query)
        guard !keywords.isEmpty else { return .empty }

        var scores: [Int: Int] = [:]
        var selectionsByPage: [Int: [PDFSelection]] = [:]
        var seenSelectionKeys: [Int: Set<String>] = [:]
        var highlightedSelections: [PDFSelection] = []
        var highlightedKeys = Set<String>()

        for keyword in keywords {
            let selections = document.findString(
                keyword,
                withOptions: [.caseInsensitive, .diacriticInsensitive]
            )

            for selection in selections {
                let pages = selection.pages
                for page in pages {
                    let pageIndex = document.index(for: page)
                    guard pageIndex >= 0 else { continue }

                    let key = selectionIdentity(selection, on: page, pageIndex: pageIndex)
                    if seenSelectionKeys[pageIndex, default: []].insert(key).inserted {
                        selectionsByPage[pageIndex, default: []].append(selection)
                        scores[pageIndex, default: 0] += 1
                    }
                }

                let overallKey = selectionIdentity(selection, in: document)
                if highlightedKeys.insert(overallKey).inserted {
                    highlightedSelections.append(selection)
                }
            }
        }

        let pageResults = scores.keys.compactMap { pageIndex -> PDFPageSearchResult? in
            guard let selections = selectionsByPage[pageIndex],
                  let primarySelection = selections.first else { return nil }
            return PDFPageSearchResult(
                pageIndex: pageIndex,
                score: scores[pageIndex, default: 0],
                primarySelection: primarySelection
            )
        }
        .sorted {
            $0.score == $1.score
                ? $0.pageIndex < $1.pageIndex
                : $0.score > $1.score
        }

        return PDFPageSearch(
            pageResults: pageResults,
            highlightedSelections: highlightedSelections
        )
    }

    private func selectionIdentity(
        _ selection: PDFSelection,
        on page: PDFPage,
        pageIndex: Int
    ) -> String {
        let bounds = selection.bounds(for: page)
        return [
            String(pageIndex),
            String(Int((bounds.origin.x * 100).rounded())),
            String(Int((bounds.origin.y * 100).rounded())),
            String(Int((bounds.width * 100).rounded())),
            String(Int((bounds.height * 100).rounded())),
            selection.string ?? ""
        ].joined(separator: ":")
    }

    private func selectionIdentity(_ selection: PDFSelection, in document: PDFDocument) -> String {
        selection.pages.compactMap { page -> String? in
            let pageIndex = document.index(for: page)
            guard pageIndex >= 0 else { return nil }
            return selectionIdentity(selection, on: page, pageIndex: pageIndex)
        }
        .joined(separator: "|")
    }

    private func updateBindings(page: Int, count: Int, matches: Int) {
        DispatchQueue.main.async {
            currentPage = page
            pageCount = count
            matchCount = matches
        }
    }

    private func updateMatchCount(_ count: Int) {
        DispatchQueue.main.async {
            matchCount = count
        }
    }

    final class Coordinator: NSObject {
        var parent: PDFKitView
        weak var pdfView: PDFView?
        var loadedURL: URL?
        var lastSearchQuery: String?
        var lastCommandID: UUID?
        fileprivate var pageResults: [PDFPageSearchResult] = []
        var highlightedSelections: [PDFSelection] = []
        var currentMatchIndex = -1

        init(parent: PDFKitView) {
            self.parent = parent
        }

        @objc func pageDidChange(_ notification: Notification) {
            guard let view = notification.object as? PDFView,
                  let document = view.document,
                  let page = view.currentPage else { return }
            let number = document.index(for: page) + 1
            if number != parent.currentPage {
                parent.currentPage = number
            }
        }
    }
}

fileprivate struct PDFPageSearchResult {
    let pageIndex: Int
    let score: Int
    let primarySelection: PDFSelection
}

private struct PDFPageSearch {
    let pageResults: [PDFPageSearchResult]
    let highlightedSelections: [PDFSelection]

    static let empty = PDFPageSearch(pageResults: [], highlightedSelections: [])
}

private enum PDFPaperSearchResolver {
    /// These are intentionally the same science-term expansions used by the
    /// prior Windows reader. The bundled paper is English, so a Chinese query
    /// must resolve to its English scientific vocabulary before PDFKit searches.
    private static let chineseTermExpansions: [(term: String, expansions: [String])] = [
        ("接地线", ["grounding line", "grounding zone"]),
        ("后退", ["retreat", "migration"]),
        ("冰架", ["ice shelf", "buttressing"]),
        ("基底", ["basal", "bed"]),
        ("融化", ["melt", "melting", "basal melt"]),
        ("海平面", ["sea level", "sea-level rise"]),
        ("温水", ["warm water", "circumpolar deep water", "cdw"]),
        ("环南极深层水", ["circumpolar deep water", "cdw"]),
        ("不稳定", ["instability", "misi", "mici"]),
        ("雷达", ["radar", "ice penetrating radar"]),
        ("卫星", ["satellite", "remote sensing"]),
        ("重力", ["grace", "gravity"]),
        ("古气候", ["paleoclimate", "pliocene", "last interglacial"])
    ]

    private static let tokenExpression = try! NSRegularExpression(
        pattern: "[\\p{L}\\p{N}-]+",
        options: []
    )

    static func keywords(for query: String) -> [String] {
        let sourceRange = NSRange(query.startIndex..., in: query)
        var candidates = tokenExpression.matches(in: query, options: [], range: sourceRange)
            .compactMap { match -> String? in
                guard let range = Range(match.range, in: query) else { return nil }
                return String(query[range])
            }

        for mapping in chineseTermExpansions where query.contains(mapping.term) {
            candidates.append(contentsOf: mapping.expansions)
        }

        var seen = Set<String>()
        return candidates.compactMap { candidate in
            let normalized = candidate
                .trimmingCharacters(in: .whitespacesAndNewlines)
                .lowercased()
            guard normalized.count > 1, seen.insert(normalized).inserted else { return nil }
            return normalized
        }
    }
}
