from desktop_qt_app import *

def _antarctic_system_page(self):
    page, layout = self._page_shell(
        "🛰 Antarctic System Explorer",
        "Explore how different observation tools see the same Antarctic case study. Choose a glacier or ice-shelf case, then switch the sensor layer to see what that tool would reveal.",
    )
    caption = QLabel("Conceptual visualization: the base scene and sensor layers illustrate observation logic, not downloaded raw remote-sensing data.")
    caption.setObjectName("Muted")
    caption.setWordWrap(True)
    layout.addWidget(caption)

    controls = QGridLayout()
    case_label = QLabel("Case Study")
    case_label.setObjectName("SmallLabel")
    controls.addWidget(case_label, 0, 0)
    self.system_case_combo = QComboBox()
    self.system_case_combo.addItems(list(SYSTEM_CASES.keys()))
    controls.addWidget(self.system_case_combo, 1, 0, 1, 3)
    self.system_multilayer = QCheckBox("Multi-layer mode")
    self.system_multilayer.toggled.connect(self._sync_system_layers)
    controls.addWidget(self.system_multilayer, 1, 3)
    layer_title = QLabel("Observation layers")
    layer_title.setObjectName("Kicker")
    controls.addWidget(layer_title, 2, 0)
    layout.addLayout(controls)

    layer_row = QHBoxLayout()
    self.system_layer_buttons = {}
    for layer_name, meta in SYSTEM_LAYERS.items():
        button = QPushButton(meta["short"])
        button.setObjectName("LayerButton")
        button.setCheckable(True)
        button.clicked.connect(lambda checked=False, name=layer_name: self._toggle_system_layer(name))
        self.system_layer_buttons[layer_name] = button
        layer_row.addWidget(button)
    layout.addLayout(layer_row)

    self.system_scene = SensorSceneWidget()
    self.system_case_combo.currentTextChanged.connect(self._set_system_case)
    layout.addWidget(self.system_scene, 1)
    metrics = QHBoxLayout()
    self.system_metric_cards = {
        "Case": StatCard("Case", "Thwaites Glacier", "West Antarctica / Amundsen Sea Sector"),
        "Primary layer": StatCard("Primary layer", "Satellite Altimetry", "Surface elevation change"),
        "Visible layers": StatCard("Visible layers", "1", "Base scene plus selected observation layer"),
    }
    for card in self.system_metric_cards.values():
        metrics.addWidget(card)
    layout.addLayout(metrics)
    self.system_synthesis = QTextBrowser()
    self.system_synthesis.setObjectName("KnowledgeCard")
    self.system_synthesis.setMinimumHeight(190)
    self.system_synthesis.setVisible(False)
    system_summary_caption = QLabel("The text summarizes observation logic from the review-paper case studies.")
    system_summary_caption.setObjectName("Muted")
    system_summary_caption.setWordWrap(True)
    layout.addWidget(system_summary_caption)

    self.system_builder_toggle = QPushButton("Build the multi-sensor synthesis")
    self.system_builder_toggle.setObjectName("ExpanderButton")
    self.system_builder_toggle.setCheckable(True)
    self.system_builder_toggle.clicked.connect(self._toggle_system_builder)
    layout.addWidget(self.system_builder_toggle)
    self.system_builder_panel = QWidget()
    builder_panel_layout = QVBoxLayout(self.system_builder_panel)
    builder_panel_layout.setContentsMargins(0, 0, 0, 0)
    builder_panel_layout.setSpacing(10)
    builder_note = QLabel("Combine observation layers. Each selected sensor contributes a different kind of evidence; the goal is to show how a scientific conclusion is assembled.")
    builder_note.setObjectName("Muted")
    builder_note.setWordWrap(True)
    builder_panel_layout.addWidget(builder_note)
    self.system_builder_checks = {}
    builder_row = QHBoxLayout()
    for layer_name, meta in SYSTEM_LAYERS.items():
        checkbox = QCheckBox(meta["short"])
        checkbox.toggled.connect(self._on_system_builder_changed)
        self.system_builder_checks[layer_name] = checkbox
        builder_row.addWidget(checkbox)
    builder_row.addStretch(1)
    builder_panel_layout.addLayout(builder_row)

    self.system_evidence_builder = QTextBrowser()
    self.system_evidence_builder.setObjectName("KnowledgeCard")
    self.system_evidence_builder.setMinimumHeight(460)
    builder_panel_layout.addWidget(self.system_evidence_builder)
    self.system_builder_panel.setVisible(False)
    layout.addWidget(self.system_builder_panel)

    self.system_process_toggle = QPushButton("Physical-process context")
    self.system_process_toggle.setObjectName("ExpanderButton")
    self.system_process_toggle.setCheckable(True)
    self.system_process_toggle.clicked.connect(self._toggle_system_process_context)
    layout.addWidget(self.system_process_toggle)
    self.system_process_panel = QWidget()
    process_panel_layout = QVBoxLayout(self.system_process_panel)
    process_panel_layout.setContentsMargins(0, 0, 0, 0)
    process_panel_layout.setSpacing(10)
    self.system_process_combo = QComboBox()
    self.system_process_combo.addItems(list(SYSTEM_PROCESSES.keys()))
    self.system_process_combo.currentTextChanged.connect(self._update_system_process_context)
    process_panel_layout.addWidget(self.system_process_combo)
    self.system_process_context = QTextBrowser()
    self.system_process_context.setObjectName("KnowledgeCard")
    self.system_process_context.setMinimumHeight(150)
    process_panel_layout.addWidget(self.system_process_context)
    self.system_process_panel.setVisible(False)
    layout.addWidget(self.system_process_panel)

    self.system_active_layers = ["Satellite Altimetry"]
    self._set_system_layer("Satellite Altimetry")
    self._update_system_process_context()
    return page


def _set_system_case(self, name):
    if hasattr(self, "system_scene"):
        self.system_scene.set_case(name)
    self._update_system_synthesis(getattr(self, "system_active_layers", ["Satellite Altimetry"]))
    self._update_system_evidence_builder()
    self._update_system_process_context()


def _toggle_system_builder(self, checked=False):
    if hasattr(self, "system_builder_panel"):
        self.system_builder_panel.setVisible(bool(checked))
    if hasattr(self, "system_builder_toggle"):
        self.system_builder_toggle.setText("Build the multi-sensor synthesis (open)" if checked else "Build the multi-sensor synthesis")


def _toggle_system_process_context(self, checked=False):
    if hasattr(self, "system_process_panel"):
        self.system_process_panel.setVisible(bool(checked))
    if hasattr(self, "system_process_toggle"):
        self.system_process_toggle.setText("Physical-process context (open)" if checked else "Physical-process context")


def _toggle_system_layer(self, name):
    if hasattr(self, "system_multilayer") and self.system_multilayer.isChecked():
        layers = list(getattr(self, "system_active_layers", []))
        if name in layers and len(layers) > 1:
            layers.remove(name)
        elif name not in layers:
            layers.append(name)
        self.system_active_layers = layers
        self._sync_system_layers()
    else:
        self._set_system_layer(name)


def _set_system_layer(self, name):
    self.system_active_layers = [name]
    if hasattr(self, "system_scene"):
        self.system_scene.set_layer(name)
    for layer_name, button in getattr(self, "system_layer_buttons", {}).items():
        button.setChecked(layer_name == name)
    self._update_system_synthesis([name])
    self._set_system_builder_defaults(name)


def _sync_system_layers(self):
    layers = list(getattr(self, "system_active_layers", ["Satellite Altimetry"]))
    if hasattr(self, "system_multilayer") and self.system_multilayer.isChecked():
        if len(layers) == 1:
            layers = ["Satellite Altimetry", "InSAR Velocity", "GRACE / GRACE-FO"]
        self.system_active_layers = layers
        if hasattr(self, "system_scene"):
            self.system_scene.set_layers(layers)
        for layer_name, button in getattr(self, "system_layer_buttons", {}).items():
            button.setChecked(layer_name in layers)
        self._update_system_synthesis(layers)
        self._sync_system_builder_checks(layers)
    else:
        self._set_system_layer(layers[-1] if layers else "Satellite Altimetry")


def _update_system_synthesis(self, layers):
    if isinstance(layers, str):
        layers = [layers]
    layers = [name for name in layers if name in SYSTEM_LAYERS] or ["Satellite Altimetry"]
    layer_name = layers[-1]
    case_name = combo_current_key(self.system_case_combo) if hasattr(self, "system_case_combo") else "Thwaites Glacier"
    case = system_case(case_name)
    layer = system_tool(case_name, layer_name)
    if hasattr(self, "system_metric_cards"):
        self.system_metric_cards["Case"].set_value(case_name, case["region"])
        self.system_metric_cards["Primary layer"].set_value(layer_name, layer["measures"])
        self.system_metric_cards["Visible layers"].set_value(str(len(layers)), " + ".join(system_tool(case_name, name)["short"] for name in layers))
    if hasattr(self, "system_synthesis"):
        rows = "".join(
            f"<li><b>{html.escape(system_tool(case_name, name)['short'])}</b>: {html.escape(system_tool(case_name, name)['interpretation'])}</li>"
            for name in layers
        )
        self.system_synthesis.setHtml(
            f"<div class='ios-kicker'>OBSERVATION SUMMARY</div><h3>{html.escape(case_name)}</h3>"
            f"<p><b>Case context:</b> {html.escape(case['base_note'])}</p>"
            f"<p><b>{html.escape(layer_name)}:</b> {html.escape(layer['observed'])}</p>"
            f"<ul>{rows}</ul>"
        )


def _set_system_builder_defaults(self, selected_tool):
    if not hasattr(self, "system_builder_checks"):
        return
    if selected_tool in ["InSAR Velocity", "Satellite Altimetry"]:
        defaults = [selected_tool, "GRACE / GRACE-FO"]
    else:
        defaults = [selected_tool, "InSAR Velocity", "Satellite Altimetry"]
    self._sync_system_builder_checks(defaults)


def _sync_system_builder_checks(self, layers):
    if not hasattr(self, "system_builder_checks"):
        return
    clean_layers = [name for name in layers if name in SYSTEM_LAYERS] or ["Satellite Altimetry"]
    for layer_name, checkbox in self.system_builder_checks.items():
        checkbox.blockSignals(True)
        checkbox.setChecked(layer_name in clean_layers)
        checkbox.blockSignals(False)
    self._update_system_evidence_builder(clean_layers)


def _on_system_builder_changed(self, checked=False):
    selected = [
        layer_name
        for layer_name, checkbox in getattr(self, "system_builder_checks", {}).items()
        if checkbox.isChecked()
    ]
    self._update_system_evidence_builder(selected)


def _update_system_evidence_builder(self, layers=None):
    if not hasattr(self, "system_evidence_builder"):
        return
    case_name = combo_current_key(self.system_case_combo) if hasattr(self, "system_case_combo") else "Thwaites Glacier"
    case = system_case(case_name)
    if layers is None:
        layers = [
            layer_name
            for layer_name, checkbox in getattr(self, "system_builder_checks", {}).items()
            if checkbox.isChecked()
        ]
    layers = [name for name in layers if name in SYSTEM_LAYERS]
    if not layers:
        self.system_evidence_builder.setHtml(
            "<div class='ios-kicker'>EVIDENCE BUILDER</div>"
            "<p>Select one or more layers to build a scientific synthesis.</p>"
        )
        return
    cards = []
    for layer_name in layers:
        tool = system_tool(case_name, layer_name)
        cards.append(
            f"<p><b>{html.escape(tool['short'])} - {html.escape(layer_name)}</b><br>"
            f"<span style='color:#9adfff'>Measures:</span> {html.escape(tool['measures'])}<br>"
            f"<span style='color:#9adfff'>Observed:</span> {html.escape(tool['observed'])}</p>"
        )
    self.system_evidence_builder.setHtml(
        "<div class='ios-kicker'>EVIDENCE BUILDER</div>"
        "<h3>Build the multi-sensor synthesis</h3>"
        "<p>Each selected sensor contributes a different evidence dimension; together they assemble a scientific conclusion.</p>"
        + "".join(cards)
        + f"<p><b>Synthesis:</b> For <b>{html.escape(case_name)}</b>, these layers support the theme: <b>{html.escape(case['main_theme'])}</b>.</p>"
    )


def _update_system_process_context(self, process_name=None):
    if not hasattr(self, "system_process_context"):
        return
    if not process_name and hasattr(self, "system_process_combo"):
        process_name = combo_current_key(self.system_process_combo)
    process_name = process_name or "Ocean Forcing"
    text = SYSTEM_PROCESSES.get(process_name, SYSTEM_PROCESSES["Ocean Forcing"])
    self.system_process_context.setHtml(
        "<div class='ios-kicker'>PHYSICAL-PROCESS CONTEXT</div>"
        f"<h3>{html.escape(process_name)}</h3>"
        f"<p>{html.escape(text)}</p>"
    )
