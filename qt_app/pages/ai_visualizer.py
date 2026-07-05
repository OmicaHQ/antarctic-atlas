from desktop_qt_app import *

def _ai_visualizer_page(self):
    page, layout = self._page_shell(
        "🎨 AI Visualizer",
        "",
    )
    control_row = QGridLayout()
    story_label = QLabel("Choose story")
    story_label.setObjectName("SmallLabel")
    control_row.addWidget(story_label, 0, 0)
    self.story_combo = QComboBox()
    self.story_combo.addItems(["Ice Sheet Stability", "Ocean Heat Pathways", "Hydrofracture & Ice Cliff Risk", "Solid Earth Feedbacks"])
    self.story_combo.currentTextChanged.connect(self._set_story_topic)
    control_row.addWidget(self.story_combo, 1, 0, 1, 2)
    lens_label = QLabel("Lens")
    lens_label.setObjectName("SmallLabel")
    control_row.addWidget(lens_label, 0, 2)
    lens_row = QHBoxLayout()
    self.story_lens_buttons = []
    for index, lens in enumerate(["Past", "Present", "Future"]):
        radio = QRadioButton(lens)
        radio.setChecked(index == 0)
        radio.toggled.connect(lambda checked, value=lens: checked and self._set_story_lens(value))
        self.story_lens_buttons.append(radio)
        lens_row.addWidget(radio)
    control_row.addLayout(lens_row, 1, 2)
    layout.addLayout(control_row)

    self.story_scene = StoryEngineWidget()
    self.story_scene.stateChanged.connect(self._update_story_details)
    layout.addWidget(self.story_scene, 1)

    caption = QLabel("This is a curated scientific-story visualization based on the review-paper mechanisms. It is designed for explanation and presentation, not as a raw-data simulation.")
    caption.setObjectName("Muted")
    caption.setWordWrap(True)
    layout.addWidget(caption)
    metrics = QHBoxLayout()
    self.story_metric_cards = {
        "Story": StatCard("Story", "Ice Sheet Stability", "Selected scientific storyline"),
        "Lens": StatCard("Lens", "Past", "Research-use framing"),
        "Story beats": StatCard("Story beats", "4", "Connected nodes"),
        "Output mode": StatCard("Output mode", "Interactive", "Slide-ready chain"),
    }
    for card in self.story_metric_cards.values():
        metrics.addWidget(card)
    layout.addLayout(metrics)
    self.story_export = QTextBrowser()
    self.story_export.setObjectName("KnowledgeCard")
    self.story_export.setMinimumHeight(190)
    layout.addWidget(self.story_export)
    self.storyboard_toggle = QPushButton("Storyboard table")
    self.storyboard_toggle.setObjectName("ExpanderButton")
    self.storyboard_toggle.setCheckable(True)
    self.storyboard_toggle.clicked.connect(self._toggle_storyboard_table)
    layout.addWidget(self.storyboard_toggle)
    self.storyboard_table = QTreeWidget()
    self.storyboard_table.setObjectName("KnowledgeCard")
    self.storyboard_table.setHeaderLabels(["Stage", "Node", "System / Type", "Meaning", "Evidence"])
    self.storyboard_table.setRootIsDecorated(False)
    self.storyboard_table.setAlternatingRowColors(True)
    self.storyboard_table.setMinimumHeight(210)
    self.storyboard_table.setVisible(False)
    layout.addWidget(self.storyboard_table)
    self._update_story_details()
    return page


def _set_story_topic(self, story):
    if hasattr(self, "story_scene"):
        self.story_scene.set_story(story)
    self._update_story_details()


def _set_story_lens(self, lens):
    if hasattr(self, "story_scene"):
        self.story_scene.set_lens(lens)
    self._update_story_details()


def _toggle_storyboard_table(self, checked=False):
    if hasattr(self, "storyboard_table"):
        self.storyboard_table.setVisible(bool(checked))
    if hasattr(self, "storyboard_toggle"):
        self.storyboard_toggle.setText(translate_text("Storyboard table (open)" if checked else "Storyboard table"))


def _update_story_details(self):
    story = combo_current_key(self.story_combo) if hasattr(self, "story_combo") else "Ice Sheet Stability"
    lens = self.story_scene.lens if hasattr(self, "story_scene") else "Past"
    opening, nodes = self.story_scene._story_nodes() if hasattr(self, "story_scene") else ("", [])
    chain_nodes = [node["name"] for node in nodes]
    chain = " -> ".join(translate_text(name) for name in chain_nodes)
    display_story = translate_text(story)
    display_lens = translate_text(lens)
    display_opening = translate_text(opening)
    if hasattr(self, "story_metric_cards"):
        self.story_metric_cards["Story"].set_value(story, "Selected scientific storyline")
        self.story_metric_cards["Lens"].set_value(lens, "Past / Present / Future framing")
        self.story_metric_cards["Story beats"].set_value(str(len(chain_nodes)), "Connected nodes")
        step = self.story_scene.step if hasattr(self, "story_scene") else -1
        mode_detail = "Ready: Begin Story" if step < 0 else f"Beat {step + 1} / {len(chain_nodes)}: {chain_nodes[step]}"
        self.story_metric_cards["Output mode"].set_value("Interactive", mode_detail)
    if hasattr(self, "story_export"):
        self.story_export.setHtml(
            f"<div class='ios-kicker'>{html.escape(translate_text('SLIDE-READY EXPORT TEXT'))}</div><h3>{html.escape(display_story)} - {html.escape(display_lens)}</h3>"
            f"<p><b>{html.escape(translate_text('Main message'))}:</b> {html.escape(display_opening)}</p>"
            f"<p><b>{html.escape(translate_text('Visual chain'))}:</b> {html.escape(chain)}</p>"
            f"<p><b>{html.escape(translate_text('Speaker note'))}:</b> "
            f"{html.escape(translate_text('Use the animation as a step-by-step explanation. Each node represents one scientific beat; the right card links the beat to evidence such as satellite observations, ocean data, paleo records, or coupled models.'))}</p>"
        )
    if hasattr(self, "storyboard_table"):
        self.storyboard_table.clear()
        for i, node in enumerate(nodes):
            item = QTreeWidgetItem([
                str(i + 1),
                translate_text(node["name"]),
                translate_text(node["kind"]),
                translate_text(node["note"]),
                translate_text(node["evidence"]),
            ])
            self.storyboard_table.addTopLevelItem(item)
        for column, width in enumerate([64, 190, 150, 520, 260]):
            self.storyboard_table.setColumnWidth(column, width)
