from desktop_qt_app import *

def _raw_paper_page(self):
    page, layout = self._page_shell(
        "📄 Read Raw Paper",
        f"Loaded {len(self.pages)} readable pages from the review paper.",
    )
    search_row = QHBoxLayout()
    self.paper_query = QLineEdit()
    self.paper_query.setPlaceholderText("Example: grounding line, basal melt, Thwaites")
    search_button = QPushButton("Search")
    search_button.clicked.connect(self._search_paper)
    search_row.addWidget(self.paper_query, 1)
    search_row.addWidget(search_button)
    layout.addLayout(search_row)

    slider_card = Card()
    slider_layout = QVBoxLayout(slider_card)
    slider_layout.setContentsMargins(16, 12, 16, 12)
    slider_layout.setSpacing(6)
    self.paper_page_label = QLabel("Select page: Page 1")
    self.paper_page_label.setObjectName("SmallLabel")
    self.paper_page_slider = QSlider(Qt.Horizontal)
    self.paper_page_slider.setRange(1, max(1, len(self.pages)))
    self.paper_page_slider.setValue(1)
    self.paper_page_slider.valueChanged.connect(self._show_paper_page_number)
    slider_layout.addWidget(self.paper_page_label)
    slider_layout.addWidget(self.paper_page_slider)
    layout.addWidget(slider_card)
    self.paper_slider_card = slider_card

    match_card = Card()
    match_layout = QVBoxLayout(match_card)
    match_layout.setContentsMargins(16, 12, 16, 12)
    match_layout.setSpacing(6)
    match_label = QLabel("Matching pages")
    match_label.setObjectName("SmallLabel")
    self.paper_match_combo = QComboBox()
    self.paper_match_combo.currentIndexChanged.connect(self._show_selected_paper_match)
    match_layout.addWidget(match_label)
    match_layout.addWidget(self.paper_match_combo)
    match_card.setVisible(False)
    self.paper_match_card = match_card
    layout.addWidget(match_card)

    self.paper_matches = QTextBrowser()
    self.paper_matches.setObjectName("KnowledgeCard")
    self.paper_matches.setMinimumHeight(210)
    self.paper_matches.setMaximumHeight(260)
    self.paper_matches.setVisible(False)
    layout.addWidget(self.paper_matches)

    self.paper_results = QListWidget()
    self.paper_results.setObjectName("ResultsList")
    self.paper_results.setVisible(False)
    self.paper_text_label = QLabel("Page 1")
    self.paper_text_label.setObjectName("SmallLabel")
    layout.addWidget(self.paper_text_label)
    self.paper_text = QTextBrowser()
    self.paper_text.setObjectName("KnowledgeCard")
    self.paper_text.setFontFamily("Consolas")
    self.paper_text.setFontPointSize(10)
    self.paper_text.setMinimumHeight(600)
    self.paper_results.currentRowChanged.connect(self._show_selected_paper_page)
    layout.addWidget(self.paper_text, 1)
    self.current_paper_pages = [self.pages[0]] if self.pages else []
    self._show_paper_page_number(1)
    return page


def _search_paper(self):
    query = self.paper_query.text().strip()
    if not query:
        self.paper_matches.setVisible(False)
        if hasattr(self, "paper_match_card"):
            self.paper_match_card.setVisible(False)
        if hasattr(self, "paper_slider_card"):
            self.paper_slider_card.setVisible(True)
        self._show_paper_page_number(self.paper_page_slider.value())
        return
    raw_results = search_pages(self.pages, query, max_results=8)
    no_matches = not raw_results
    results = raw_results or self.pages[:1]
    if hasattr(self, "paper_slider_card"):
        self.paper_slider_card.setVisible(False)
    self.current_paper_pages = results
    self._populate_paper_match_combo(results)
    self._populate_paper_results(self.current_paper_pages)
    self._render_paper_matches(query, results, no_matches=no_matches)


def _show_paper_page_number(self, page_number):
    if not self.pages:
        return
    index = max(0, min(len(self.pages) - 1, page_number - 1))
    page = self.pages[index]
    self.paper_page_label.setText(f"Select page: Page {page.page}")
    if hasattr(self, "paper_text_label"):
        self.paper_text_label.setText(f"Page {page.page}")
    self.current_paper_pages = [page]
    self._populate_paper_results(self.current_paper_pages)
    self._render_paper_text(page)


def _render_paper_matches(self, query, pages, no_matches=False):
    keywords = extract_search_keywords(query)
    if no_matches:
        self.paper_matches.setHtml("<h3>No matching pages found. Showing page 1.</h3>")
        self.paper_matches.setVisible(True)
        return
    cards = ["<h3>Search matches</h3>"]
    for page in pages[:4]:
        cleaned = clean_text(page.text)
        lowered = cleaned.lower()
        score = sum(lowered.count(keyword.lower()) for keyword in keywords)
        excerpt = build_search_excerpt(page.text, keywords)
        cards.append(
            "<div class='ios-result-card'>"
            f"<div class='ios-kicker'>Page {page.page} - score {score}</div>"
            f"<div class='ios-muted'>{excerpt}</div>"
            "</div>"
        )
    self.paper_matches.setHtml("".join(cards))
    self.paper_matches.setVisible(True)


def _populate_paper_match_combo(self, pages):
    if not hasattr(self, "paper_match_combo"):
        return
    self.paper_match_combo.blockSignals(True)
    self.paper_match_combo.clear()
    for page in pages:
        self.paper_match_combo.addItem(f"Page {page.page}", page.page)
    self.paper_match_combo.blockSignals(False)
    if hasattr(self, "paper_match_card"):
        self.paper_match_card.setVisible(True)
    if pages:
        self.paper_match_combo.setCurrentIndex(0)


def _show_selected_paper_match(self, index):
    if index < 0 or index >= len(getattr(self, "current_paper_pages", [])):
        return
    page = self.current_paper_pages[index]
    if hasattr(self, "paper_page_label"):
        self.paper_page_label.setText(f"Matching pages: Page {page.page}")
    if hasattr(self, "paper_text_label"):
        self.paper_text_label.setText(f"Page {page.page}")
    if hasattr(self, "paper_results") and self.paper_results.currentRow() != index:
        self.paper_results.blockSignals(True)
        self.paper_results.setCurrentRow(index)
        self.paper_results.blockSignals(False)
    if hasattr(self, "paper_text"):
        self._render_paper_text(page)


def _populate_paper_results(self, pages):
    self.paper_results.clear()
    for page in pages:
        excerpt = clean_text(page.text)[:90]
        self.paper_results.addItem(f"Page {page.page}: {excerpt}...")
    self.paper_results.setCurrentRow(0)


def _show_selected_paper_page(self, row):
    if row < 0 or row >= len(self.current_paper_pages):
        return
    page = self.current_paper_pages[row]
    if hasattr(self, "paper_page_label"):
        prefix = "Matching pages" if hasattr(self, "paper_match_card") and not self.paper_match_card.isHidden() else "Select page"
        self.paper_page_label.setText(f"{prefix}: Page {page.page}")
    if hasattr(self, "paper_text_label"):
        self.paper_text_label.setText(f"Page {page.page}")
    if hasattr(self, "paper_match_combo") and self.paper_match_combo.isVisible() and self.paper_match_combo.currentIndex() != row:
        self.paper_match_combo.blockSignals(True)
        self.paper_match_combo.setCurrentIndex(row)
        self.paper_match_combo.blockSignals(False)
    self._render_paper_text(page)


def _render_paper_text(self, page):
    if not hasattr(self, "paper_text"):
        return
    lines = [re.sub(r"[ \t]+", " ", line).rstrip() for line in page.text.strip().splitlines()]
    self.paper_text.setPlainText("\n".join(lines))
