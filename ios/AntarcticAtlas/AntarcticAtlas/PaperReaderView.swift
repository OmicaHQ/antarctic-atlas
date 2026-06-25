import PDFKit
import SwiftUI

struct PaperReaderView: View {
    @State private var document = PDFDocument(resourceName: "Noble2020")
    @State private var query = ""
    @State private var selectedPageIndex = 0
    @State private var searchResults: [PaperSearchResult] = []
    @State private var selectedResult: PaperSearchResult?

    var body: some View {
        VStack(spacing: 0) {
            PaperSearchBar(
                query: $query,
                pageText: pageText,
                canGoBack: selectedPageIndex > 0,
                canGoForward: selectedPageIndex < max(document.pageCount - 1, 0),
                previousPage: { selectedPageIndex = max(selectedPageIndex - 1, 0) },
                nextPage: { selectedPageIndex = min(selectedPageIndex + 1, max(document.pageCount - 1, 0)) },
                runSearch: runSearch
            )

            if !searchResults.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(searchResults) { result in
                            Button {
                                selectedPageIndex = result.pageIndex
                                selectedResult = result
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("Page \(result.pageIndex + 1)")
                                        .font(.caption.weight(.bold))
                                    Text(result.excerpt)
                                        .font(.caption2)
                                        .lineLimit(2)
                                        .multilineTextAlignment(.leading)
                                }
                                .frame(width: 190, alignment: .leading)
                            }
                            .buttonStyle(.bordered)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                }
                .background(.thinMaterial)
            }

            PDFKitView(document: document, selectedPageIndex: $selectedPageIndex)
                .ignoresSafeArea(.container, edges: .bottom)
        }
        .navigationTitle("Raw Paper")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Search match", item: $selectedResult) { _ in
            Button("OK", role: .cancel) {}
        } message: { result in
            Text("Page \(result.pageIndex + 1)\n\n\(result.excerpt)")
        }
    }

    private var pageText: String {
        guard document.pageCount > 0 else { return "No PDF" }
        return "Page \(selectedPageIndex + 1) / \(document.pageCount)"
    }

    private func runSearch() {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            searchResults = []
            return
        }

        searchResults = document.search(trimmed, maxResults: 20)
        if let first = searchResults.first {
            selectedPageIndex = first.pageIndex
            selectedResult = first
        }
    }
}

struct PaperSearchBar: View {
    @Binding var query: String
    let pageText: String
    let canGoBack: Bool
    let canGoForward: Bool
    let previousPage: () -> Void
    let nextPage: () -> Void
    let runSearch: () -> Void

    var body: some View {
        VStack(spacing: 10) {
            HStack(spacing: 8) {
                TextField("Search paper", text: $query)
                    .textFieldStyle(.roundedBorder)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .onSubmit(runSearch)

                Button(action: runSearch) {
                    Image(systemName: "magnifyingglass")
                }
                .buttonStyle(.borderedProminent)
            }

            HStack {
                Button(action: previousPage) {
                    Image(systemName: "chevron.left")
                }
                .disabled(!canGoBack)

                Text(pageText)
                    .font(.subheadline.monospacedDigit())
                    .frame(maxWidth: .infinity)

                Button(action: nextPage) {
                    Image(systemName: "chevron.right")
                }
                .disabled(!canGoForward)
            }
        }
        .padding(12)
        .background(.regularMaterial)
    }
}

struct PDFKitView: UIViewRepresentable {
    let document: PDFDocument
    @Binding var selectedPageIndex: Int

    func makeUIView(context: Context) -> PDFView {
        let pdfView = PDFView()
        pdfView.autoScales = true
        pdfView.displayMode = .singlePageContinuous
        pdfView.displayDirection = .vertical
        pdfView.usePageViewController(false)
        pdfView.backgroundColor = .systemBackground
        pdfView.document = document
        return pdfView
    }

    func updateUIView(_ pdfView: PDFView, context: Context) {
        if pdfView.document !== document {
            pdfView.document = document
        }

        guard selectedPageIndex >= 0, selectedPageIndex < document.pageCount, let page = document.page(at: selectedPageIndex) else {
            return
        }

        if pdfView.currentPage !== page {
            pdfView.go(to: page)
        }
    }
}

struct PaperSearchResult: Identifiable {
    let id = UUID()
    let pageIndex: Int
    let excerpt: String
}

extension PDFDocument {
    convenience init(resourceName: String) {
        if let url = Bundle.main.url(forResource: resourceName, withExtension: "pdf"), let document = PDFDocument(url: url) {
            self.init()
            for index in 0..<document.pageCount {
                if let page = document.page(at: index) {
                    insert(page, at: index)
                }
            }
        } else {
            self.init()
        }
    }

    func search(_ query: String, maxResults: Int) -> [PaperSearchResult] {
        let needle = query.lowercased()
        var results: [PaperSearchResult] = []

        for pageIndex in 0..<pageCount {
            guard let text = page(at: pageIndex)?.string else { continue }
            let lower = text.lowercased()
            guard let range = lower.range(of: needle) else { continue }

            let start = lower.distance(from: lower.startIndex, to: range.lowerBound)
            let excerpt = text.paperExcerpt(around: start, radius: 140)
            results.append(PaperSearchResult(pageIndex: pageIndex, excerpt: excerpt))

            if results.count >= maxResults {
                return results
            }
        }

        return results
    }
}

extension String {
    func paperExcerpt(around index: Int, radius: Int) -> String {
        let safeIndex = max(0, min(index, count))
        let startOffset = max(0, safeIndex - radius)
        let endOffset = min(count, safeIndex + radius)
        let start = self.index(self.startIndex, offsetBy: startOffset)
        let end = self.index(self.startIndex, offsetBy: endOffset)
        return String(self[start..<end])
            .replacingOccurrences(of: "\n", with: " ")
            .replacingOccurrences(of: "  ", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
