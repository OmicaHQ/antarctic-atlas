import SwiftUI
import UniformTypeIdentifiers

struct PaperView: View {
    @Environment(AppModel.self) private var appModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var documentURL: URL?
    @State private var securityScopedURL: URL?
    @State private var currentPage = 1
    @State private var pageCount = 0
    @State private var matchCount = 0
    @State private var effectiveSearchQuery = ""
    @State private var command: PDFKitCommand?
    @State private var isChoosingDocument = false

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()

            if let documentURL {
                reader(for: documentURL)
            } else {
                missingDocument
            }
        }
        .background(Color(nsColor: .windowBackgroundColor).ignoresSafeArea())
        .navigationTitle("Read the Paper")
        .onAppear(perform: locateBundledPaper)
        .task(id: appModel.searchText) {
            let requestedQuery = appModel.searchText
            if !requestedQuery.isEmpty {
                try? await Task.sleep(for: .milliseconds(180))
            }
            guard !Task.isCancelled else { return }
            effectiveSearchQuery = requestedQuery
        }
        .onDisappear {
            securityScopedURL?.stopAccessingSecurityScopedResource()
        }
        .fileImporter(isPresented: $isChoosingDocument, allowedContentTypes: [.pdf]) { result in
            guard case .success(let url) = result else { return }
            securityScopedURL?.stopAccessingSecurityScopedResource()
            securityScopedURL = url.startAccessingSecurityScopedResource() ? url : nil
            open(url)
        }
    }

    private var header: some View {
        HStack(alignment: .center, spacing: 16) {
            Image(systemName: "doc.richtext")
                .font(.system(size: 23, weight: .semibold))
                .foregroundStyle(.tint)
                .frame(width: 44, height: 44)
                .background(.tint.opacity(0.12), in: RoundedRectangle(cornerRadius: 12))
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 3) {
                Text(appModel.text("Read the Paper", "阅读论文"))
                    .font(.title2.weight(.semibold))
                Text(documentURL?.deletingPathExtension().lastPathComponent ?? "The Sensitivity of the Antarctic Ice Sheet to a Changing Climate")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer(minLength: 16)

            Button {
                isChoosingDocument = true
            } label: {
                Label(appModel.text("Choose PDF", "选择 PDF"), systemImage: "folder")
            }
            .help(appModel.text("Open another research paper", "打开另一篇研究论文"))

            if let documentURL {
                ShareLink(item: documentURL) {
                    Label(appModel.text("Share", "分享"), systemImage: "square.and.arrow.up")
                }
                .help(appModel.text("Share the PDF", "分享 PDF"))

                Button {
                    send(.printDocument)
                } label: {
                    Label(appModel.text("Print", "打印"), systemImage: "printer")
                }
                .keyboardShortcut("p", modifiers: .command)
                .help(appModel.text("Print the PDF", "打印 PDF"))
            }
        }
        .padding(.horizontal, 22)
        .padding(.vertical, 14)
        .background(.bar)
    }

    private func reader(for url: URL) -> some View {
        VStack(spacing: 0) {
            readerToolbar
            Divider()

            HSplitView {
                pageRail
                    .frame(minWidth: 96, idealWidth: 112, maxWidth: 150)

                PDFKitView(
                    url: url,
                    searchQuery: effectiveSearchQuery,
                    currentPage: $currentPage,
                    pageCount: $pageCount,
                    matchCount: $matchCount,
                    command: command
                )
                .frame(minWidth: 520, minHeight: 520)
                .accessibilityLabel("PDF page view")
            }
        }
    }

    private var readerToolbar: some View {
        HStack(spacing: 12) {
            HStack(spacing: 7) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                TextField(appModel.text("Search this paper", "搜索论文"), text: sharedSearch)
                    .textFieldStyle(.plain)
                    .frame(minWidth: 180, idealWidth: 260, maxWidth: 360)
                    .accessibilityLabel(appModel.text("Search the paper", "搜索论文"))
                if !appModel.searchText.isEmpty {
                    Button {
                        appModel.searchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(appModel.text("Clear search", "清除搜索"))
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 8))

            if !appModel.searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                if isSearchPending {
                    ProgressView()
                        .controlSize(.small)
                        .accessibilityLabel(appModel.text("Searching the paper", "正在搜索论文"))
                    Text(appModel.text("Searching…", "正在搜索…"))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    Text(matchCount == 1
                         ? appModel.text("1 match", "1 处匹配")
                         : appModel.text("\(matchCount) matches", "\(matchCount) 处匹配"))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(matchCount == 0 ? Color.orange : Color.secondary)
                        .contentTransition(reduceMotion ? .identity : .numericText())
                        .accessibilityLabel(appModel.text(
                            "\(matchCount) search matches",
                            "找到 \(matchCount) 处搜索匹配"
                        ))
                }

                ControlGroup {
                    Button { send(.previousMatch) } label: {
                        Label(appModel.text("Previous match", "上一个匹配"), systemImage: "chevron.up")
                    }
                    Button { send(.nextMatch) } label: {
                        Label(appModel.text("Next match", "下一个匹配"), systemImage: "chevron.down")
                    }
                }
                .disabled(matchCount == 0 || isSearchPending)
            }

            Spacer()

            ControlGroup {
                Button {
                    currentPage = max(1, currentPage - 1)
                } label: {
                    Label(appModel.text("Previous page", "上一页"), systemImage: "chevron.left")
                }
                .disabled(currentPage <= 1)

                Button {
                    currentPage = min(max(1, pageCount), currentPage + 1)
                } label: {
                    Label(appModel.text("Next page", "下一页"), systemImage: "chevron.right")
                }
                .disabled(currentPage >= pageCount)
            }

            Text(appModel.text("Page \(currentPage) of \(pageCount)", "第 \(currentPage) 页，共 \(pageCount) 页"))
                .font(.callout.monospacedDigit())
                .frame(minWidth: 112)
                .accessibilityLabel(appModel.text("Page \(currentPage) of \(pageCount)", "第 \(currentPage) 页，共 \(pageCount) 页"))

            ControlGroup {
                Button { send(.zoomOut) } label: {
                    Label(appModel.text("Zoom out", "缩小"), systemImage: "minus.magnifyingglass")
                }
                Button { send(.fitPage) } label: {
                    Label(appModel.text("Fit", "适合页面"), systemImage: "arrow.up.left.and.arrow.down.right")
                }
                Button { send(.zoomIn) } label: {
                    Label(appModel.text("Zoom in", "放大"), systemImage: "plus.magnifyingglass")
                }
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 9)
        .background(.bar)
    }

    private var pageRail: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 7) {
                    ForEach(1...max(1, pageCount), id: \.self) { page in
                        Button {
                            currentPage = page
                        } label: {
                            VStack(spacing: 7) {
                                Image(systemName: "doc.text")
                                    .font(.title3)
                                    .foregroundStyle(page == currentPage ? Color.accentColor : Color.secondary)
                                Text(appModel.text("Page \(page)", "第 \(page) 页"))
                                    .font(.caption.monospacedDigit())
                                    .foregroundStyle(page == currentPage ? Color.primary : Color.secondary)
                            }
                            .frame(maxWidth: .infinity, minHeight: 62)
                            .background(
                                page == currentPage ? AnyShapeStyle(Color.accentColor.opacity(0.14)) : AnyShapeStyle(.clear),
                                in: RoundedRectangle(cornerRadius: 9)
                            )
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .id(page)
                        .accessibilityLabel(appModel.text("Page \(page)", "第 \(page) 页"))
                        .accessibilityAddTraits(page == currentPage ? .isSelected : [])
                    }
                }
                .padding(9)
            }
            .background(Color(nsColor: .underPageBackgroundColor).opacity(0.5))
            .onChange(of: currentPage) { _, page in
                withAnimation(reduceMotion ? nil : .easeInOut(duration: 0.18)) {
                    proxy.scrollTo(page, anchor: .center)
                }
            }
        }
        .accessibilityLabel(appModel.text("PDF page numbers", "PDF 页码"))
    }

    private var missingDocument: some View {
        ContentUnavailableView {
            Label(appModel.text("Paper not found", "未找到论文"), systemImage: "doc.questionmark")
        } description: {
            Text(appModel.text(
                "The included review paper was not found in the app bundle or next to the project.",
                "在应用资源或项目目录旁未找到内置综述论文。"
            ))
        } actions: {
            Button(appModel.text("Locate Again", "重新查找"), action: locateBundledPaper)
            Button(appModel.text("Choose PDF…", "选择 PDF…")) { isChoosingDocument = true }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func send(_ kind: PDFKitCommandKind) {
        command = PDFKitCommand(kind: kind)
    }

    private func open(_ url: URL) {
        documentURL = url
        currentPage = 1
        pageCount = 0
        matchCount = 0
        appModel.searchText = ""
        effectiveSearchQuery = ""
        command = nil
    }

    private func locateBundledPaper() {
        guard documentURL == nil else { return }
        if let located = AAPaperResourceLocator.locate() {
            open(located)
        }
    }

    private var sharedSearch: Binding<String> {
        Binding(
            get: { appModel.searchText },
            set: { appModel.searchText = $0 }
        )
    }

    private var isSearchPending: Bool {
        appModel.searchText != effectiveSearchQuery
    }
}

private enum AAPaperResourceLocator {
    static let preferredName = "Reviews of Geophysics - 2020 - Noble - The Sensitivity of the Antarctic Ice Sheet to a Changing Climate  Past  Present  and.pdf"

    static func locate() -> URL? {
        let fileManager = FileManager.default

        if let bundled = Bundle.main.url(forResource: preferredName.replacingOccurrences(of: ".pdf", with: ""), withExtension: "pdf") {
            return bundled
        }

        var directories: [URL] = []
        if let resourceURL = Bundle.main.resourceURL {
            directories.append(resourceURL)
        }
        directories.append(URL(fileURLWithPath: fileManager.currentDirectoryPath, isDirectory: true))

        if let executableURL = Bundle.main.executableURL {
            var cursor = executableURL.deletingLastPathComponent()
            for _ in 0..<6 {
                directories.append(cursor)
                cursor.deleteLastPathComponent()
            }
        }

        var visited = Set<String>()
        for directory in directories where visited.insert(directory.standardizedFileURL.path).inserted {
            let preferredURL = directory.appendingPathComponent(preferredName)
            if fileManager.fileExists(atPath: preferredURL.path) {
                return preferredURL
            }

            guard let entries = try? fileManager.contentsOfDirectory(
                at: directory,
                includingPropertiesForKeys: [.isRegularFileKey],
                options: [.skipsHiddenFiles]
            ) else { continue }

            if let firstPDF = entries.first(where: {
                $0.pathExtension.localizedCaseInsensitiveCompare("pdf") == .orderedSame
                    && $0.lastPathComponent.localizedCaseInsensitiveContains("Antarctic")
            }) {
                return firstPDF
            }
        }
        return nil
    }
}

#Preview {
    PaperView()
        .environment(AppModel())
        .frame(width: 1_180, height: 820)
}
