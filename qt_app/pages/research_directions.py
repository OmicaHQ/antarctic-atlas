from desktop_qt_app import *

def _research_directions_page(self):
    page, layout = self._page_shell(
        "🧭 Research Compass",
        "Explore frontier questions from the review paper: choose a theme, inspect uncertainty, connect regions and methods, then generate a starter research idea.",
    )
    top = QHBoxLayout()
    top.setSpacing(18)
    left_column = QVBoxLayout()
    left_column.setSpacing(16)
    metric_row = QHBoxLayout()
    metric_row.setSpacing(16)
    self.direction_metric_cards = {
        "Impact": StatCard("Impact", "94", "/ 100"),
        "Uncertainty": StatCard("Uncertainty", "92", "/ 100"),
        "Observability": StatCard("Observability", "58", "/ 100"),
        "Time scale": StatCard("Time scale", "days → decades", ""),
    }
    self.direction_metric_cards["Time scale"].value_widget.setStyleSheet("font-size: 16px;")
    for card in self.direction_metric_cards.values():
        card.setMinimumHeight(150)
        card.setMaximumHeight(170)
        metric_row.addWidget(card)
    left_column.addLayout(metric_row)
    control = Card()
    control.setMinimumWidth(340)
    control.setMaximumWidth(390)
    control_layout = QVBoxLayout(control)
    control_layout.setContentsMargins(16, 14, 16, 14)
    control_layout.setSpacing(12)
    label = QLabel("Choose a frontier direction")
    label.setObjectName("SmallLabel")
    self.direction_combo = QComboBox()
    self.direction_combo.addItems(list(DIRECTION_DATA.keys()))
    self.direction_combo.currentTextChanged.connect(self._update_direction_details)
    self.direction_view_mode = "Compass"
    radio_caption = QLabel("View mode")
    radio_caption.setObjectName("SmallLabel")
    control_layout.addWidget(label)
    control_layout.addWidget(self.direction_combo)
    control_layout.addWidget(radio_caption)
    self.direction_mode_radios = {}
    for index, mode in enumerate(["Compass", "Timeline", "Region map", "Proposal builder"]):
        r = QRadioButton(mode)
        r.setChecked(index == 0)
        r.toggled.connect(lambda checked, value=mode: checked and self._set_direction_mode(value))
        self.direction_mode_radios[mode] = r
        control_layout.addWidget(r)
    ambition = QLabel("Ambition level")
    ambition.setObjectName("SmallLabel")
    self.direction_ambition_value = QLabel("3")
    self.direction_ambition_value.setObjectName("SliderValue")
    ambition_row = QHBoxLayout()
    ambition_row.setContentsMargins(0, 0, 0, 0)
    ambition_row.addWidget(ambition, 1)
    ambition_row.addWidget(self.direction_ambition_value)
    self.direction_ambition = QSlider(Qt.Horizontal)
    self.direction_ambition.setRange(1, 5)
    self.direction_ambition.setValue(3)
    self.direction_ambition.valueChanged.connect(self._update_direction_details)
    control_layout.addLayout(ambition_row)
    control_layout.addWidget(self.direction_ambition)

    self.direction_proposal_panel = QWidget()
    self.direction_proposal_panel.setObjectName("InlinePanel")
    proposal_layout = QVBoxLayout(self.direction_proposal_panel)
    proposal_layout.setContentsMargins(10, 10, 10, 10)
    proposal_layout.setSpacing(6)
    question_label = QLabel("Starter question")
    question_label.setObjectName("SmallLabel")
    self.direction_question_combo = QComboBox()
    self.direction_question_combo.currentTextChanged.connect(self._update_direction_details)
    methods_label = QLabel("Methods to include")
    methods_label.setObjectName("SmallLabel")
    regions_label = QLabel("Regions / evidence contexts")
    regions_label.setObjectName("SmallLabel")
    proposal_layout.addWidget(question_label)
    proposal_layout.addWidget(self.direction_question_combo)
    proposal_layout.addWidget(methods_label)
    self.direction_method_checks = []
    for _ in range(4):
        checkbox = QCheckBox()
        checkbox.toggled.connect(self._update_direction_details)
        self.direction_method_checks.append(checkbox)
        proposal_layout.addWidget(checkbox)
    proposal_layout.addWidget(regions_label)
    self.direction_region_checks = []
    for _ in range(4):
        checkbox = QCheckBox()
        checkbox.toggled.connect(self._update_direction_details)
        self.direction_region_checks.append(checkbox)
        proposal_layout.addWidget(checkbox)
    self.direction_download_button = QPushButton("Download proposal seed as .txt")
    self.direction_download_button.clicked.connect(self._download_direction_proposal)
    self.direction_download_status = QLabel("")
    self.direction_download_status.setObjectName("Muted")
    self.direction_download_status.setWordWrap(True)
    proposal_layout.addWidget(self.direction_download_button)
    proposal_layout.addWidget(self.direction_download_status)
    self.direction_proposal_panel.setVisible(False)
    control_layout.addWidget(self.direction_proposal_panel)

    cards = QHBoxLayout()
    cards.setSpacing(16)
    self.direction_selected_card = QTextBrowser()
    self.direction_selected_card.setObjectName("KnowledgeCard")
    self.direction_why_card = QTextBrowser()
    self.direction_why_card.setObjectName("KnowledgeCard")
    self.direction_methods_card = Card()
    self.direction_methods_card.setObjectName("KnowledgeCard")
    methods_layout = QVBoxLayout(self.direction_methods_card)
    methods_layout.setContentsMargins(18, 18, 18, 18)
    methods_layout.setSpacing(10)
    self.direction_methods_kicker = QLabel("USEFUL METHODS")
    self.direction_methods_kicker.setObjectName("Kicker")
    self.direction_methods_title = QLabel("Observation +\nmodeling toolkit")
    self.direction_methods_title.setObjectName("CardTitle")
    self.direction_methods_title.setWordWrap(True)
    self.direction_methods_chip_row = QWidget()
    self.direction_methods_chip_layout = QGridLayout(self.direction_methods_chip_row)
    self.direction_methods_chip_layout.setContentsMargins(0, 0, 0, 0)
    self.direction_methods_chip_layout.setHorizontalSpacing(6)
    self.direction_methods_chip_layout.setVerticalSpacing(6)
    methods_layout.addWidget(self.direction_methods_kicker)
    methods_layout.addWidget(self.direction_methods_title)
    methods_layout.addWidget(self.direction_methods_chip_row)
    methods_layout.addStretch(1)
    self.direction_method_chip_labels = []
    self.direction_summary_cards = [self.direction_selected_card, self.direction_why_card, self.direction_methods_card]
    for browser in [self.direction_selected_card, self.direction_why_card]:
        browser.setMinimumHeight(285)
        browser.setMaximumHeight(335)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cards.addWidget(browser)
    self.direction_methods_card.setMinimumHeight(285)
    self.direction_methods_card.setMaximumHeight(335)
    cards.addWidget(self.direction_methods_card)
    left_column.addLayout(cards)
    self.direction_proposal_title = QLabel("Generated research proposal seed")
    self.direction_proposal_title.setObjectName("PanelTitle")
    self.direction_proposal_title.setVisible(False)
    self.direction_proposal_text = QTextBrowser()
    self.direction_proposal_text.setObjectName("KnowledgeCard")
    self.direction_proposal_text.setMinimumHeight(430)
    self.direction_proposal_text.setVisible(False)
    left_column.addWidget(self.direction_proposal_title)
    left_column.addWidget(self.direction_proposal_text)
    left_column.addStretch(1)
    top.addLayout(left_column, 7)
    top.addWidget(control, 3)
    layout.addLayout(top)

    self.direction_visual = CompassPlotWidget()
    layout.addWidget(self.direction_visual, 1)
    seed_title = QLabel("Research seed cards")
    seed_title.setObjectName("PanelTitle")
    layout.addWidget(seed_title)
    seed_row = QHBoxLayout()
    seed_row.setSpacing(16)
    self.direction_seed_gap = QTextBrowser()
    self.direction_seed_gap.setObjectName("KnowledgeCard")
    self.direction_seed_questions = QTextBrowser()
    self.direction_seed_questions.setObjectName("KnowledgeCard")
    for browser in [self.direction_seed_gap, self.direction_seed_questions]:
        browser.setMinimumHeight(190)
        browser.setMaximumHeight(230)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        seed_row.addWidget(browser)
    layout.addLayout(seed_row)
    self._update_direction_details()
    return page


def _set_direction_mode(self, mode):
    self.direction_view_mode = mode
    for value, radio in getattr(self, "direction_mode_radios", {}).items():
        radio.blockSignals(True)
        radio.setChecked(value == mode)
        radio.blockSignals(False)
    if hasattr(self, "direction_visual"):
        self.direction_visual.set_mode(mode)
        self.direction_visual.setVisible(mode != "Proposal builder")
    if hasattr(self, "direction_proposal_title"):
        self.direction_proposal_title.setVisible(mode == "Proposal builder")
    if hasattr(self, "direction_proposal_text"):
        self.direction_proposal_text.setVisible(mode == "Proposal builder")
    if hasattr(self, "direction_proposal_panel"):
        self.direction_proposal_panel.setVisible(mode == "Proposal builder")
    if hasattr(self, "direction_download_status") and mode != "Proposal builder":
        self.direction_download_status.setText("")
    self._update_direction_details()


def _sync_direction_proposal_controls(self, info):
    if not hasattr(self, "direction_question_combo"):
        return
    self.direction_question_combo.blockSignals(True)
    self.direction_question_combo.clear()
    self.direction_question_combo.addItems(info["starter_questions"])
    self.direction_question_combo.blockSignals(False)
    for index, checkbox in enumerate(self.direction_method_checks):
        checkbox.blockSignals(True)
        if index < len(info["methods"]):
            checkbox.setText(info["methods"][index])
            checkbox.setChecked(index < 2)
            checkbox.setVisible(True)
        else:
            checkbox.setVisible(False)
        checkbox.blockSignals(False)
    for index, checkbox in enumerate(self.direction_region_checks):
        checkbox.blockSignals(True)
        if index < len(info["regions"]):
            checkbox.setText(info["regions"][index])
            checkbox.setChecked(index < 2)
            checkbox.setVisible(True)
        else:
            checkbox.setVisible(False)
        checkbox.blockSignals(False)


def _direction_selected_focus(self, info):
    question = info["starter_questions"][0]
    if hasattr(self, "direction_question_combo") and combo_current_key(self.direction_question_combo):
        question = combo_current_key(self.direction_question_combo)
    methods = [checkbox.text() for checkbox in getattr(self, "direction_method_checks", []) if checkbox.isVisible() and checkbox.isChecked()]
    regions = [checkbox.text() for checkbox in getattr(self, "direction_region_checks", []) if checkbox.isVisible() and checkbox.isChecked()]
    return question, methods or info["methods"][:2], regions or info["regions"][:2]


def _direction_proposal_text(self, name, info, question, method_focus, region_focus, ambition):
    ambition_text = {
        1: "a small class-project style literature synthesis",
        2: "a focused exploratory analysis",
        3: "a feasible undergraduate research proposal",
        4: "an ambitious portfolio project with visualization or modeling",
        5: "a high-end PhD-style frontier proposal",
    }.get(ambition, "a feasible undergraduate research proposal")
    methods = ", ".join(method_focus) if method_focus else "selected observations and models"
    regions = ", ".join(region_focus) if region_focus else "a suitable Antarctic case region"
    return (
        f"Title: {name}: {question}\n\n"
        f"Research style: {ambition_text}\n\n"
        "Motivation:\n"
        f"{info['why_now']}\n\n"
        "Knowledge gap:\n"
        f"{info['gap']}\n\n"
        "Possible approach:\n"
        f"Use {methods} focused on {regions}. The goal is to connect mechanism, observation, and uncertainty rather than only summarize the paper.\n\n"
        "Expected output:\n"
        "1. A concept map of the mechanism.\n"
        "2. A small evidence table linking observations to physical interpretation.\n"
        "3. A visual figure or interactive module that explains the research direction.\n"
        "4. A short uncertainty paragraph explaining what remains unknown.\n\n"
        "Why this fits your Atlas:\n"
        f"{info['student_angle']}"
    )


def _direction_proposal_filename(self, name):
    safe = name.lower().replace(" ", "_").replace("-", "_")
    safe = re.sub(r"[^a-z0-9_]+", "", safe)
    return f"research_direction_{safe}.txt"


def _download_direction_proposal(self):
    if not hasattr(self, "direction_combo"):
        return
    name = combo_current_key(self.direction_combo)
    info = DIRECTION_DATA.get(name, DIRECTION_DATA["Ocean heat pathways"])
    question, method_focus, region_focus = self._direction_selected_focus(info)
    ambition = self.direction_ambition.value() if hasattr(self, "direction_ambition") else 3
    proposal = self._direction_proposal_text(name, info, question, method_focus, region_focus, ambition)
    default_name = self._direction_proposal_filename(name)
    path, _ = QFileDialog.getSaveFileName(self, "Save proposal seed", default_name, "Text files (*.txt)")
    if not path:
        if hasattr(self, "direction_download_status"):
            self.direction_download_status.setText("Save cancelled.")
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(proposal)
    if hasattr(self, "direction_download_status"):
        self.direction_download_status.setText(f"Saved proposal seed to {path}")


def _update_direction_details(self):
    if not hasattr(self, "direction_combo"):
        return
    name = combo_current_key(self.direction_combo)
    info = DIRECTION_DATA.get(name, DIRECTION_DATA["Ocean heat pathways"])
    if getattr(self, "_direction_controls_name", None) != name:
        self._sync_direction_proposal_controls(info)
        self._direction_controls_name = name
    question, method_focus, region_focus = self._direction_selected_focus(info)
    ambition = self.direction_ambition.value() if hasattr(self, "direction_ambition") else 3
    if hasattr(self, "direction_ambition_value"):
        self.direction_ambition_value.setText(str(ambition))
    time_scale = info["time_scale"]
    if hasattr(self, "direction_metric_cards"):
        self.direction_metric_cards["Impact"].set_value(info["impact"], "/ 100")
        self.direction_metric_cards["Uncertainty"].set_value(info["uncertainty"], "/ 100")
        self.direction_metric_cards["Observability"].set_value(info["observability"], "/ 100")
        self.direction_metric_cards["Time scale"].set_value(time_scale, "")
    if hasattr(self, "direction_selected_card"):
        self.direction_selected_card.setHtml(f"<div class='ios-kicker'>SELECTED FRONTIER</div><h2>{html.escape(name)}</h2><p><b>Core question:</b><br>{html.escape(info['core_question'])}</p>")
        self.direction_why_card.setHtml(f"<div class='ios-kicker'>WHY IT MATTERS NOW</div><h2>{html.escape(info['system'])}</h2><p>{html.escape(info['why_now'])}</p>")
    if hasattr(self, "direction_methods_chip_layout"):
        while self.direction_methods_chip_layout.count():
            item = self.direction_methods_chip_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        self.direction_method_chip_labels = []
        for index, method in enumerate(info["methods"]):
            chip = QLabel(method)
            chip.setObjectName("MethodChip")
            chip.setWordWrap(True)
            chip.setAlignment(Qt.AlignCenter)
            chip.setMinimumHeight(28)
            chip.setMaximumHeight(42)
            if index < 3:
                self.direction_methods_chip_layout.addWidget(chip, 0, index)
            else:
                self.direction_methods_chip_layout.addWidget(chip, 1, 0, 1, 3)
            self.direction_method_chip_labels.append(chip)
    visual_info = dict(info)
    visual_info.update(active_question=question, active_methods=method_focus, active_regions=region_focus, active_ambition=ambition)
    if hasattr(self, "direction_visual"):
        self.direction_visual.set_direction(name, visual_info, DIRECTION_DATA)
    if hasattr(self, "direction_proposal_text"):
        proposal = self._direction_proposal_text(name, info, question, method_focus, region_focus, ambition)
        self.direction_proposal_text.setPlainText(proposal)
    if hasattr(self, "direction_seed_gap"):
        questions = "".join(f"<li>{html.escape(item)}</li>" for item in info["starter_questions"])
        self.direction_seed_gap.setHtml(
            f"<h3>Key gap</h3><p>{html.escape(info['gap'])}</p>"
            f"<h3>Beginner-researcher angle</h3><p>{html.escape(info['student_angle'])}</p>"
        )
        self.direction_seed_questions.setHtml(f"<h3>Starter questions</h3><ul>{questions}</ul>")
