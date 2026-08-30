from desktop_qt_app import *
from core.simulation import glacier_surface_melt_pressure


def _lab_zh():
    return current_locale().startswith("zh")


def _lab_text(en_text, zh_text=None):
    if zh_text and _lab_zh():
        return zh_text
    return translate_text(en_text)


_LAB_EXPERIMENT_LABELS = {
    "Glacier Flow Simulator": "冰川流动模拟器",
    "Ice Shelf Buttressing Lab": "冰架支撑实验室",
    "Hydrofracture & Ice Shelf Collapse Lab": "水力压裂和冰架塌陷实验室",
}

def _mini_lab_page(self):
    page, layout = self._page_shell(
        "Mini Research Lab",
        "",
    )
    exp_label = QLabel("Choose an experiment")
    exp_label.setObjectName("SmallLabel")
    layout.addWidget(exp_label)
    exp_row = QHBoxLayout()
    self.lab_experiment_buttons = []
    for index, name in enumerate(["Glacier Flow Simulator", "Ice Shelf Buttressing Lab", "Hydrofracture & Ice Shelf Collapse Lab"]):
        radio = QRadioButton(_lab_text(name, _LAB_EXPERIMENT_LABELS.get(name, name)).replace("&", "&&"))
        radio.setProperty("atlas_value", name)
        radio.setChecked(index == 0)
        radio.toggled.connect(lambda checked, value=name: checked and self._set_lab_experiment(value))
        self.lab_experiment_buttons.append(radio)
        exp_row.addWidget(radio)
    exp_row.addStretch(1)
    layout.addLayout(exp_row)

    self.lab_title = QLabel("Interactive Antarctic Ice Sheet Simulator")
    self.lab_title.setObjectName("SectionTitle")
    layout.addWidget(self.lab_title)
    guide = Card()
    guide_layout = QHBoxLayout(guide)
    guide_layout.setContentsMargins(14, 10, 14, 10)
    guide_layout.addWidget(QLabel("-"))
    self.lab_guide_label = QLabel("Legend and visual guide")
    guide_layout.addWidget(self.lab_guide_label, 1)
    layout.addWidget(guide)
    guide.setVisible(False)
    self.lab_guide_toggle = QPushButton("Legend and visual guide")
    self.lab_guide_toggle.setObjectName("ExpanderButton")
    self.lab_guide_toggle.setCheckable(True)
    self.lab_guide_toggle.clicked.connect(self._toggle_lab_guide)
    layout.addWidget(self.lab_guide_toggle)
    self.lab_preset_label = QLabel("Preset glacier mode")
    self.lab_preset_label.setObjectName("SmallLabel")
    layout.addWidget(self.lab_preset_label)
    self.lab_preset_combo = QComboBox()
    self.lab_preset_combo.addItems(["Custom", "Thwaites-like", "Pine Island-like", "Totten-like"])
    self.lab_preset_combo.currentTextChanged.connect(self._apply_lab_preset)
    layout.addWidget(self.lab_preset_combo)
    self.lab_caption = QLabel("")
    self.lab_caption.setObjectName("Muted")
    self.lab_caption.setWordWrap(True)
    layout.addWidget(self.lab_caption)
    self.lab_experiment_note = QTextBrowser()
    self.lab_experiment_note.setObjectName("KnowledgeCard")
    self.lab_experiment_note.setMaximumHeight(126)
    self.lab_experiment_note.setVisible(False)
    layout.addWidget(self.lab_experiment_note)

    self.lab_controls_grid = QGridLayout()
    self.lab_sliders = {}
    self.lab_control_widgets = []
    self.lab_control_titles = []
    self.lab_control_values = []
    self.lab_control_sliders = []
    self.lab_control_notes = []
    controls = [
        ("Simulation Year", 2025, 2100, 2025, "Controls long-term climate forcing."),
        ("Air Temperature (°C)", -50, 0, -20, "Higher air temperature increases surface-related ice loss."),
        ("Ocean Temperature / CDW Forcing (°C)", -20, 50, 0, "Higher values enhance basal melting and retreat."),
        ("Snowfall / Accumulation (m/yr)", 0, 50, 10, "More snowfall thickens ice and partly offsets melting."),
        ("Ice Shelf Thickness (m)", 50, 500, 200, "Thicker shelves provide stronger buttressing."),
        ("Basal Friction (0=low, 1=high)", 0, 100, 50, "Lower friction allows faster ice flow."),
        ("Bed Slope / Retrograde Bed Strength (°)", 0, 50, 10, "Higher values make MISI-like retreat easier."),
    ]
    for index, (label, minimum, maximum, value, caption) in enumerate(controls):
        cell = QWidget()
        cell_layout = QVBoxLayout(cell)
        cell_layout.setContentsMargins(0, 0, 16, 0)
        cell_layout.setSpacing(4)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel(label)
        title.setProperty("atlas_key", label)
        title.setObjectName("SmallLabel")
        value_label = QLabel("")
        value_label.setObjectName("SliderValue")
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider = QSlider(Qt.Horizontal)
        slider.setAccessibleName(_lab_text(label))
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(self._update_lab)
        note = QLabel(caption)
        note.setObjectName("Muted")
        note.setWordWrap(True)
        header.addWidget(title, 1)
        header.addWidget(value_label)
        cell_layout.addLayout(header)
        cell_layout.addWidget(slider)
        cell_layout.addWidget(note)
        self.lab_sliders[label] = slider
        self.lab_control_widgets.append(cell)
        self.lab_control_titles.append(title)
        self.lab_control_values.append(value_label)
        self.lab_control_sliders.append(slider)
        self.lab_control_notes.append(note)
        self.lab_controls_grid.addWidget(cell, index % 3, index // 3)
    self.misi_check = QCheckBox("Enable MISI feedback")
    self.misi_check.setChecked(True)
    self.shelf_collapse_check = QCheckBox("Ice Shelf Collapse")
    self.cdw_check = QCheckBox("CDW Warm Water Intrusion")
    self.cdw_check.setChecked(True)
    for checkbox in [self.misi_check, self.shelf_collapse_check, self.cdw_check]:
        checkbox.toggled.connect(self._update_lab)
    self.lab_controls_grid.addWidget(self.misi_check, 1, 2)
    self.lab_controls_grid.addWidget(self.shelf_collapse_check, 2, 2)
    self.lab_controls_grid.addWidget(self.cdw_check, 3, 2)
    layout.addLayout(self.lab_controls_grid)

    self.lab_diagnosis = QTextBrowser()
    self.lab_diagnosis.setObjectName("KnowledgeCard")
    self.lab_diagnosis.setMaximumHeight(150)
    self.lab_diagnosis.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    layout.addWidget(self.lab_diagnosis)

    self.lab_canvas = LabCanvasWidget()
    layout.addWidget(self.lab_canvas, 1)

    self.lab_metrics_row = QHBoxLayout()
    self.lab_metric_cards = {
        "Ice Loss": StatCard("Ice Loss", "0.00", "Conceptual index"),
        "Grounding Line Retreat": StatCard("Grounding Line Retreat", "0.0 km", "Retreat proxy"),
        "Ice Flow Velocity": StatCard("Ice Flow Velocity", "0.00 km/yr", "Relative speed"),
        "Sea Level Contribution": StatCard("Sea Level Contribution", "0.00 m", "Scenario signal"),
    }
    for card in self.lab_metric_cards.values():
        self.lab_metrics_row.addWidget(card)
    layout.addLayout(self.lab_metrics_row)
    self.lab_sea_level_signal = StatCard("Conceptual Sea-level Signal", "0.00 m", "Hydrofracture scenario signal")
    self.lab_sea_level_signal.setVisible(False)
    layout.addWidget(self.lab_sea_level_signal)
    self.current_lab_experiment = "Glacier Flow Simulator"
    self._set_lab_experiment("Glacier Flow Simulator")
    return page


def _format_lab_control_value(self, label, value):
    if label == "Simulation Year":
        return str(value)
    if "Temperature" in label or "Forcing (°C)" in label or "Slope" in label or "Snowfall" in label:
        return f"{value / 10:.1f}"
    if "Friction" in label:
        return f"{value / 100:.2f}"
    if "%" in label:
        return f"{value}%"
    return str(value)


def _refresh_lab_control_values(self):
    if not hasattr(self, "lab_control_values"):
        return
    for control, title, value_label, slider in zip(self.lab_control_widgets, self.lab_control_titles, self.lab_control_values, self.lab_control_sliders):
        if not control.isHidden():
            value_label.setText(self._format_lab_control_value(title.property("atlas_key") or title.text(), slider.value()))
            value_label.setVisible(True)
        else:
            value_label.setVisible(False)


def _update_lab(self):
    if not hasattr(self, "lab_control_sliders"):
        return
    self._refresh_lab_control_values()
    experiment = getattr(self, "current_lab_experiment", "Glacier Flow Simulator")
    slider = lambda index: self.lab_control_sliders[index].value()

    if experiment == "Ice Shelf Buttressing Lab":
        shelf = slider(0)
        ocean = slider(1) / 10
        pinning = slider(2)
        calving = slider(3)
        lateral = slider(4)
        bed = slider(5) / 10
        thickness_factor = shelf / 700
        pinning_factor = pinning / 100
        lateral_factor = lateral / 100
        calving_factor = calving / 100
        ocean_factor = max(ocean, 0) / 5
        buttressing = 100 * (0.45 * thickness_factor + 0.30 * pinning_factor + 0.25 * lateral_factor)
        buttressing *= 1 - 0.75 * calving_factor
        buttressing *= 1 - 0.45 * ocean_factor
        buttressing = max(0, min(100, buttressing))
        velocity_myr = 180 + (100 - buttressing) * 8.5 + ocean_factor * 260 + bed * 55
        retreat = max(0, min(45, (100 - buttressing) * 0.18 + ocean_factor * 8 + bed * 2.0))
        sea_level = retreat * 0.011
        values = {
            "shelf": shelf,
            "ocean": ocean,
            "pinning": pinning,
            "calving": calving,
            "lateral": lateral,
            "bed": bed,
            "buttressing": buttressing,
            "velocity_myr": velocity_myr,
            "retreat": retreat,
            "sea_level": sea_level,
        }
        metrics = [
            ("Buttressing Index", f"{buttressing:.0f} / 100", "Back-stress support"),
            ("Ice Flow Velocity", f"{velocity_myr:.0f} m/yr", "Grounded ice speed"),
            ("Grounding Line Retreat", f"{retreat:.1f} km", "Retreat proxy"),
            ("Sea Level Contribution", f"{sea_level:.2f} m", "Scenario signal"),
        ]
        if _lab_zh():
            diagnosis = (
                "<p><b>阅读方法：</b>较厚、受侧向约束并被固定点牵制的冰架，会以蓝色背应力箭头"
                "支撑陆地冰；变薄、崩解、暖海水强迫或固定作用减弱都会降低支撑。<br>"
                f"<b>当前诊断：</b>支撑指数为 {buttressing:.0f}/100，概念性冰流速度约为 "
                f"{velocity_myr:.0f} m/yr，后退压力为 {retreat:.1f} km。</p>"
            )
        else:
            diagnosis = (
                "<p><b>How to read this lab:</b> thick, laterally confined, pinned shelves push blue back-stress arrows "
                "against grounded ice; thinning, calving, warm ocean forcing, or weak pinning reduce support.<br>"
                f"<b>Current diagnosis:</b> buttressing is {buttressing:.0f}/100, with about {velocity_myr:.0f} m/yr "
                f"of conceptual ice speed and {retreat:.1f} km of retreat pressure.</p>"
            )
    elif experiment == "Hydrofracture & Ice Shelf Collapse Lab":
        surface_melt = slider(0)
        firn = slider(1)
        crevasse = slider(2)
        strength = slider(3)
        swell = slider(4)
        play_stage = slider(5)
        ponding = max(0, min(1, (surface_melt * 0.75 - firn * 0.45 + 20) / 100))
        fracture = max(0, min(1, 0.45 * ponding + 0.30 * (crevasse / 100) + 0.20 * (swell / 100) - 0.25 * (strength / 100)))
        collapse_risk = max(0, min(100, 100 * (0.55 * fracture + 0.35 * ponding + 0.10 * (swell / 100))))
        if collapse_risk < 25:
            auto_stage = 0
        elif collapse_risk < 45:
            auto_stage = 1
        elif collapse_risk < 65:
            auto_stage = 2
        elif collapse_risk < 82:
            auto_stage = 3
        else:
            auto_stage = 4
        stage = max(play_stage, auto_stage)
        buttressing_remaining = max(0, min(100, 100 - collapse_risk * 0.85 - (25 if stage >= 3 else 0)))
        post_collapse_velocity = 300 + (100 - buttressing_remaining) * 18
        sea_level_signal = (100 - buttressing_remaining) * 0.018
        stage_labels = [
            "0 Intact shelf",
            "1 Melt ponds form",
            "2 Water-filled cracks deepen",
            "3 Shelf fragments",
            "4 Breakup and flow acceleration",
        ]
        display_stage_labels = [
            _lab_text("0 Intact shelf", "0 完整冰架"),
            _lab_text("1 Melt ponds form", "1 融水池形成"),
            _lab_text("2 Water-filled cracks deepen", "2 充水裂缝加深"),
            _lab_text("3 Shelf fragments", "3 冰架碎裂"),
            _lab_text("4 Breakup and flow acceleration", "4 破碎并加速流动"),
        ]
        values = {
            "surface_melt": surface_melt,
            "firn": firn,
            "crevasse": crevasse,
            "strength": strength,
            "swell": swell,
            "play_stage": play_stage,
            "auto_stage": auto_stage,
            "stage": stage,
            "ponding": ponding,
            "fracture": fracture,
            "collapse_risk": collapse_risk,
            "buttressing_remaining": buttressing_remaining,
            "post_collapse_velocity": post_collapse_velocity,
            "sea_level": sea_level_signal,
        }
        metrics = [
            ("Ponding Index", f"{ponding * 100:.0f} / 100", "Surface water load"),
            ("Fracture Index", f"{fracture * 100:.0f} / 100", "Crack propagation"),
            ("Buttressing Remaining", f"{buttressing_remaining:.0f} / 100", "Shelf support left"),
            ("Post-collapse Velocity", f"{post_collapse_velocity:.0f} m/yr", "Inland acceleration"),
        ]
        if _lab_zh():
            diagnosis = (
                f"<p><b>自动诊断阶段：</b>{auto_stage}。<b>展示阶段：</b>{stage}（{display_stage_labels[stage]}），"
                "取自动诊断阶段和手动滑块阶段中的较高值。<br>"
                "<b>机制：</b>表面融水形成池塘；较低的 firn 空气容量会让水进入裂隙；"
                "连通裂隙会使冰架破碎，并加速内陆冰流。</p>"
            )
        else:
            diagnosis = (
                f"<p><b>Auto-diagnosed stage:</b> {auto_stage}. <b>Displayed stage:</b> {stage} ({stage_labels[stage]}), "
                "using the larger of the auto stage and manual slider.<br>"
                "<b>Mechanism:</b> surface melt creates ponds; low firn capacity lets water fill crevasses; connected "
                "fractures fragment the shelf and accelerate inland ice.</p>"
            )
    else:
        year = slider(0)
        air_temp = slider(1) / 10
        ocean = slider(2) / 10
        snowfall = slider(3) / 10
        shelf = slider(4)
        friction = slider(5) / 100
        bed = slider(6) / 10
        time_factor = (year - 2025) / 75
        misi_on = bool(getattr(self, "misi_check", None) and self.misi_check.isChecked())
        shelf_collapse = bool(getattr(self, "shelf_collapse_check", None) and self.shelf_collapse_check.isChecked())
        cdw_intrusion = bool(getattr(self, "cdw_check", None) and self.cdw_check.isChecked())
        effective_ocean = ocean + (1.2 * time_factor if cdw_intrusion else 0.2 * time_factor)
        effective_shelf = shelf * ((1 - 0.45 * time_factor) if shelf_collapse else (1 - 0.12 * time_factor))
        effective_shelf = max(effective_shelf, 20)
        retreat = 8 + effective_ocean * 7.0 + bed * 5.0 - effective_shelf * 0.045 - friction * 9.0
        if misi_on and bed > 1.5 and effective_ocean > 0.5:
            retreat *= 1 + 0.55 * bed + 0.25 * effective_ocean
        if shelf_collapse:
            retreat *= 1.45
        if cdw_intrusion:
            retreat *= 1.18
        retreat = max(0, min(68, retreat))
        velocity_strength = max(0.08, 0.35 + effective_ocean * 0.30 + (1 - friction) * 1.45 + bed * 0.18 + time_factor * 0.45)
        if misi_on and retreat > 20:
            velocity_strength *= 1.45
        if shelf_collapse:
            velocity_strength *= 1.35
        surface_melt_pressure = glacier_surface_melt_pressure(air_temp)
        ice_loss = ((surface_melt_pressure + max(effective_ocean, 0) * 2.6) * (1.25 - friction * 0.65) / (snowfall + 0.5))
        velocity = velocity_strength * 1.8
        sea_level = retreat * 0.013
        values = {
            "year": year,
            "air_temp": air_temp,
            "surface_melt_pressure": surface_melt_pressure,
            "ocean": ocean,
            "snowfall": snowfall,
            "shelf": shelf,
            "friction": friction,
            "bed": bed,
            "effective_ocean": effective_ocean,
            "effective_shelf": effective_shelf,
            "misi_on": misi_on,
            "shelf_collapse": shelf_collapse,
            "cdw_intrusion": cdw_intrusion,
            "ice_loss": ice_loss,
            "velocity": velocity,
            "retreat": retreat,
            "sea_level": sea_level,
        }
        metrics = [
            ("Ice Loss", f"{ice_loss:.2f}", "Conceptual index"),
            ("Grounding Line Retreat", f"{retreat:.1f} km", "Retreat proxy"),
            ("Ice Flow Velocity", f"{velocity:.2f} km/yr", "Relative speed"),
            ("Sea Level Contribution", f"{sea_level:.2f} m", "Scenario signal"),
        ]
        active_flags = []
        if misi_on:
            active_flags.append(_lab_text("MISI feedback", "MISI 反馈"))
        if shelf_collapse:
            active_flags.append(_lab_text("ice-shelf collapse", "冰架崩解"))
        if cdw_intrusion:
            active_flags.append(_lab_text("CDW warm-water intrusion", "CDW 暖水入侵"))
        flags = ", ".join(active_flags) if active_flags else _lab_text("no nonlinear feedback toggles", "未启用非线性反馈开关")
        if _lab_zh():
            diagnosis = (
                "<p><b>图例：</b>白蓝色为接地冰体，浅蓝色为浮动冰架，棕色为基岩，红线为接地线，"
                "橙色箭头为冰流，青色粒子为冰体单元，暖色区域为 CDW 强迫。<br>"
                f"<b>当前诊断：</b>{flags}。有效冰架厚度为 {effective_shelf:.0f} m，后退压力为 {retreat:.1f} km。</p>"
            )
        else:
            diagnosis = (
                "<p><b>Legend:</b> white-blue grounded ice, light-blue floating shelf, brown bedrock, red grounding line, "
                "orange flow arrows, cyan ice parcels, and warm CDW forcing.<br>"
                f"<b>Current diagnosis:</b> {flags}. Effective shelf thickness is {effective_shelf:.0f} m and retreat pressure is {retreat:.1f} km.</p>"
            )
    if hasattr(self, "lab_canvas"):
        self.lab_canvas.set_values(values)
    if hasattr(self, "lab_metric_cards"):
        for card, (label, value, detail) in zip(self.lab_metric_cards.values(), metrics):
            card.label_widget.setText(translate_text(label))
            card.set_value(value, translate_text(detail))
    if hasattr(self, "lab_diagnosis"):
        self.lab_diagnosis.setHtml(diagnosis)
        self.lab_diagnosis.setVisible(True)
    if hasattr(self, "lab_sea_level_signal"):
        if experiment == "Hydrofracture & Ice Shelf Collapse Lab":
            self.lab_sea_level_signal.set_value(f"{values.get('sea_level', 0):.2f} m", "Conceptual scenario signal")
            self.lab_sea_level_signal.setVisible(True)
        else:
            self.lab_sea_level_signal.setVisible(False)


def _apply_lab_preset(self, preset):
    if getattr(self, "current_lab_experiment", "Glacier Flow Simulator") != "Glacier Flow Simulator":
        return
    presets = {
        "Custom": (0, 10, 200, 50, 10),
        "Thwaites-like": (20, 10, 160, 25, 32),
        "Pine Island-like": (17, 11, 180, 30, 28),
        "Totten-like": (12, 15, 240, 45, 20),
    }
    if preset not in presets or not hasattr(self, "lab_sliders"):
        return
    ocean, snow, shelf, friction, bed = presets[preset]
    self.lab_sliders["Ocean Temperature / CDW Forcing (°C)"].setValue(ocean)
    self.lab_sliders["Snowfall / Accumulation (m/yr)"].setValue(snow)
    self.lab_sliders["Ice Shelf Thickness (m)"].setValue(shelf)
    self.lab_sliders["Basal Friction (0=low, 1=high)"].setValue(friction)
    self.lab_sliders["Bed Slope / Retrograde Bed Strength (°)"].setValue(bed)
    self._update_lab()


def _configure_lab_controls(self, experiment):
    control_sets = {
        "Glacier Flow Simulator": [
            ("Simulation Year", 2025, 2100, 2025, "Controls long-term climate forcing."),
            ("Air Temperature (°C)", -50, 0, -20, "Higher air temperature increases surface-related ice loss."),
            ("Ocean Temperature / CDW Forcing (°C)", -20, 50, 0, "Higher values enhance basal melting and retreat."),
            ("Snowfall / Accumulation (m/yr)", 0, 50, 10, "More snowfall thickens ice and partly offsets melting."),
            ("Ice Shelf Thickness (m)", 50, 500, 200, "Thicker shelves provide stronger buttressing."),
            ("Basal Friction (0=low, 1=high)", 0, 100, 50, "Lower friction allows faster ice flow."),
            ("Bed Slope / Retrograde Bed Strength (°)", 0, 50, 10, "Higher values make MISI-like retreat easier."),
        ],
        "Ice Shelf Buttressing Lab": [
            ("Ice Shelf Thickness (m)", 50, 700, 260, "Thicker ice shelves provide stronger mechanical support."),
            ("Ocean Temperature Forcing (°C)", -20, 50, 10, "Warmer ocean water increases basal melting from below."),
            ("Pinning Point Strength (%)", 0, 100, 55, "Pinning points help the ice shelf resist flow."),
            ("Calving / Shelf Loss (%)", 0, 100, 20, "Shelf loss removes floating area and reduces buttressing."),
            ("Lateral Confinement (%)", 0, 100, 60, "Side walls and embayments strengthen buttressing."),
            ("Retrograde Bed Slope (°)", 0, 50, 15, "Retrograde beds make grounding-line retreat more unstable."),
        ],
        "Hydrofracture & Ice Shelf Collapse Lab": [
            ("Surface Melt Intensity (%)", 0, 100, 45, "More melt produces more surface ponds."),
            ("Firn Air Capacity (%)", 0, 100, 45, "Higher firn capacity absorbs meltwater and delays ponding."),
            ("Crevasse Density (%)", 0, 100, 40, "More crevasses make hydrofracture easier."),
            ("Ice Shelf Strength (%)", 0, 100, 60, "Stronger ice resists crack propagation."),
            ("Ocean Swell / Flexure (%)", 0, 100, 35, "Swell and flexure help fractures widen and connect."),
            ("Collapse Stage", 0, 4, 2, "Move through intact shelf, ponds, cracks, fragmentation, and acceleration."),
        ],
    }
    controls = control_sets.get(experiment, control_sets["Glacier Flow Simulator"])
    self.lab_sliders = {}
    for index, control in enumerate(self.lab_control_widgets):
        visible = index < len(controls)
        control.setVisible(visible)
        if not visible:
            continue
        label, minimum, maximum, value, caption = controls[index]
        slider = self.lab_control_sliders[index]
        self.lab_control_titles[index].setProperty("atlas_key", label)
        self.lab_control_titles[index].setText(label)
        self.lab_control_notes[index].setText(caption)
        slider.blockSignals(True)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.blockSignals(False)
        self.lab_sliders[label] = slider
    self._refresh_lab_control_values()
    for checkbox in [self.misi_check, self.shelf_collapse_check, self.cdw_check]:
        checkbox.setVisible(experiment == "Glacier Flow Simulator")


def _toggle_lab_guide(self, checked=False):
    if hasattr(self, "lab_experiment_note"):
        self.lab_experiment_note.setVisible(bool(checked))
    if hasattr(self, "lab_guide_toggle"):
        base = getattr(self, "lab_guide_title", "Legend and visual guide")
        self.lab_guide_toggle.setText(f"{base} (open)" if checked else base)


def _set_lab_experiment(self, name):
    self.current_lab_experiment = name
    if hasattr(self, "lab_experiment_buttons"):
        for radio in self.lab_experiment_buttons:
            radio.blockSignals(True)
            value = radio.property("atlas_value") or radio.text().replace("&&", "&")
            radio.setText(_lab_text(value, _LAB_EXPERIMENT_LABELS.get(value, value)).replace("&", "&&"))
            radio.setChecked(value == name)
            radio.blockSignals(False)
    titles = {
        "Glacier Flow Simulator": "Interactive Antarctic Ice Sheet Simulator",
        "Ice Shelf Buttressing Lab": "Ice Shelf Buttressing Lab",
        "Hydrofracture & Ice Shelf Collapse Lab": _lab_text("Hydrofracture & Ice Shelf Collapse Lab", "水力压裂和冰架塌陷实验室"),
    }
    captions = {
        "Glacier Flow Simulator": "Choose a conceptual glacier setting. The preset changes ocean forcing, ice shelf thickness, basal friction, and bed slope to resemble different Antarctic glacier styles.",
        "Ice Shelf Buttressing Lab": "This conceptual lab focuses on one mechanism: a floating ice shelf can provide back stress that slows down inland grounded ice.",
        "Hydrofracture & Ice Shelf Collapse Lab": "This conceptual lab visualizes how atmospheric warming can create surface meltwater, deepen crevasses, and fragment an ice shelf.",
    }
    guide_bodies = {
        "Glacier Flow Simulator": (
            "<ul>"
            "<li><b>White-blue surface:</b> Grounded ice sheet. Darker blue means thicker ice.</li>"
            "<li><b>Light blue floating surface:</b> Floating ice shelf extending over the ocean.</li>"
            "<li><b>Brown surface:</b> Bedrock beneath the ice.</li>"
            "<li><b>Transparent blue plane:</b> Ocean surface.</li>"
            "<li><b>Red line:</b> Grounding line, where grounded ice begins to float.</li>"
            "<li><b>Orange line arrows:</b> Ice flow direction.</li>"
            "<li><b>Cyan moving particles:</b> Ice parcels moving downstream.</li>"
            "<li><b>Orange/red subsurface patch:</b> Warm Circumpolar Deep Water intrusion.</li>"
            "</ul>"
        ),
        "Ice Shelf Buttressing Lab": (
            "<ul>"
            "<li><b>Dark blue block:</b> Grounded ice sheet flowing toward the ocean.</li>"
            "<li><b>Light blue block:</b> Floating ice shelf.</li>"
            "<li><b>Orange arrows:</b> Relative ice-flow speed.</li>"
            "<li><b>Brown bump:</b> Pinning point / local topographic resistance.</li>"
            "<li><b>Red dashed line:</b> Grounding line.</li>"
            "<li><b>Gray removed zone:</b> Calved or collapsed ice-shelf area.</li>"
            "<li><b>Blue back-stress arrows:</b> Buttressing force pushing back against grounded ice.</li>"
            "</ul>"
        ),
        "Hydrofracture & Ice Shelf Collapse Lab": (
            "<ul>"
            "<li><b>Ice-blue slab:</b> Floating ice shelf.</li>"
            "<li><b>Deep blue ponds:</b> Surface meltwater ponds.</li>"
            "<li><b>Red cracks:</b> Hydrofracture pathways driven by water-filled crevasses.</li>"
            "<li><b>Gray separated blocks:</b> Collapsed / fragmented ice shelf pieces.</li>"
            "<li><b>Orange arrows:</b> Post-collapse acceleration of inland ice.</li>"
            "<li><b>Dark ocean background:</b> Open ocean beneath and around the floating shelf.</li>"
            "</ul>"
        ),
    }
    guide_titles = {
        "Glacier Flow Simulator": "Legend and visual guide",
        "Ice Shelf Buttressing Lab": "Legend and mechanism guide",
        "Hydrofracture & Ice Shelf Collapse Lab": "Legend and collapse sequence",
    }
    if hasattr(self, "lab_title"):
        self.lab_title.setText(titles.get(name, name))
    if hasattr(self, "lab_guide_label"):
        self.lab_guide_label.setText(guide_titles.get(name, "Legend and visual guide"))
    if hasattr(self, "lab_guide_toggle"):
        self.lab_guide_title = guide_titles.get(name, "Legend and visual guide")
        self.lab_guide_toggle.setChecked(False)
        self.lab_guide_toggle.setText(self.lab_guide_title)
    if hasattr(self, "lab_canvas"):
        self.lab_canvas.set_experiment(name)
    if hasattr(self, "lab_experiment_note"):
        self.lab_experiment_note.setHtml(guide_bodies.get(name, ""))
        self.lab_experiment_note.setVisible(False)
    if hasattr(self, "lab_caption"):
        self.lab_caption.setText(captions.get(name, ""))
    if hasattr(self, "lab_preset_combo"):
        self.lab_preset_combo.setVisible(name == "Glacier Flow Simulator")
    if hasattr(self, "lab_preset_label"):
        self.lab_preset_label.setVisible(name == "Glacier Flow Simulator")
    if hasattr(self, "lab_control_widgets"):
        self._configure_lab_controls(name)
    self._update_lab()
