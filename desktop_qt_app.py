import html
import json
import os
import re
import sys
import time
from math import atan2, cos, pi, sin
from pathlib import Path

import requests
import jieba
from PySide6.QtCore import QEasingCurve, QObject, QPointF, QProcess, QPropertyAnimation, QRectF, QSize, Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QBrush, QColor, QDesktopServices, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qt_app.config import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    OLLAMA_MODEL,
    OLLAMA_URL,
    ORCAROUTER_BASE_URL,
    ORCAROUTER_MODEL,
    ORCAROUTER_MODEL_OPTIONS,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    OPENAI_MODEL_OPTIONS,
    PDF_FILENAME,
    PDF_PATH,
)
from qt_app.i18n import combo_current_key, current_locale, install_qt_i18n_hooks, localize_runtime_globals, localize_widget_tree, set_locale, t, translate_html, translate_text
from core.data import load_data_json, resource_path
from core.paper import (CHINESE_PAPER_KEYWORDS, build_search_excerpt, clean_answer_markdown, clean_text, extract_paper_keywords, extract_search_keywords, is_low_value_reference_page, is_overview_question, load_pdf_pages, scored_search_pages, scored_search_pages_by_keywords, search_pages)
from core.version import app_version
sys.modules.setdefault("desktop_qt_app", sys.modules[__name__])
install_qt_i18n_hooks()


APP_TITLE = "Antarctic Atlas"
APP_VERSION = app_version()
TARGET_FRAME_RATE = 120
FRAME_INTERVAL_MS = max(1, round(1000 / TARGET_FRAME_RATE))
SLOW_ANIMATION_INTERVAL_MS = 33
PACKAGED_SMOKE_ENV = "ANTARCTIC_ATLAS_SMOKE_TEST"


def _application_icon_path():
    return resource_path("antarctic_atlas.png")


def ui_font(point_size, weight=QFont.Normal):
    """Return the active platform UI font with the requested size and weight."""

    font = QFont(QApplication.font()) if QApplication.instance() else QFont()
    font.setPointSize(point_size)
    font.setWeight(weight)
    return font


class FunctionWorker(QThread):
    resultReady = Signal(object)
    errorReady = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            if not self.isInterruptionRequested():
                self.resultReady.emit(result)
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.errorReady.emit(str(exc))


class StreamWorker(QThread):
    chunkReady = Signal(str)
    resultReady = Signal(str)
    errorReady = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            def emit_chunk(piece):
                if not self.isInterruptionRequested():
                    self.chunkReady.emit(piece)

            result = self.fn(emit_chunk, *self.args, **self.kwargs)
            if not self.isInterruptionRequested():
                self.resultReady.emit(result)
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.errorReady.emit(str(exc))


UNIVERSE_TOPIC_DETAILS = load_data_json("topics.json")
RESEARCH_AREAS = load_data_json("research_areas.json")
UNIVERSE_TOPIC_KEYWORDS = load_data_json("keywords.json")


def universe_payload():
    areas = {}
    for area_name, area in RESEARCH_AREAS.items():
        topics = []
        for topic_name, why in area["topics"].items():
            detail = UNIVERSE_TOPIC_DETAILS.get(topic_name, {})
            topics.append(
                {
                    "name": topic_name,
                    "display_name": translate_text(topic_name),
                    "key_question": translate_text(detail.get("key_question", why)),
                    "why": translate_text(why),
                    "status": translate_text(detail.get("status", "Research frontier")),
                    "regions": translate_text(detail.get("regions", area_name)),
                }
            )
        areas[area_name] = {
            "display_name": translate_text(area_name),
            "status": translate_text("Research area"),
            "color": area["color"],
            "angle": {
                "Ocean": 160,
                "Ice Dynamics": 25,
                "Solid Earth": 270,
                "Observations": 90,
                "Paleoclimate": 215,
                "Future Projections": 325,
            }.get(area_name, 0),
            "key_question": translate_text(area["question"]),
            "importance": translate_text(area["why"]),
            "topics": topics,
        }
    return {
        "center": {
            "name": "Antarctic Ice Sheet",
            "display_name": translate_text("Antarctic Ice Sheet"),
            "type": translate_text("Core system"),
            "color": "#DDEEFF",
            "key_question": translate_text("How does the Antarctic Ice Sheet respond to climate forcing?"),
            "importance": translate_text("The central system linking atmosphere, ocean, ice dynamics, solid Earth, observations, paleoclimate evidence, and future sea-level risk."),
            "status": translate_text("Research hub"),
            "regions": translate_text("Antarctica and global coastlines"),
        },
        "areas": areas,
        "labels": {
            "title": translate_text("Antarctic Research Universe"),
            "subtitle": translate_text("Ask a question; AI locates the matching node. You can also click any sphere manually."),
            "hint": translate_text("Click a sphere · Ask below · matched module auto-focuses here"),
            "key_question": translate_text("KEY QUESTION"),
            "why_it_matters": translate_text("WHY IT MATTERS"),
            "research_status": translate_text("RESEARCH STATUS"),
            "key_regions": translate_text("KEY REGIONS / LINKED TOPICS"),
            "core_system": translate_text("Core system"),
            "research_area": translate_text("Research area"),
        },
    }


def original_universe_html(initial_focus_topic="", initial_focus_source="manual", initial_focus_token=0):
    template = resource_path("qt_app", "templates", "research_universe_template.html").read_text(encoding="utf-8")
    template = template.replace(
        "<script>",
        "<script src='qrc:///qtwebchannel/qwebchannel.js'></script>\n    <script>",
        1,
    )
    template = template.replace(
        "      const data = __DATA__;",
        "      let qtUniverseBridge = null;\n"
        "      if (window.qt && window.qt.webChannelTransport) {\n"
        "        new QWebChannel(window.qt.webChannelTransport, channel => { qtUniverseBridge = channel.objects.universeBridge; });\n"
        "      }\n"
        "      function notifyQtUniverseSelection(id) {\n"
        "        try { if (qtUniverseBridge && qtUniverseBridge.selectTopic) qtUniverseBridge.selectTopic(id); } catch (e) {}\n"
        "      }\n"
        "      const data = __DATA__;",
    )
    template = template.replace(
        'g.addEventListener("click", ev => { ev.stopPropagation(); focusedId === n.id ? resetUniverse() : focusNode(n); });',
        'g.addEventListener("click", ev => { ev.stopPropagation(); '
        'if (focusedId === n.id) { resetUniverse(); notifyQtUniverseSelection(data.center.name); } '
        'else { focusNode(n); notifyQtUniverseSelection(n.id); } });',
    )
    template = template.replace(
        "      function restoreUniverseState() {",
        "      if (initialFocus) { try { window.localStorage.removeItem(storageKey); } catch (e) {} }\n"
        "      function restoreUniverseState() {",
    )
    template = template.replace(
        'svg.addEventListener("click", () => resetUniverse(true));',
        'window.__focusResearchUniverse = function(id, source) { '
        'if (!id || !nodeById.has(id)) return; '
        'if (source === "ai") pulseThenFocus(id); else focusNode(nodeById.get(id)); '
        '};\n'
        '      svg.addEventListener("click", () => resetUniverse(true));',
    )
    template = template.replace(
        'nodes.push({ id:data.center.name, parent:null, group:"Core", level:0, r:56, color:data.center.color,',
        'nodes.push({ id:data.center.name, display:data.center.display_name || data.center.name, parent:null, group:"Core", level:0, r:56, color:data.center.color,',
    )
    template = template.replace(
        'nodes.push({ id:areaName, parent:data.center.name, group:areaName, level:1, r:38, color:area.color,',
        'nodes.push({ id:areaName, display:area.display_name || areaName, groupDisplay:area.display_name || areaName, parent:data.center.name, group:areaName, level:1, r:38, color:area.color,',
    )
    template = template.replace(
        'status:"Research area", regions:area.topics.map(t => t.name).join(" - "), home:p });',
        'status:area.status || data.labels.research_area || "Research area", regions:area.topics.map(t => t.display_name || t.name).join(" - "), home:p });',
    )
    template = template.replace(
        'nodes.push({ id:topic.name, parent:areaName, group:areaName, level:2, r:22, color:area.color,',
        'nodes.push({ id:topic.name, display:topic.display_name || topic.name, groupDisplay:area.display_name || areaName, parent:areaName, group:areaName, level:2, r:22, color:area.color,',
    )
    template = template.replace(
        ': safe(d.group)}</div>',
        ': safe(d.groupDisplay || d.group)}</div>',
    )
    template = template.replace(
        'addWrappedText(g, n.id, n.level === 0 ? 14 : n.level === 1 ? 12 : 10);',
        'addWrappedText(g, n.display || n.id, n.level === 0 ? 14 : n.level === 1 ? 12 : 10);',
    )
    template = template.replace(
        '<h3>${safe(d.id)}</h3><div class="label">Key question</div><p>${safe(d.question)}</p>',
        '<h3>${safe(d.display || d.id)}</h3><div class="label">Key question</div><p>${safe(d.question)}</p>',
    )
    template = template.replace(
        '<h2>Antarctic Research Universe</h2><p>Ask a question; AI locates the matching node. You can also click any sphere manually.</p>',
        f'<h2>{html.escape(translate_text("Antarctic Research Universe"))}</h2><p>{html.escape(translate_text("Ask a question; AI locates the matching node. You can also click any sphere manually."))}</p>',
    )
    template = template.replace(
        'Click a sphere · Ask below · matched module auto-focuses here',
        html.escape(translate_text("Click a sphere · Ask below · matched module auto-focuses here")),
    )
    # The group-display patch above runs first, so match its resulting
    # expression when replacing the graph-level badge labels.
    template = template.replace(
        '${d.level === 0 ? "Core system" : d.level === 1 ? "Research area" : safe(d.groupDisplay || d.group)}',
        '${d.level === 0 ? safe(data.labels.core_system || "Core system") : d.level === 1 ? safe(data.labels.research_area || "Research area") : safe(d.groupDisplay || d.group)}',
    )
    template = template.replace('<div class="label">Key question</div>', '<div class="label">${safe(data.labels.key_question || "KEY QUESTION")}</div>')
    template = template.replace('<div class="label">Why it matters</div>', '<div class="label">${safe(data.labels.why_it_matters || "WHY IT MATTERS")}</div>')
    template = template.replace('<div class="label">Research status</div>', '<div class="label">${safe(data.labels.research_status || "RESEARCH STATUS")}</div>')
    template = template.replace('<div class="label">Key regions / linked topics</div>', '<div class="label">${safe(data.labels.key_regions || "KEY REGIONS / LINKED TOPICS")}</div>')
    body = (
        template.replace("__DATA__", json.dumps(universe_payload(), ensure_ascii=False))
        .replace("__INITIAL_FOCUS__", json.dumps(initial_focus_topic, ensure_ascii=False))
        .replace("__INITIAL_FOCUS_SOURCE__", json.dumps(initial_focus_source, ensure_ascii=False))
        .replace("__INITIAL_FOCUS_TOKEN__", json.dumps(initial_focus_token, ensure_ascii=False))
    )
    return translate_html(
        "<!doctype html><html><head><meta charset='utf-8'></head>"
        "<body style='margin:0;background:#020617;overflow:hidden;'>"
        f"{body}"
        "</body></html>"
    )


DIRECTION_DATA = {
    "Ocean heat pathways": {
        "emoji": "*",
        "system": "Ocean-ice shelf interaction",
        "uncertainty": 92,
        "impact": 94,
        "observability": 58,
        "time_scale": "days -> decades",
        "regions": ["Amundsen Sea", "Bellingshausen Sea", "Totten Glacier", "Filchner-Ronne"],
        "methods": ["Ocean moorings", "AUV", "CTD", "High-resolution ocean models"],
        "core_question": "How does warm Circumpolar Deep Water cross the continental shelf and reach ice-shelf cavities?",
        "why_now": "The paper repeatedly points to warm ocean access as a central control on basal melting, but the exact pathways depend on winds, eddies, tides, bathymetry, and freshwater feedbacks.",
        "gap": "Cross-shelf heat transport is still hard to observe directly and difficult to represent in models at the right spatial scale.",
        "student_angle": "Build a conceptual or data-driven map linking bathymetric troughs, wind forcing, and glacier thinning hotspots.",
        "starter_questions": [
            "Which Antarctic margins are most exposed to warm-water access under changing winds?",
            "Can satellite-observed thinning be connected to likely ocean heat pathways?",
            "How does meltwater-driven stratification change the persistence of warm water beneath ice shelves?",
        ],
    },
    "Grounding-line instability": {
        "emoji": "*",
        "system": "Ice dynamics",
        "uncertainty": 88,
        "impact": 96,
        "observability": 64,
        "time_scale": "years -> centuries",
        "regions": ["Thwaites", "Pine Island", "Wilkes Basin", "Aurora Basin"],
        "methods": ["InSAR", "Satellite altimetry", "Radar sounding", "Ice-sheet models"],
        "core_question": "When does grounding-line retreat become self-sustaining on retrograde bed topography?",
        "why_now": "MISI links bed geometry, ice-shelf buttressing, and ocean forcing; it is one of the highest-impact mechanisms for future sea-level projections.",
        "gap": "The timing and reversibility of retreat depend on subglacial topography, basal friction, ocean melt parameterization, and solid-Earth feedbacks.",
        "student_angle": "Use a case-study comparison between Thwaites, Pine Island, and an East Antarctic basin to explain how bed geometry changes risk.",
        "starter_questions": [
            "Which bed geometries make retreat most sensitive to small melt-rate changes?",
            "How do pinning points delay or reorganize grounding-line retreat?",
            "Can InSAR-derived velocity changes be used as early signs of buttressing loss?",
        ],
    },
    "Ice-shelf fracture and calving": {
        "emoji": "*",
        "system": "Atmosphere-ice shelf coupling",
        "uncertainty": 85,
        "impact": 90,
        "observability": 70,
        "time_scale": "days -> years",
        "regions": ["Antarctic Peninsula", "Larsen B", "Wilkins", "Roi Baudouin"],
        "methods": ["Optical imagery", "SAR", "Surface melt mapping", "Fracture models"],
        "core_question": "How do surface melt, hydrofracturing, and calving change ice-shelf buttressing?",
        "why_now": "Surface hydrology and hydrofracture are crucial for understanding rapid shelf collapse and high-end sea-level risk, but MICI remains debated.",
        "gap": "Models still struggle to predict when fractures connect, when shelves collapse, and how quickly inland glaciers respond.",
        "student_angle": "Create a visual diagnostic framework that classifies ice shelves by meltwater ponding, crevasse density, and buttressing importance.",
        "starter_questions": [
            "Which surface-hydrology patterns indicate increasing hydrofracture vulnerability?",
            "How much passive shelf area can be lost before grounded ice accelerates?",
            "Can Larsen B-like collapse logic be generalized to other Antarctic shelves?",
        ],
    },
    "Subglacial water and basal sliding": {
        "emoji": "*",
        "system": "Subglacial hydrology",
        "uncertainty": 91,
        "impact": 82,
        "observability": 42,
        "time_scale": "hours -> millennia",
        "regions": ["Siple Coast", "Thwaites", "Byrd Glacier", "Subglacial lakes"],
        "methods": ["Radar", "Altimetry lake detection", "Boreholes", "Hydrology models"],
        "core_question": "How does water beneath the ice sheet control basal friction and ice velocity?",
        "why_now": "Basal water can lubricate the bed, drain through lakes and channels, and feed freshwater into ice-shelf cavities.",
        "gap": "The subglacial system is difficult to observe directly, so models often rely on simplified sliding laws and uncertain hydrological parameters.",
        "student_angle": "Compare distributed versus channelized drainage and explain how each could stabilize or destabilize ice flow.",
        "starter_questions": [
            "How do active subglacial lake drainage events change downstream velocity?",
            "What remote-sensing signatures indicate a switch from distributed to channelized flow?",
            "How should basal hydrology be represented in beginner-friendly ice-flow simulations?",
        ],
    },
    "Solid-Earth feedbacks": {
        "emoji": "*",
        "system": "Solid Earth-ice interaction",
        "uncertainty": 87,
        "impact": 84,
        "observability": 50,
        "time_scale": "decades -> millennia",
        "regions": ["West Antarctica", "Amundsen Sea", "Antarctic Peninsula", "East Antarctica"],
        "methods": ["GPS/GNSS", "GRACE correction", "Seismology", "GIA models"],
        "core_question": "Can bedrock uplift and sea-level fingerprints slow or reshape ice-sheet retreat?",
        "why_now": "GIA affects both observed mass-balance estimates and physical retreat feedbacks near grounding lines.",
        "gap": "Antarctic mantle viscosity varies in 3D, but many models still simplify Earth structure or lack enough geodetic constraints.",
        "student_angle": "Explain why the solid Earth is not just a correction term but an active feedback in ice-sheet stability.",
        "starter_questions": [
            "Where is rapid bedrock uplift most likely to slow grounding-line retreat?",
            "How sensitive are GRACE-derived mass trends to different GIA assumptions?",
            "Can regional GPS/GNSS constraints improve ice-sheet projection confidence?",
        ],
    },
    "Paleo constraints for future projections": {
        "emoji": "*",
        "system": "Past-future bridge",
        "uncertainty": 80,
        "impact": 88,
        "observability": 56,
        "time_scale": "centuries -> millions of years",
        "regions": ["Pliocene", "Last Interglacial", "Marine margins", "Ice-core sites"],
        "methods": ["Marine sediment cores", "Ice cores", "Sea-level records", "Model-data comparison"],
        "core_question": "How can past warm periods constrain future Antarctic sea-level contribution?",
        "why_now": "The satellite era is too short to reveal the full AIS response, so paleo records are essential for testing long-term sensitivity.",
        "gap": "Paleo sea-level and ice-extent reconstructions have large uncertainties, making it hard to validate specific model physics.",
        "student_angle": "Build a Past-Present-Future evidence chain showing what each archive can and cannot prove.",
        "starter_questions": [
            "Which past warm intervals are most useful analogs for future Antarctic change?",
            "How can paleo records test whether high-end collapse mechanisms are realistic?",
            "What uncertainty remains when using sea-level records to constrain AIS retreat?",
        ],
    },
    "AI-assisted Antarctic research": {
        "emoji": "*",
        "system": "AI + Earth observation",
        "uncertainty": 74,
        "impact": 78,
        "observability": 86,
        "time_scale": "now -> next decade",
        "regions": ["Remote sensing", "Literature synthesis", "Education", "Model workflows"],
        "methods": ["Knowledge graphs", "RAG", "Computer vision", "Interactive visualization"],
        "core_question": "How can AI help organize observations, literature, and model uncertainty without replacing scientific reasoning?",
        "why_now": "Your Atlas itself is a prototype: it turns a dense review paper into explorable knowledge maps, simulations, and paper-grounded Q&A.",
        "gap": "AI tools must remain source-grounded, uncertainty-aware, and connected to real observation and modeling workflows.",
        "student_angle": "Turn this project into a portfolio piece: an AI research assistant for Antarctic ice-sheet literature and remote-sensing reasoning.",
        "starter_questions": [
            "Can a knowledge graph help students navigate AIS mechanisms more effectively than a linear PDF?",
            "How can RAG systems cite paper passages while generating slide-ready scientific explanations?",
            "Can AI detect conceptual links between satellite observations and physical ice-sheet processes?",
        ],
    },
}


DIRECTION_REGION_COORDS = {
    "Amundsen Sea": (-74.5, -110),
    "Bellingshausen Sea": (-72, -85),
    "Totten Glacier": (-67, 116),
    "Filchner-Ronne": (-78, -55),
    "Thwaites": (-75.5, -106),
    "Pine Island": (-75, -100),
    "Wilkes Basin": (-70, 140),
    "Aurora Basin": (-72, 120),
    "Antarctic Peninsula": (-65, -62),
    "Larsen B": (-65.5, -61),
    "Wilkins": (-70, -73),
    "Roi Baudouin": (-70, 24),
    "Siple Coast": (-82, -150),
    "Byrd Glacier": (-80, 160),
    "Subglacial lakes": (-77, 105),
    "West Antarctica": (-78, -115),
    "East Antarctica": (-78, 80),
    "Marine margins": (-70, 30),
    "Ice-core sites": (-76, 20),
    "Remote sensing": (-75, 0),
    "Literature synthesis": (-74, 40),
    "Education": (-73, 80),
    "Model workflows": (-73, 120),
    "GRACE correction": (-76, -30),
}


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFrameShape(QFrame.NoFrame)


class HeroHeader(Card):
    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self.setObjectName("HeroHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(18)
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        title_label.setWordWrap(True)
        title_label.setMinimumWidth(520)
        layout.addWidget(title_label, 0 if subtitle else 1)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("Subtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label, 1)


class StatCard(Card):
    def __init__(self, label, value, detail="", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(5)
        self.label_widget = QLabel(label)
        self.label_widget.setObjectName("Kicker")
        self.value_widget = QLabel(value)
        self.value_widget.setObjectName("StatValue")
        self.value_widget.setWordWrap(True)
        self.detail_widget = QLabel(detail)
        self.detail_widget.setObjectName("Muted")
        self.detail_widget.setWordWrap(True)
        layout.addWidget(self.label_widget)
        layout.addWidget(self.value_widget)
        layout.addWidget(self.detail_widget)

    def set_value(self, value, detail=None):
        self.value_widget.setText(str(value))
        if detail is not None:
            self.detail_widget.setText(str(detail))



class UniverseBridge(QObject):
    topicSelected = Signal(str)

    @Slot(str)
    def selectTopic(self, topic):
        if topic:
            self.topicSelected.emit(topic)


class OriginalUniverseWebWidget(QWebEngineView):
    topicSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UniverseMap")
        self.setMinimumHeight(720)
        self.setStyleSheet("background:#020617; border-radius:28px;")
        self.page().setBackgroundColor(QColor("#020617"))
        self.focused_topic = ""
        self._focus_token = 0
        self._focus_source = "manual"
        self._did_initial_visible_focus = False
        self._html_loaded = False
        self._bridge = UniverseBridge(self)
        self._bridge.topicSelected.connect(self._on_web_topic_selected)
        self._channel = QWebChannel(self.page())
        self._channel.registerObject("universeBridge", self._bridge)
        self.page().setWebChannel(self._channel)
        self.loadFinished.connect(self._apply_focus_after_load)
        self.setHtml(original_universe_html(self.focused_topic, self._focus_source, self._focus_token))

    def set_focus(self, topic, pulse=False):
        if not topic:
            return
        self.focused_topic = topic
        self._focus_token += 1
        self._focus_source = "ai" if pulse else "manual"
        if not self._html_loaded:
            self.setHtml(original_universe_html(topic, self._focus_source, self._focus_token))
        else:
            self.apply_focus_in_page(topic, source=self._focus_source)
        for delay in (450, 1100, 1900):
            QTimer.singleShot(delay, lambda topic=topic, source=self._focus_source: self.apply_focus_in_page(topic, source=source))
        self.topicSelected.emit(topic)

    def _on_web_topic_selected(self, topic):
        self.focused_topic = topic
        self.topicSelected.emit(topic)
        if topic != "Antarctic Ice Sheet":
            QTimer.singleShot(80, lambda topic=topic: self.apply_focus_in_page(topic, source="manual"))

    def _apply_focus_after_load(self, ok):
        self._html_loaded = bool(ok)
        if not ok or not self.focused_topic:
            return
        for delay in (450, 1100, 1800):
            QTimer.singleShot(delay, lambda: self.apply_focus_in_page(self.focused_topic, source="manual"))

    def apply_focus_in_page(self, topic=None, source="manual"):
        topic = topic or self.focused_topic
        if not topic:
            return
        script = f"window.__focusResearchUniverse && window.__focusResearchUniverse({json.dumps(topic)}, {json.dumps(source)});"
        self.page().runJavaScript(script)

    def showEvent(self, event):
        super().showEvent(event)


SYSTEM_LAYERS = {
    "Satellite Altimetry": {
        "short": "Altimetry",
        "measures": "Surface elevation change",
        "observed": "Surface lowering and dynamic thinning near the glacier trunk and grounding zone.",
        "visual": "Laser/radar tracks scan across the glacier while a blue-to-red thinning layer appears.",
        "interpretation": "Lower surface elevation is consistent with ice-shelf thinning and faster discharge.",
    },
    "InSAR Velocity": {
        "short": "InSAR",
        "measures": "Ice velocity and deformation",
        "observed": "Fast flow and acceleration toward the floating ice shelf.",
        "visual": "Orange velocity vectors appear over the glacier trunk and lengthen downstream.",
        "interpretation": "Velocity patterns reveal where ice discharge is concentrated.",
    },
    "GRACE / GRACE-FO": {
        "short": "GRACE",
        "measures": "Regional mass change from gravity",
        "observed": "Large-scale negative mass balance in West Antarctica.",
        "visual": "A broad red gravity-anomaly field covers the regional basin.",
        "interpretation": "Mass loss contributes to sea-level rise, but needs GIA correction.",
    },
    "GPS / GNSS": {
        "short": "GNSS",
        "measures": "Point motion and bedrock response",
        "observed": "Sparse stations track crustal motion and local displacement.",
        "visual": "Station markers pulse with small uplift vectors.",
        "interpretation": "GNSS helps separate ice-mass change from solid-Earth motion.",
    },
    "Ice-penetrating Radar": {
        "short": "Radar",
        "measures": "Ice thickness, bed topography, internal layers",
        "observed": "Bed geometry and possible retrograde slopes beneath the glacier system.",
        "visual": "Radar flight lines and a glowing subglacial cross-section appear.",
        "interpretation": "Bed topography determines whether retreat can become self-sustaining.",
    },
    "Ice / Marine Sediment Cores": {
        "short": "Cores",
        "measures": "Past climate and retreat history",
        "observed": "Marine records reconstruct previous grounding-line positions.",
        "visual": "Core sites appear offshore, connected to a layered archive.",
        "interpretation": "Past retreat constrains model scenarios for future instability.",
    },
}


SYSTEM_CASES = {
    "Thwaites Glacier": {
        "region": "West Antarctica / Amundsen Sea Sector",
        "type": "Fast outlet glacier",
        "main_theme": "Ocean-driven thinning, grounding-line retreat, and MISI-like vulnerability",
        "location_label": "Amundsen Sea Sector",
        "coords": "~75S, 106W",
        "base_note": "Thwaites is often discussed as one of the most vulnerable WAIS glaciers because warm ocean water can thin its ice shelf and reduce buttressing.",
        "tools": {
            "Satellite Altimetry": {
                "observed": "Surface lowering and dynamic thinning near the glacier trunk and grounding zone.",
                "result": "The satellite-era record indicates strong thinning in the Amundsen Sea sector.",
                "interpretation": "Lower surface elevation is consistent with ice-shelf thinning and faster discharge of grounded ice.",
                "visual": "Laser/radar tracks scan across the glacier while a blue-to-red thinning layer appears over the trunk.",
                "process": "Elevation loss -> thinner ice shelf -> weaker buttressing -> faster flow",
            },
            "InSAR Velocity": {
                "observed": "Fast flow and acceleration toward the floating ice shelf.",
                "result": "Velocity patterns reveal where ice discharge is concentrated and where flow responds to buttressing loss.",
                "interpretation": "Faster flow suggests reduced resistance near the grounding line and shelf front.",
                "visual": "Orange velocity vectors appear over the glacier trunk and lengthen downstream.",
                "process": "Phase difference -> displacement -> velocity field -> ice discharge",
            },
            "GRACE / GRACE-FO": {
                "observed": "Large-scale negative mass balance in West Antarctica.",
                "result": "GRACE-like observations connect glacier change to regional mass loss.",
                "interpretation": "Mass loss contributes to global mean sea-level rise, but requires GIA correction.",
                "visual": "A broad red gravity-anomaly style field covers the regional basin.",
                "process": "Gravity change -> mass balance -> sea-level contribution",
            },
            "GPS / GNSS": {
                "observed": "Sparse station-style points track crustal motion and local displacement.",
                "result": "GNSS helps separate ice-mass change from solid-Earth motion.",
                "interpretation": "This is important for constraining GIA and interpreting gravity-based mass estimates.",
                "visual": "Station markers pulse, with small vectors showing motion/uplift.",
                "process": "Station position -> crustal motion -> GIA correction",
            },
            "Ice-penetrating Radar": {
                "observed": "Bed geometry and possible retrograde slopes beneath the glacier system.",
                "result": "Radar-style profiles reveal the hidden boundary conditions controlling retreat.",
                "interpretation": "Bed topography determines whether retreat can become self-sustaining.",
                "visual": "Radar flight lines and a glowing subglacial cross-section appear beneath the ice.",
                "process": "Radar echo -> bed map -> instability assessment",
            },
            "Ice / Marine Sediment Cores": {
                "observed": "Marine records help reconstruct previous grounding-line positions and retreat episodes.",
                "result": "Paleo evidence extends interpretation beyond the short satellite era.",
                "interpretation": "Past retreat provides context for how the system may respond to future forcing.",
                "visual": "Core sites appear offshore, connected to a time-depth archive strip.",
                "process": "Core record -> past retreat -> future sensitivity constraint",
            },
        },
    },
    "Pine Island Glacier": {
        "region": "West Antarctica / Amundsen Sea Sector",
        "type": "Fast outlet glacier",
        "main_theme": "CDW intrusion, ice-shelf thinning, grounding-line retreat",
        "location_label": "Pine Island Bay",
        "coords": "~75S, 100W",
        "base_note": "Pine Island Glacier is a classic example of rapid retreat linked to warm Circumpolar Deep Water reaching the ice-shelf cavity.",
        "tools": {
            "Satellite Altimetry": {
                "observed": "Strong thinning along the glacier and ice shelf.",
                "result": "Altimetry-style evidence shows where surface lowering is concentrated.",
                "interpretation": "Surface lowering reflects dynamic thinning and enhanced basal melting.",
                "visual": "Repeated satellite tracks reveal a thinning corridor near the grounding zone.",
                "process": "Repeated elevation profiles -> thinning map -> dynamic response",
            },
            "InSAR Velocity": {
                "observed": "Fast outlet flow toward Pine Island Bay.",
                "result": "Velocity vectors show the main discharge pathway.",
                "interpretation": "Acceleration is consistent with reduced ice-shelf buttressing.",
                "visual": "Dense downstream arrows highlight the fast-flowing trunk.",
                "process": "SAR phase -> velocity -> ice discharge",
            },
            "GRACE / GRACE-FO": {
                "observed": "Part of the broader Amundsen Sea mass-loss signal.",
                "result": "Gravity change captures integrated regional loss rather than local glacier detail.",
                "interpretation": "Useful for linking local dynamic change to total mass loss.",
                "visual": "A basin-scale mass-loss halo overlays the map.",
                "process": "Gravity anomaly -> regional mass trend -> sea-level signal",
            },
            "GPS / GNSS": {
                "observed": "Point observations can help constrain solid-Earth response.",
                "result": "GNSS is precise but spatially sparse.",
                "interpretation": "Important for separating ice signals from bedrock uplift.",
                "visual": "Station points blink at the margin with uplift arrows.",
                "process": "Position time series -> uplift rate -> correction",
            },
            "Ice-penetrating Radar": {
                "observed": "Troughs and bed features that route ocean heat toward the grounding line.",
                "result": "Radar and bathymetry reveal pathways for warm water access.",
                "interpretation": "Geometry helps explain why Pine Island is sensitive to ocean forcing.",
                "visual": "Subglacial troughs glow beneath the ice image.",
                "process": "Bed sounding -> trough geometry -> ocean access pathway",
            },
            "Ice / Marine Sediment Cores": {
                "observed": "Marine archives record earlier ice-margin behavior in Pine Island Trough.",
                "result": "Sediment evidence helps test whether retreat was rapid or episodic.",
                "interpretation": "Past retreat constrains model scenarios for future instability.",
                "visual": "Offshore core dots and a layered sediment strip appear.",
                "process": "Sediment layers -> retreat history -> model constraint",
            },
        },
    },
    "Totten Glacier": {
        "region": "East Antarctica / Sabrina Coast",
        "type": "East Antarctic outlet glacier",
        "main_theme": "Warm water access to a marine-based EAIS sector",
        "location_label": "Sabrina Coast",
        "coords": "~67S, 116E",
        "base_note": "Totten Glacier shows that parts of East Antarctica can also be sensitive to ocean heat and marine-based bed geometry.",
        "tools": {
            "Satellite Altimetry": {
                "observed": "Surface lowering in a vulnerable East Antarctic outlet system.",
                "result": "Altimetry helps detect whether EAIS outlet glaciers are thinning or thickening.",
                "interpretation": "Thinning suggests ocean forcing can affect parts of East Antarctica too.",
                "visual": "Satellite tracks cross an East Antarctic outlet with localized thinning colors.",
                "process": "Elevation change -> outlet thinning -> EAIS vulnerability",
            },
            "InSAR Velocity": {
                "observed": "Fast flow through the Totten outlet toward the coast.",
                "result": "InSAR-style velocity mapping identifies dynamic outlet behavior.",
                "interpretation": "Flow pattern links inland catchment ice to coastal forcing.",
                "visual": "Flow arrows converge toward the outlet glacier trunk.",
                "process": "Velocity field -> discharge pathway -> dynamic thinning",
            },
            "GRACE / GRACE-FO": {
                "observed": "EAIS mass change is harder to isolate because signals are broad and uncertain.",
                "result": "GRACE provides continent-scale mass context but local attribution is limited.",
                "interpretation": "Needs careful regional interpretation and GIA correction.",
                "visual": "A broad, softer mass-balance field overlays the East Antarctic sector.",
                "process": "Gravity trend -> regional mass estimate -> uncertainty",
            },
            "GPS / GNSS": {
                "observed": "Sparse geodetic constraints for East Antarctic solid-Earth response.",
                "result": "GNSS helps improve corrections to mass-balance estimates.",
                "interpretation": "Especially important where mass-change signals are subtle.",
                "visual": "Few station markers emphasize sparse but precise measurements.",
                "process": "GNSS station -> uplift correction -> better mass estimate",
            },
            "Ice-penetrating Radar": {
                "observed": "Marine-based geometry and bed pathways beneath the outlet system.",
                "result": "Radar is central for identifying hidden EAIS vulnerabilities.",
                "interpretation": "Bed shape controls whether ocean-driven retreat can propagate inland.",
                "visual": "A deep basin cross-section appears below the satellite-style surface.",
                "process": "Radar profile -> marine basin -> retreat sensitivity",
            },
            "Ice / Marine Sediment Cores": {
                "observed": "Marine sediment records can indicate past margin retreat and ocean warmth.",
                "result": "Paleo data helps evaluate long-term East Antarctic sensitivity.",
                "interpretation": "Useful because satellite records are too short for millennial-scale behavior.",
                "visual": "Core archive marks appear along the continental shelf.",
                "process": "Paleo archive -> warm-period behavior -> future analog",
            },
        },
    },
    "Larsen B Ice Shelf": {
        "region": "Antarctic Peninsula",
        "type": "Collapsed ice shelf",
        "main_theme": "Surface meltwater, hydrofracturing, and buttressing loss",
        "location_label": "Antarctic Peninsula",
        "coords": "~65S, 61W",
        "base_note": "Larsen B is a famous example of ice-shelf collapse followed by acceleration of tributary glaciers after buttressing was lost.",
        "tools": {
            "Satellite Altimetry": {
                "observed": "Elevation and surface morphology changed dramatically after shelf breakup.",
                "result": "Altimetry-like monitoring helps quantify post-collapse glacier thinning.",
                "interpretation": "After shelf loss, tributary glaciers can accelerate and thin.",
                "visual": "Before/after scan lines reveal lowered tributary glacier surfaces.",
                "process": "Ice-shelf loss -> tributary thinning -> reduced stability",
            },
            "InSAR Velocity": {
                "observed": "Glaciers feeding the former shelf accelerated after collapse.",
                "result": "Velocity mapping directly shows the dynamic impact of buttressing loss.",
                "interpretation": "This is a clear example of why floating shelves matter for grounded ice.",
                "visual": "Arrows behind the former shelf become longer and brighter.",
                "process": "Shelf collapse -> lower back stress -> faster tributary flow",
            },
            "GRACE / GRACE-FO": {
                "observed": "Regional signal is smaller and harder to isolate than WAIS basin-scale loss.",
                "result": "GRACE gives context but is not the primary local diagnostic here.",
                "interpretation": "Better used with altimetry and velocity for this case.",
                "visual": "A faint regional mass-change layer appears over the Peninsula.",
                "process": "Regional gravity -> mass context -> multi-sensor interpretation",
            },
            "GPS / GNSS": {
                "observed": "Point measurements can support local deformation and uplift context.",
                "result": "GNSS is useful but sparse relative to satellite imagery.",
                "interpretation": "Best interpreted together with optical/SAR records.",
                "visual": "A few station vectors appear along the Peninsula.",
                "process": "Station motion -> local deformation -> context",
            },
            "Ice-penetrating Radar": {
                "observed": "Internal structure and thickness help explain shelf weakness and tributary response.",
                "result": "Radar can support understanding of mechanical vulnerability.",
                "interpretation": "Geometry and crevasse structure affect collapse potential.",
                "visual": "Crack-like internal layers and radar profiles appear across the shelf.",
                "process": "Internal structure -> fracture vulnerability -> collapse risk",
            },
            "Ice / Marine Sediment Cores": {
                "observed": "Records can help determine whether collapse was unusual in recent millennia.",
                "result": "Paleo context tells whether modern breakup exceeds natural variability.",
                "interpretation": "Important for connecting recent atmospheric warming to shelf stability.",
                "visual": "Core archive appears near the shelf front and former embayment.",
                "process": "Archive record -> shelf history -> modern anomaly",
            },
        },
    },
    "Wilkes Subglacial Basin": {
        "region": "East Antarctica",
        "type": "Marine-based subglacial basin",
        "main_theme": "Bed topography, marine-based ice, long-term sensitivity",
        "location_label": "Wilkes Land",
        "coords": "~70S, 140E",
        "base_note": "Wilkes Subglacial Basin is important because marine-based East Antarctic ice could be vulnerable if warming and bed geometry allow retreat to propagate inland.",
        "tools": {
            "Satellite Altimetry": {
                "observed": "Surface elevation provides a first view of present-day change over a large basin.",
                "result": "Altimetry helps detect whether the basin is stable, thinning, or thickening.",
                "interpretation": "Present changes must be interpreted against snowfall and firn processes.",
                "visual": "Wide satellite tracks sweep across the basin surface.",
                "process": "Elevation trend -> basin-scale change -> mass-balance clue",
            },
            "InSAR Velocity": {
                "observed": "Velocity fields show where ice can drain from the basin toward the coast.",
                "result": "InSAR identifies fast-flow corridors and outlet controls.",
                "interpretation": "Flow pathways connect interior basin geometry to coastal vulnerability.",
                "visual": "Flow arrows trace drainage from the basin toward the margin.",
                "process": "Velocity map -> drainage structure -> discharge risk",
            },
            "GRACE / GRACE-FO": {
                "observed": "Broad gravity signals help monitor basin-scale mass balance.",
                "result": "Spatial resolution is coarse, so interpretation is regional.",
                "interpretation": "GIA correction is essential in East Antarctica.",
                "visual": "A broad mass-balance wash appears across Wilkes Land.",
                "process": "Gravity field -> basin mass trend -> GIA-sensitive estimate",
            },
            "GPS / GNSS": {
                "observed": "Sparse but valuable constraints on vertical bedrock motion.",
                "result": "GNSS improves the correction needed for gravity-derived ice mass.",
                "interpretation": "Important for reducing uncertainty in East Antarctic mass balance.",
                "visual": "Uplift vectors appear as fixed station points over the basin margin.",
                "process": "Uplift rate -> GIA model -> corrected ice mass",
            },
            "Ice-penetrating Radar": {
                "observed": "Deep subglacial basin and retrograde-bed style geometry.",
                "result": "Radar is the most visually important tool for this case because the key feature is hidden beneath ice.",
                "interpretation": "Bed topography controls long-term marine ice-sheet sensitivity.",
                "visual": "A large glowing subglacial basin appears beneath the ice surface.",
                "process": "Bed echo -> basin geometry -> marine instability potential",
            },
            "Ice / Marine Sediment Cores": {
                "observed": "Paleo records test whether marine-based EAIS sectors retreated in past warm climates.",
                "result": "Core evidence helps constrain long-term sensitivity that satellites cannot capture.",
                "interpretation": "Useful for Pliocene and interglacial analogs.",
                "visual": "Archive markers connect the basin to past warm-period evidence.",
                "process": "Past margin record -> warm-climate response -> future constraint",
            },
        },
    },
}


def system_case(name):
    return SYSTEM_CASES.get(name, SYSTEM_CASES["Thwaites Glacier"])


def system_tool(case_name, layer_name):
    case = system_case(case_name)
    base = dict(SYSTEM_LAYERS.get(layer_name, SYSTEM_LAYERS["Satellite Altimetry"]))
    base.update(case.get("tools", {}).get(layer_name, {}))
    return base


SYSTEM_PROCESSES = {
    "Ocean Forcing": "Warm Circumpolar Deep Water can reach the continental shelf and increase basal melting below ice shelves.",
    "Ice Shelf Buttressing": "Floating ice shelves slow inland ice flow by providing back stress; thinning or collapse reduces this support.",
    "Grounding Line Retreat": "The grounding line marks the transition from grounded ice to floating ice; retreat can increase ice discharge.",
    "MISI": "Marine Ice Sheet Instability can occur when retreat on a retrograde bed exposes thicker ice and causes further retreat.",
    "MICI": "Marine Ice Cliff Instability is a proposed rapid-collapse mechanism involving hydrofracturing and cliff failure.",
    "Basal Hydrology": "Subglacial water can reduce basal resistance and affect ice flow speed.",
    "Solid Earth Feedback": "Bedrock uplift and sea-level fingerprints can either amplify or slow ice-sheet retreat.",
}


class SensorSceneWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(520)
        self.case_name = "Thwaites Glacier"
        self.layer_name = "Satellite Altimetry"
        self.visible_layers = ["Satellite Altimetry"]
        self.motion_phase = 0.0
        self.motion_timer = QTimer(self)
        self.motion_timer.setTimerType(Qt.PreciseTimer)
        self.motion_timer.setInterval(SLOW_ANIMATION_INTERVAL_MS)
        self.motion_timer.timeout.connect(self._advance_motion)
        self.motion_timer.start()

    def _advance_motion(self):
        if not self.isVisible():
            self.motion_timer.stop()
            return
        self.motion_phase = (self.motion_phase + 0.008) % 1.0
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.motion_timer.isActive():
            self.motion_timer.start()

    def hideEvent(self, event):
        self.motion_timer.stop()
        super().hideEvent(event)

    def set_case(self, name):
        self.case_name = name
        self.update()

    def set_layer(self, name):
        self.layer_name = name
        self.visible_layers = [name]
        self.update()

    def set_layers(self, names):
        layers = [name for name in names if name in SYSTEM_LAYERS]
        if not layers:
            layers = ["Satellite Altimetry"]
        self.visible_layers = layers
        self.layer_name = layers[-1]
        self.update()

    def _draw_case_signature(self, painter, inner):
        case_name = self.case_name
        if case_name == "Larsen B Ice Shelf":
            painter.setPen(QPen(QColor(255, 70, 90, 190), 4))
            for x_frac in [0.34, 0.46, 0.58, 0.70]:
                x = inner.left() + inner.width() * x_frac
                painter.drawLine(QPointF(x, inner.top() + 86), QPointF(x + 28, inner.bottom() - 74))
            painter.setBrush(QColor(45, 165, 245, 180))
            painter.setPen(QPen(QColor(180, 235, 255, 130), 2))
            for x_frac, y_frac in [(0.42, 0.30), (0.54, 0.38), (0.63, 0.28), (0.74, 0.43)]:
                painter.drawEllipse(QPointF(inner.left() + inner.width() * x_frac, inner.top() + inner.height() * y_frac), 20, 8)
        elif case_name == "Wilkes Subglacial Basin":
            basin = QRadialGradient(QPointF(inner.left() + inner.width() * 0.52, inner.top() + inner.height() * 0.60), 220)
            basin.setColorAt(0, QColor(40, 92, 190, 95))
            basin.setColorAt(0.72, QColor(20, 62, 132, 42))
            basin.setColorAt(1, QColor(20, 62, 132, 0))
            painter.fillRect(inner, basin)
            painter.setPen(QPen(QColor(255, 214, 82, 210), 4))
            painter.drawArc(QRectF(inner.left() + 165, inner.bottom() - 140, 430, 155), 0, -180 * 16)
        elif case_name == "Totten Glacier":
            painter.setPen(QPen(QColor(65, 210, 255, 145), 5, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(inner.left() + 110, inner.bottom() - 90), QPointF(inner.left() + 370, inner.top() + 120))
            painter.drawLine(QPointF(inner.left() + 180, inner.bottom() - 76), QPointF(inner.left() + 470, inner.top() + 140))
            painter.setBrush(QColor(78, 163, 241, 72))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(inner.left() + inner.width() * 0.62, inner.top() + inner.height() * 0.38), 86, 40)
        elif case_name == "Pine Island Glacier":
            painter.setPen(QPen(QColor(78, 163, 241, 150), 5, Qt.SolidLine, Qt.RoundCap))
            for offset in [0, 34, 68]:
                painter.drawLine(QPointF(inner.left() + 110, inner.top() + 120 + offset), QPointF(inner.left() + 450, inner.top() + 188 + offset * 0.35))
            heat = QRadialGradient(QPointF(inner.left() + inner.width() * 0.58, inner.top() + inner.height() * 0.50), 120)
            heat.setColorAt(0, QColor(255, 130, 75, 90))
            heat.setColorAt(1, QColor(255, 130, 75, 0))
            painter.fillRect(inner, heat)
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 100), 3, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(inner.left() + 145, inner.top() + 98), QPointF(inner.left() + 430, inner.bottom() - 92))
            painter.setPen(QPen(QColor(78, 163, 241, 150), 4, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(inner.left() + 210, inner.bottom() - 116), QPointF(inner.left() + 520, inner.bottom() - 48))

    def _draw_sensor_layer(self, painter, inner, layer_name):
        phase = self.motion_phase
        if layer_name == "Satellite Altimetry":
            painter.setPen(QPen(QColor(145, 231, 255, 180), 2))
            for x_frac in [0.28, 0.46, 0.62]:
                x = inner.left() + inner.width() * x_frac
                painter.drawLine(QPointF(x, inner.top() + 8), QPointF(x, inner.bottom() - 8))
            heat = QRadialGradient(QPointF(inner.left() + inner.width() * 0.54, inner.top() + inner.height() * 0.56), 105)
            heat.setColorAt(0, QColor(255, 92, 64, 130 + int(35 * (0.5 + 0.5 * sin(phase * 2 * pi)))))
            heat.setColorAt(0.55, QColor(255, 193, 84, 90))
            heat.setColorAt(1, QColor(255, 193, 84, 0))
            painter.fillRect(inner, heat)
            scan_y = inner.top() + 16 + (inner.height() - 32) * phase
            painter.setPen(QPen(QColor(185, 244, 255, 140), 3, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(inner.left() + 42, scan_y), QPointF(inner.right() - 42, scan_y - 20))
        elif layer_name == "InSAR Velocity":
            painter.setPen(QPen(QColor(255, 149, 45, 205 + int(35 * (0.5 + 0.5 * sin(phase * 2 * pi)))), 4))
            for y_frac, length in [(0.42, 130), (0.50, 170), (0.58, 200), (0.66, 150)]:
                y = inner.top() + inner.height() * y_frac
                x = inner.left() + 145
                moving_length = length + 16 * sin(phase * 2 * pi + y_frac * 8)
                painter.drawLine(QPointF(x, y), QPointF(x + moving_length, y + 18))
                painter.drawLine(QPointF(x + moving_length, y + 18), QPointF(x + moving_length - 16, y + 8))
                painter.drawLine(QPointF(x + moving_length, y + 18), QPointF(x + moving_length - 18, y + 29))
        elif layer_name == "GRACE / GRACE-FO":
            mass = QRadialGradient(QPointF(inner.left() + inner.width() * 0.48, inner.top() + inner.height() * 0.50), 190)
            mass.setColorAt(0, QColor(255, 75, 70, 105 + int(42 * (0.5 + 0.5 * sin(phase * 2 * pi)))))
            mass.setColorAt(0.55, QColor(255, 132, 60, 65))
            mass.setColorAt(1, QColor(30, 100, 230, 0))
            painter.fillRect(inner, mass)
        elif layer_name == "GPS / GNSS":
            painter.setPen(QPen(QColor("#f8fbff"), 2))
            painter.setBrush(QColor("#73f0a2"))
            for index, (x_frac, y_frac) in enumerate([(0.34, 0.44), (0.50, 0.62), (0.66, 0.38), (0.26, 0.70)]):
                p = QPointF(inner.left() + inner.width() * x_frac, inner.top() + inner.height() * y_frac)
                radius = 7 + 4 * (0.5 + 0.5 * sin(phase * 2 * pi + index))
                painter.drawEllipse(p, radius, radius)
                painter.drawText(QRectF(p.x() + 12, p.y() - 20, 32, 22), "->")
        elif layer_name == "Ice-penetrating Radar":
            for index, y_frac in enumerate([0.36, 0.52, 0.67]):
                painter.setPen(QPen(QColor(255, 255, 255, 150 + int(70 * (0.5 + 0.5 * sin(phase * 2 * pi + index)))), 3))
                y = inner.top() + inner.height() * y_frac
                painter.drawLine(QPointF(inner.left() + 120, y), QPointF(inner.left() + 480, y - 70))
            painter.setPen(QPen(QColor(255, 214, 82, 230), 4))
            painter.drawArc(QRectF(inner.left() + 210, inner.bottom() - 92, 330, 112), 0, -180 * 16)
        elif layer_name == "Ice / Marine Sediment Cores":
            painter.setPen(QPen(QColor("#f8fbff"), 2))
            painter.setBrush(QColor("#F6C85F"))
            for index, (x_frac, y_frac) in enumerate([(0.70, 0.68), (0.77, 0.55), (0.62, 0.76)]):
                radius = 8 + 2 * (0.5 + 0.5 * sin(phase * 2 * pi + index))
                painter.drawEllipse(QPointF(inner.left() + inner.width() * x_frac, inner.top() + inner.height() * y_frac), radius, radius)
            archive = QRectF(inner.right() - 108, inner.top() + 74, 72, 220)
            painter.setBrush(QColor(230, 242, 248, 210))
            painter.drawRoundedRect(archive, 12, 12)
            painter.setPen(QPen(QColor(80, 120, 145, 150), 3))
            for y in range(int(archive.top()) + 18, int(archive.bottom()) - 8, 22):
                painter.drawLine(QPointF(archive.left() + 8, y), QPointF(archive.right() - 8, y))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        case = system_case(self.case_name)
        rect = QRectF(self.rect()).adjusted(0, 0, -1, -1)
        bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bg.setColorAt(0, QColor("#10253f"))
        bg.setColorAt(0.56, QColor("#07111f"))
        bg.setColorAt(1, QColor("#080b1a"))
        painter.setPen(QPen(QColor(210, 238, 255, 55), 1.2))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 26, 26)

        title = QRectF(24, 22, rect.width() * 0.66, 50)
        painter.setBrush(QColor(9, 21, 39, 170))
        painter.drawRoundedRect(title, 18, 18)
        painter.setPen(QColor("#f8fbff"))
        painter.setFont(ui_font(15, QFont.Bold))
        painter.drawText(QRectF(title.left() + 16, title.top() + 8, 300, 30), "Multi-Sensor Evidence Explorer")
        painter.setPen(QColor(221, 240, 252, 180))
        painter.setFont(ui_font(7))
        painter.drawText(QRectF(title.left() + 326, title.top() + 10, title.width() - 344, 34), Qt.TextWordWrap, "Case study as the base satellite scene; each observation tool adds a different evidence layer on top.")

        scene = QRectF(24, 82, rect.width() * 0.66, rect.height() - 106)
        painter.setPen(QPen(QColor(210, 238, 255, 50), 1))
        painter.setBrush(QColor(5, 16, 30, 205))
        painter.drawRoundedRect(scene, 20, 20)

        sat = QLinearGradient(scene.topLeft(), scene.bottomRight())
        sat.setColorAt(0, QColor("#17334a"))
        sat.setColorAt(0.45, QColor("#cfeefa"))
        sat.setColorAt(0.72, QColor("#07546e"))
        sat.setColorAt(1, QColor("#061829"))
        painter.setBrush(sat)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(scene.adjusted(16, 18, -16, -18), 18, 18)

        inner = scene.adjusted(16, 18, -16, -18)
        painter.save()
        inner_clip = QPainterPath()
        inner_clip.addRoundedRect(inner, 18, 18)
        painter.setClipPath(inner_clip)
        painter.setPen(QPen(QColor(170, 220, 240, 28), 1))
        for i in range(12):
            x = inner.left() + i * inner.width() / 11
            painter.drawLine(QPointF(x, inner.top()), QPointF(x - 110, inner.bottom()))
        for i in range(9):
            y = inner.top() + i * inner.height() / 8
            painter.drawLine(QPointF(inner.left(), y), QPointF(inner.right(), y - 52))

        ice_path = QPainterPath()
        ice_path.moveTo(inner.left() + 70, inner.bottom() - 80)
        ice_path.cubicTo(inner.left() + 120, inner.top() + 70, inner.left() + 360, inner.top() + 34, inner.left() + 450, inner.bottom() - 92)
        ice_path.cubicTo(inner.left() + 355, inner.bottom() - 20, inner.left() + 205, inner.bottom() - 14, inner.left() + 70, inner.bottom() - 80)
        painter.setPen(QPen(QColor(245, 252, 255, 92), 2))
        painter.setBrush(QColor(220, 246, 255, 62))
        painter.drawPath(ice_path)
        self._draw_case_signature(painter, inner)

        visible_layers = [name for name in self.visible_layers if name in SYSTEM_LAYERS]
        if not visible_layers:
            visible_layers = [self.layer_name]
        for visible_layer in visible_layers:
            self._draw_sensor_layer(painter, inner, visible_layer)
        painter.restore()
        layer = system_tool(self.case_name, self.layer_name)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(2, 6, 23, 160))
        painter.drawRoundedRect(QRectF(inner.left() + 34, inner.top() + 40, 330, 34), 17, 17)
        painter.drawRoundedRect(QRectF(inner.left() + 34, inner.bottom() - 82, 344, 34), 17, 17)
        painter.drawRoundedRect(QRectF(inner.right() - 214, inner.bottom() - 42, 190, 34), 17, 17)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(ui_font(8, QFont.Bold))
        painter.drawText(QRectF(inner.left() + 48, inner.top() + 48, 304, 20), f"Location: {case['location_label']} - {case['coords']}")
        painter.drawText(QRectF(inner.left() + 48, inner.bottom() - 74, 320, 20), f"Primary layer: {layer['short']} - {layer['measures']}")
        painter.drawText(QRectF(inner.right() - 198, inner.bottom() - 34, 170, 20), "Ocean cavity / shelf sea")

        side = QRectF(scene.right() + 18, scene.top(), rect.right() - scene.right() - 42, scene.height())
        side_bg = QLinearGradient(side.topLeft(), side.bottomRight())
        side_bg.setColorAt(0, QColor(20, 38, 66, 225))
        side_bg.setColorAt(1, QColor(7, 15, 29, 205))
        painter.setPen(QPen(QColor(210, 238, 255, 70), 1.2))
        painter.setBrush(side_bg)
        painter.drawRoundedRect(side, 22, 22)
        painter.setBrush(QColor(78, 163, 241, 44))
        painter.drawRoundedRect(QRectF(side.left() + 20, side.top() + 18, 145, 30), 15, 15)
        painter.setPen(QColor("#d8f2ff"))
        painter.setFont(ui_font(8, QFont.Bold))
        painter.drawText(QRectF(side.left() + 28, side.top() + 25, 130, 18), f"{layer['short']} layer")
        painter.setPen(QColor("#f8fbff"))
        painter.setFont(ui_font(17, QFont.Bold))
        painter.drawText(QRectF(side.left() + 20, side.top() + 64, side.width() - 40, 34), Qt.TextWordWrap, self.case_name)
        painter.setFont(ui_font(8))
        painter.setPen(QColor(235, 248, 255, 198))
        painter.drawText(
            QRectF(side.left() + 20, side.top() + 104, side.width() - 40, 72),
            Qt.TextWordWrap,
            f"Region: {case['region']}\nType: {case['type']}\nMain theme: {case['main_theme']}",
        )

        detail_rows = [
            ("OBSERVATION", layer["observed"]),
            ("RESULT", layer["result"]),
            ("MEASUREMENT", layer["measures"]),
            ("VISUAL LAYER", layer["visual"]),
            ("PROCESS CHAIN", layer["process"]),
        ]
        available_top = side.top() + 190
        available_bottom = side.bottom() - 14
        gap = 8
        box_height = (available_bottom - available_top - gap * (len(detail_rows) - 1)) / len(detail_rows)
        if box_height < 48:
            detail_rows = detail_rows[:4]
            box_height = (available_bottom - available_top - gap * (len(detail_rows) - 1)) / len(detail_rows)
        box_height = max(42, min(56, box_height))
        y = available_top
        for label, text in detail_rows:
            box = QRectF(side.left() + 20, y, side.width() - 40, box_height)
            painter.setPen(QPen(QColor(210, 238, 255, 46), 1))
            painter.setBrush(QColor(255, 255, 255, 16))
            painter.drawRoundedRect(box, 15, 15)
            painter.setPen(QColor("#9ed8f5"))
            painter.setFont(ui_font(7, QFont.Bold))
            painter.drawText(QRectF(box.left() + 12, box.top() + 7, box.width() - 24, 14), label)
            painter.setPen(QColor(245, 250, 255, 220))
            painter.setFont(ui_font(7))
            painter.drawText(QRectF(box.left() + 12, box.top() + 22, box.width() - 24, box.height() - 26), Qt.TextWordWrap, text)
            y += box_height + gap


class StoryEngineWidget(QWidget):
    stateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(520)
        self.story = "Ice Sheet Stability"
        self.lens = "Past"
        self.step = -1
        self.play_rect = QRectF()
        self.reset_rect = QRectF()
        self.node_hitboxes = []
        self.play_timer = QTimer(self)
        self.play_timer.setInterval(1150)
        self.play_timer.timeout.connect(self._advance_playback)
        self.ambient_phase = 0.0
        self.ambient_timer = QTimer(self)
        self.ambient_timer.setTimerType(Qt.PreciseTimer)
        self.ambient_timer.setInterval(SLOW_ANIMATION_INTERVAL_MS)
        self.ambient_timer.timeout.connect(self._advance_ambient_motion)
        self.ambient_timer.start()

    def _advance_ambient_motion(self):
        if not self.isVisible():
            self.ambient_timer.stop()
            return
        self.ambient_phase = (self.ambient_phase + 0.007) % 1.0
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.ambient_timer.isActive():
            self.ambient_timer.start()

    def hideEvent(self, event):
        self.ambient_timer.stop()
        self.play_timer.stop()
        super().hideEvent(event)

    def set_story(self, story):
        self.play_timer.stop()
        self.story = story
        self.step = -1
        self.update()
        self.stateChanged.emit()

    def set_lens(self, lens):
        self.play_timer.stop()
        self.lens = lens
        self.step = -1
        self.update()
        self.stateChanged.emit()

    def advance_story(self):
        _, nodes = self._story_nodes()
        if not nodes:
            return
        self.step = 0 if self.step >= len(nodes) - 1 else self.step + 1
        self.update()
        self.stateChanged.emit()

    def play_story(self):
        _, nodes = self._story_nodes()
        if not nodes:
            return
        self.step = 0
        self.update()
        self.stateChanged.emit()
        if len(nodes) > 1:
            self.play_timer.start()

    def _advance_playback(self):
        _, nodes = self._story_nodes()
        if not nodes:
            self.play_timer.stop()
            return
        if self.step >= len(nodes) - 1:
            self.play_timer.stop()
            self.update()
            self.stateChanged.emit()
            return
        self.step += 1
        if self.step >= len(nodes) - 1:
            self.play_timer.stop()
        self.update()
        self.stateChanged.emit()

    def reset_story(self):
        self.play_timer.stop()
        self.step = -1
        self.update()
        self.stateChanged.emit()

    def set_story_step(self, index):
        self.play_timer.stop()
        _, nodes = self._story_nodes()
        if not nodes:
            return
        self.step = max(0, min(index, len(nodes) - 1))
        self.update()
        self.stateChanged.emit()

    def mousePressEvent(self, event):
        pos = event.position()
        if self.play_rect.contains(pos):
            self.play_story()
            return
        if self.reset_rect.contains(pos):
            self.reset_story()
            return
        for index, hitbox in self.node_hitboxes:
            if hitbox.contains(pos):
                self.set_story_step(index)
                return
        super().mousePressEvent(event)

    def _story_nodes(self):
        palette = {
            "Ocean": "#4EA3F1",
            "Ice shelf": "#B8F2FF",
            "Ice dynamics": "#7BDFF2",
            "Observation": "#9575CD",
            "Atmosphere": "#A7C7E7",
            "Hydrology": "#58D5FF",
            "Fracture": "#FF8A65",
            "Instability": "#FFB067",
            "Impact": "#CDB4DB",
            "Forcing": "#F6C85F",
            "Uncertainty": "#FFD166",
            "Solid Earth": "#C19A6B",
            "Feedback": "#9CCC65",
            "Paleo": "#F6C85F",
            "Model": "#CDB4DB",
            "Risk": "#FF8A65",
        }
        scenes = {
            "Ice Sheet Stability": {
                "opening": "From ocean heat to ice-sheet retreat, the story emerges through connected mechanisms.",
                "Past": [
                    ("Past Warm Periods", "Paleo", 0.18, 0.37, "Past warm intervals show that Antarctica can retreat beyond the satellite record.", "Marine sediments and sea-level archives"),
                    ("Marine-based Ice", "Ice dynamics", 0.40, 0.49, "Large sectors rest below sea level and are sensitive to ocean and grounding-line feedbacks.", "Bed topography and paleo reconstruction"),
                    ("Retreat Episodes", "Ice dynamics", 0.62, 0.42, "Earlier retreat gives boundary conditions for testing instability mechanisms.", "Shelf cores and geomorphic records"),
                    ("Model Constraints", "Model", 0.82, 0.58, "Paleo records constrain projections by showing what the ice sheet has done before.", "Model-data comparison"),
                ],
                "Present": [
                    ("Ocean Heat", "Ocean", 0.16, 0.54, "Warm Circumpolar Deep Water can reach cavities beneath vulnerable ice shelves.", "Moorings, CTD, and ocean reanalysis"),
                    ("Shelf Thinning", "Ice shelf", 0.38, 0.42, "Basal melt thins shelves and weakens buttressing.", "Altimetry and melt-rate estimates"),
                    ("Grounding Retreat", "Ice dynamics", 0.60, 0.51, "Grounding-line retreat links shelf thinning to inland discharge.", "InSAR grounding-zone mapping"),
                    ("Sea-level Risk", "Impact", 0.80, 0.40, "Antarctica remains a major uncertainty in future sea-level projections.", "Projection ensembles"),
                ],
                "Future": [
                    ("Forcing Pathways", "Forcing", 0.18, 0.46, "Future winds, stratification, and meltwater feedbacks control ocean heat access.", "Climate and ocean scenarios"),
                    ("Buttressing Loss", "Ice shelf", 0.40, 0.34, "Thinner shelves provide less back stress to inland ice.", "Stress-balance models"),
                    ("Instability Thresholds", "Instability", 0.62, 0.50, "MISI-like retreat may become hard to reverse on retrograde beds.", "Ice-sheet sensitivity tests"),
                    ("Uncertainty Range", "Uncertainty", 0.82, 0.35, "Projection spread depends on poorly constrained process coupling.", "Uncertainty quantification"),
                ],
            },
            "Ocean Heat Pathways": {
                "opening": "Ocean access links Southern Ocean change to basal melting and ice-shelf thinning.",
                "Past": [
                    ("Shelf Break", "Ocean", 0.18, 0.44, "Bathymetric gateways shaped earlier continental-shelf heat access.", "Bathymetry and sediment archives"),
                    ("Warm Intervals", "Paleo", 0.40, 0.34, "Past warm periods offer clues about persistent ocean forcing.", "Paleoceanographic proxies"),
                    ("Melt Archive", "Paleo", 0.62, 0.52, "Marine records can preserve signals of grounding-zone retreat and shelf melt.", "Marine sediment cores"),
                    ("Analog Limits", "Uncertainty", 0.82, 0.40, "Ancient states help, but no past interval maps perfectly onto modern forcing.", "Proxy uncertainty"),
                ],
                "Present": [
                    ("CDW Intrusion", "Ocean", 0.18, 0.48, "Warm water follows troughs toward vulnerable shelves.", "Moorings and CTD sections"),
                    ("Cavity Circulation", "Ocean", 0.40, 0.36, "Sub-ice circulation controls where basal melting concentrates.", "Ocean models"),
                    ("Basal Melt", "Ice shelf", 0.62, 0.50, "Basal melt thins shelves and changes stress transmission.", "Altimetry and ice-shelf mass balance"),
                    ("Discharge Signal", "Observation", 0.82, 0.38, "Velocity and elevation signals connect ocean forcing to inland response.", "InSAR and altimetry"),
                ],
                "Future": [
                    ("Wind Shift", "Forcing", 0.18, 0.43, "Changing winds can reorganize shelf-edge heat access.", "Climate projections"),
                    ("Freshwater Feedback", "Feedback", 0.40, 0.56, "Meltwater freshening can change stratification and circulation pathways.", "Coupled ocean-ice models"),
                    ("Persistent Melt", "Risk", 0.62, 0.40, "Sustained heat delivery can keep shelves in a thinning regime.", "Scenario experiments"),
                    ("Observation Need", "Observation", 0.82, 0.52, "Targeted observations are needed to reduce pathway uncertainty.", "Field campaigns and AUVs"),
                ],
            },
            "Hydrofracture & Ice Cliff Risk": {
                "opening": "Surface melt, crevasses, and shelf strength govern rapid collapse risk.",
                "Past": [
                    ("Collapse Analog", "Paleo", 0.18, 0.44, "Past and recent shelf collapses provide analogs for rapid structural failure.", "Larsen B and paleo shelf records"),
                    ("Surface Melt", "Atmosphere", 0.40, 0.34, "Meltwater loading can deepen crevasses through hydrofracture.", "Surface melt mapping"),
                    ("Shelf Breakup", "Fracture", 0.62, 0.52, "Connected fractures can convert a shelf into fragmented ice.", "Optical and SAR imagery"),
                    ("Response Lag", "Ice dynamics", 0.82, 0.40, "Inland acceleration can follow after buttressing is removed.", "Post-collapse velocity change"),
                ],
                "Present": [
                    ("Ponding", "Hydrology", 0.18, 0.46, "Surface lakes and slush zones mark vulnerable shelves.", "Optical imagery and climate data"),
                    ("Crevasse Fields", "Fracture", 0.40, 0.34, "Crevasse density shows where fracture pathways may connect.", "SAR and high-resolution imagery"),
                    ("Buttressing Map", "Ice shelf", 0.62, 0.51, "Passive and active shelf zones differ in their dynamic importance.", "Stress-balance modeling"),
                    ("MICI Debate", "Instability", 0.82, 0.39, "Marine ice-cliff instability is a high-end mechanism with large uncertainty.", "Model comparison"),
                ],
                "Future": [
                    ("Warming Summers", "Atmosphere", 0.18, 0.44, "More frequent melt seasons can increase surface-water loading.", "Climate projections"),
                    ("Shelf Collapse", "Risk", 0.40, 0.55, "Rapid shelf loss removes back stress from tributary glaciers.", "Collapse scenario experiments"),
                    ("Cliff Exposure", "Instability", 0.62, 0.39, "Tall exposed ice cliffs may fail rapidly in some model formulations.", "MICI sensitivity tests"),
                    ("Constraint Need", "Observation", 0.82, 0.52, "Future risk depends on better fracture physics and shelf-strength constraints.", "Observation and modeling"),
                ],
            },
            "Solid Earth Feedbacks": {
                "opening": "The solid Earth is both a correction for observations and an active ice-sheet feedback.",
                "Past": [
                    ("Ice Load Memory", "Feedback", 0.18, 0.44, "Past ice loading still shapes modern bedrock motion.", "GIA theory and paleo ice history"),
                    ("Raised Shores", "Paleo", 0.40, 0.34, "Relative sea-level markers help constrain uplift and former ice extent.", "Geomorphic records"),
                    ("Mantle Structure", "Solid Earth", 0.62, 0.52, "Viscosity variations govern how fast bedrock responds.", "Seismology and GIA models"),
                    ("Model Input", "Model", 0.82, 0.40, "Past constraints improve present mass-balance corrections.", "Model calibration"),
                ],
                "Present": [
                    ("GRACE Signal", "Observation", 0.18, 0.45, "Gravity change combines ice mass loss and solid-Earth motion.", "GRACE / GRACE-FO"),
                    ("GNSS Uplift", "Solid Earth", 0.40, 0.34, "Stations measure bedrock motion that helps separate ice and Earth signals.", "GPS/GNSS networks"),
                    ("GIA Correction", "Observation", 0.62, 0.52, "Mass trends need solid-Earth correction to avoid biased estimates.", "GIA model ensembles"),
                    ("Grounding Feedback", "Feedback", 0.82, 0.40, "Bedrock uplift and local sea-level fall can alter retreat dynamics.", "Coupled ice-solid Earth models"),
                ],
                "Future": [
                    ("Bedrock Uplift", "Feedback", 0.18, 0.46, "Ice loss can trigger uplift that changes grounding-zone geometry.", "Coupled sea-level models"),
                    ("Relative Sea Level", "Feedback", 0.40, 0.31, "Local sea-level fall may slow retreat in some settings.", "Sea-level fingerprint models"),
                    ("3D Earth Structure", "Uncertainty", 0.62, 0.49, "Viscosity varies strongly across Antarctica, affecting feedback timing.", "Seismology and geodesy"),
                    ("Coupled Projection", "Model", 0.82, 0.35, "Future projections need ice, ocean, atmosphere, and solid-Earth coupling.", "Coupled model development"),
                ],
            },
        }
        scene = scenes.get(self.story, scenes["Ice Sheet Stability"])
        rows = scene.get(self.lens, scene["Past"])
        nodes = []
        for name, kind, fx, fy, note, evidence in rows:
            nodes.append(
                {
                    "name": name,
                    "kind": kind,
                    "fx": fx,
                    "fy": fy,
                    "color": palette.get(kind, "#9EDBFF"),
                    "note": note,
                    "evidence": evidence,
                }
            )
        return scene["opening"], nodes

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        opening, nodes = self._story_nodes()
        rect = QRectF(self.rect()).adjusted(0, 0, -1, -1)
        bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bg.setColorAt(0, QColor("#10253f"))
        bg.setColorAt(0.55, QColor("#07111f"))
        bg.setColorAt(1, QColor("#080b1a"))
        painter.setPen(QPen(QColor(210, 238, 255, 54), 1.2))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 26, 26)
        for i in range(56):
            twinkle = 0.5 + 0.5 * sin(self.ambient_phase * 2 * pi + i * 0.73)
            painter.setPen(QColor(240, 250, 255, 38 + int(twinkle * 64)))
            painter.drawPoint(QPointF(rect.left() + 32 + (i * 83) % int(rect.width() - 64), rect.top() + 28 + (i * 47) % int(rect.height() - 56)))

        title = QRectF(28, 54, rect.width() * 0.38, 128)
        painter.setBrush(QColor(12, 27, 49, 210))
        painter.setPen(QPen(QColor(210, 238, 255, 65), 1))
        painter.drawRoundedRect(title, 22, 22)
        painter.setPen(QColor("#9ed8f5"))
        painter.setFont(ui_font(8, QFont.Bold))
        painter.drawText(QRectF(title.left() + 22, title.top() + 18, title.width() - 44, 18), f"SCIENTIFIC STORY ENGINE - {self.lens.upper()} LENS")
        painter.setPen(QColor("#f8fbff"))
        painter.setFont(ui_font(19, QFont.Bold))
        painter.drawText(QRectF(title.left() + 22, title.top() + 48, title.width() - 44, 32), self.story)
        painter.setPen(QColor(222, 240, 252, 200))
        painter.setFont(ui_font(9))
        painter.drawText(QRectF(title.left() + 22, title.top() + 82, title.width() - 44, 38), Qt.TextWordWrap, opening)

        stage = QRectF(28, 186, rect.width() * 0.64, rect.height() - 218)
        painter.setBrush(QColor(7, 15, 29, 145))
        painter.setPen(QPen(QColor(210, 238, 255, 50), 1))
        painter.drawRoundedRect(stage, 22, 22)

        painter.setBrush(QColor(10, 20, 36, 210))
        painter.setPen(QPen(QColor(210, 238, 255, 72), 1))
        replay = QRectF(stage.left() + 26, stage.top() + 22, 118, 36)
        reset = QRectF(replay.right() + 12, replay.top(), 82, 36)
        self.play_rect = replay
        self.reset_rect = reset
        painter.drawRoundedRect(replay, 18, 18)
        painter.drawRoundedRect(reset, 18, 18)
        painter.setPen(QColor("#f8fbff"))
        painter.setFont(ui_font(9, QFont.Bold))
        if self.play_timer.isActive():
            play_label = "Playing"
        elif self.step >= len(nodes) - 1 and nodes:
            play_label = "Replay Story"
        else:
            play_label = "Begin Story"
        painter.drawText(replay, Qt.AlignCenter, play_label)
        painter.drawText(reset, Qt.AlignCenter, "Reset")
        progress_glow = 190 + int(50 * (0.5 + 0.5 * sin(self.ambient_phase * 2 * pi)))
        painter.setPen(QPen(QColor(126, 220, 255, progress_glow), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(reset.right() + 22, reset.center().y()), QPointF(reset.right() + 180, reset.center().y()))
        painter.setPen(QPen(QColor(255, 255, 255, 210), 4, Qt.SolidLine, Qt.RoundCap))
        progress_fraction = 0 if self.step < 0 else (self.step + 1) / max(1, len(nodes))
        painter.drawLine(QPointF(reset.right() + 22, reset.center().y()), QPointF(reset.right() + 22 + 158 * progress_fraction, reset.center().y()))

        horizon = QPainterPath()
        horizon.moveTo(stage.left(), stage.bottom() - 78)
        horizon.lineTo(stage.left() + 52, stage.bottom() - 90)
        horizon.lineTo(stage.left() + 176, stage.bottom() - 84)
        horizon.lineTo(stage.left() + 366, stage.bottom() - 96)
        horizon.lineTo(stage.right(), stage.bottom() - 76)
        horizon.lineTo(stage.right(), stage.bottom())
        horizon.lineTo(stage.left(), stage.bottom())
        horizon.closeSubpath()
        painter.setBrush(QColor(177, 230, 248, 155))
        painter.setPen(Qt.NoPen)
        painter.drawPath(horizon)
        painter.fillRect(QRectF(stage.left(), stage.bottom() - 58, stage.width(), 58), QColor(7, 72, 100, 130))

        visible_count = 0 if self.step < 0 else self.step + 1
        visible_nodes = nodes[:visible_count]
        self.node_hitboxes = []
        prev = None
        preview_prev = None
        painter.setPen(QPen(QColor(126, 220, 255, 42), 2))
        for index, node in enumerate(nodes):
            fx, fy = node["fx"], node["fy"]
            pos = QPointF(stage.left() + stage.width() * fx, stage.top() + stage.height() * fy)
            if preview_prev:
                painter.drawLine(preview_prev, pos)
            preview_prev = pos
            color = QColor(node["color"])
            preview_radius = 22 + 2.5 * (0.5 + 0.5 * sin(self.ambient_phase * 2 * pi + index * 0.9))
            preview_color = QColor(color)
            preview_color.setAlpha((72 if self.step < 0 else 38) + int(18 * (0.5 + 0.5 * sin(self.ambient_phase * 2 * pi + index))))
            painter.setBrush(preview_color)
            painter.setPen(QPen(QColor(255, 255, 255, 70), 1))
            painter.drawEllipse(pos, preview_radius, preview_radius)
            painter.setPen(QColor(245, 250, 255, 125 if self.step < 0 else 72))
            painter.setFont(ui_font(7, QFont.Bold))
            painter.drawText(QRectF(pos.x() - 70, pos.y() - 9, 140, 18), Qt.AlignCenter, node["name"])
            self.node_hitboxes.append((index, QRectF(pos.x() - preview_radius - 8, pos.y() - preview_radius - 8, (preview_radius + 8) * 2, (preview_radius + 8) * 2)))
        painter.setPen(QPen(QColor(8, 8, 10, 210), 10))
        for node in visible_nodes:
            fx, fy = node["fx"], node["fy"]
            pos = QPointF(stage.left() + stage.width() * fx, stage.top() + stage.height() * fy)
            if prev:
                painter.drawLine(prev, pos)
            prev = pos
        for index, node in enumerate(visible_nodes):
            name, fx, fy, color = node["name"], node["fx"], node["fy"], node["color"]
            pos = QPointF(stage.left() + stage.width() * fx, stage.top() + stage.height() * fy)
            active_node = index == self.step
            pulse = 0.5 + 0.5 * sin(self.ambient_phase * 2 * pi + index * 0.8)
            radius = (33 + 3 * pulse) if active_node else (23 + 1.5 * pulse)
            glow = QRadialGradient(pos, (72 + 9 * pulse) if active_node else (54 + 5 * pulse))
            glow.setColorAt(0, QColor(color))
            glow.setColorAt(1, QColor(126, 220, 255, 0))
            painter.fillRect(stage, glow)
            painter.setBrush(QColor(color))
            painter.setPen(QPen(QColor(255, 255, 255, 230), 4 if active_node else 2))
            painter.drawEllipse(pos, radius, radius)
            self.node_hitboxes.append((index, QRectF(pos.x() - radius - 8, pos.y() - radius - 8, (radius + 8) * 2, (radius + 8) * 2)))
            painter.setPen(QColor("#ffffff"))
            painter.setFont(ui_font(7, QFont.Bold))
            painter.drawText(QRectF(pos.x() - 70, pos.y() - 9, 140, 18), Qt.AlignCenter, name)

        chain = " -> ".join(node["name"] for node in nodes)
        painter.setBrush(QColor(20, 38, 66, 190))
        painter.setPen(QPen(QColor(210, 238, 255, 55), 1))
        caption = QRectF(stage.left() + 110, stage.bottom() - 135, stage.width() - 220, 58)
        painter.drawRoundedRect(caption, 16, 16)
        painter.setPen(QColor(245, 250, 255, 220))
        painter.setFont(ui_font(9, QFont.Bold))
        if self.step < 0:
            painter.drawText(caption.adjusted(14, 9, -14, -9), Qt.AlignCenter | Qt.TextWordWrap, "Click Begin Story to reveal the mechanism step by step, or click any glowing node to inspect its evidence card.")
        else:
            active = nodes[self.step]
            painter.drawText(caption.adjusted(14, 9, -14, -9), Qt.AlignCenter | Qt.TextWordWrap, f"{active['name']} - {active['note']}")

        side = QRectF(stage.right() + 18, stage.top() - 120, rect.right() - stage.right() - 46, stage.height() + 120)
        painter.setBrush(QColor(7, 15, 29, 205))
        painter.setPen(QPen(QColor(210, 238, 255, 65), 1))
        painter.drawRoundedRect(side, 22, 22)
        painter.setBrush(QColor(78, 163, 241, 44))
        painter.drawRoundedRect(QRectF(side.left() + 22, side.top() + 22, 145, 30), 15, 15)
        if self.step < 0:
            painter.setPen(QColor("#d8f2ff"))
            painter.setFont(ui_font(8, QFont.Bold))
            painter.drawText(QRectF(side.left() + 32, side.top() + 28, 122, 18), "Scientific Story Engine")
            painter.setPen(QColor("#f8fbff"))
            painter.setFont(ui_font(18, QFont.Bold))
            painter.drawText(QRectF(side.left() + 22, side.top() + 72, side.width() - 44, 34), self.story)
            painter.setPen(QColor(235, 248, 255, 210))
            painter.setFont(ui_font(9))
            painter.drawText(QRectF(side.left() + 22, side.top() + 116, side.width() - 44, 72), Qt.TextWordWrap, opening)
            painter.setPen(QColor("#9ed8f5"))
            painter.setFont(ui_font(8, QFont.Bold))
            painter.drawText(QRectF(side.left() + 22, side.top() + 214, side.width() - 44, 18), "CURRENT LENS")
            painter.setPen(QColor(245, 250, 255, 220))
            painter.setFont(ui_font(9))
            painter.drawText(QRectF(side.left() + 22, side.top() + 238, side.width() - 44, 40), f"{self.lens} - {len(nodes)} story beats")
            painter.setBrush(QColor(34, 197, 94, 24))
            painter.setPen(QPen(QColor(74, 222, 128, 60), 1))
            slide_box = QRectF(side.left() + 22, side.top() + 304, side.width() - 44, 96)
            painter.drawRoundedRect(slide_box, 16, 16)
            painter.setPen(QColor(235, 255, 242, 225))
            painter.drawText(slide_box.adjusted(14, 12, -14, -12), Qt.TextWordWrap, "Press Begin Story, then use each glowing node as one step of a scientific explanation. The right card gives the short interpretation and evidence layer.")
        else:
            active = nodes[self.step]
            painter.setPen(QColor("#d8f2ff"))
            painter.setFont(ui_font(8, QFont.Bold))
            painter.drawText(QRectF(side.left() + 32, side.top() + 28, 122, 18), f"{self.lens} - {active['kind']}")
            painter.setPen(QColor("#f8fbff"))
            painter.setFont(ui_font(18, QFont.Bold))
            painter.drawText(QRectF(side.left() + 22, side.top() + 72, side.width() - 44, 34), active["name"])
            painter.setPen(QColor(235, 248, 255, 210))
            painter.setFont(ui_font(9))
            painter.drawText(QRectF(side.left() + 22, side.top() + 110, side.width() - 44, 24), f"Node {self.step + 1} of {len(nodes)} in {self.story}.")
            y = side.top() + 128
            for label, text in [
                ("SCIENTIFIC MEANING", active["note"]),
                ("EVIDENCE LAYER", active["evidence"]),
            ]:
                painter.setPen(QColor("#9ed8f5"))
                painter.setFont(ui_font(8, QFont.Bold))
                painter.drawText(QRectF(side.left() + 22, y, side.width() - 44, 18), label)
                painter.setPen(QColor(245, 250, 255, 220))
                painter.setFont(ui_font(9))
                painter.drawText(QRectF(side.left() + 22, y + 22, side.width() - 44, 42), Qt.TextWordWrap, text)
                y += 68
            mini_w = (side.width() - 53) / 2
            for x, label, text in [
                (side.left() + 22, "Use in slides", "One visual beat for a talk."),
                (side.left() + 31 + mini_w, "Reading logic", "Mechanism + evidence + uncertainty."),
            ]:
                mini = QRectF(x, y, mini_w, 64)
                painter.setBrush(QColor(255, 255, 255, 13))
                painter.setPen(QPen(QColor(255, 255, 255, 34), 1))
                painter.drawRoundedRect(mini, 14, 14)
                painter.setPen(QColor("#f8fbff"))
                painter.setFont(ui_font(8, QFont.Bold))
                painter.drawText(QRectF(mini.left() + 10, mini.top() + 10, mini.width() - 20, 18), label)
                painter.setPen(QColor(230, 245, 255, 178))
                painter.setFont(ui_font(8))
                painter.drawText(QRectF(mini.left() + 10, mini.top() + 28, mini.width() - 20, 30), Qt.TextWordWrap, text)
            y += 76
            painter.setPen(QColor("#9ed8f5"))
            painter.setFont(ui_font(8, QFont.Bold))
            painter.drawText(QRectF(side.left() + 22, y, side.width() - 44, 18), "SLIDE-READY CHAIN")
            slide_box = QRectF(side.left() + 22, y + 22, side.width() - 44, 56)
            painter.setBrush(QColor(34, 197, 94, 24))
            painter.setPen(QPen(QColor(74, 222, 128, 60), 1))
            painter.drawRoundedRect(slide_box, 16, 16)
            painter.setPen(QColor(235, 255, 242, 225))
            painter.setFont(ui_font(9))
            painter.drawText(slide_box.adjusted(12, 10, -12, -10), Qt.TextWordWrap, chain)


class LabCanvasWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(430)
        self.experiment = "Glacier Flow Simulator"
        self.values = {}
        self.flow_phase = 0.0
        self.flow_timer = QTimer(self)
        self.flow_timer.setTimerType(Qt.PreciseTimer)
        self.flow_timer.setInterval(SLOW_ANIMATION_INTERVAL_MS)
        self.flow_timer.timeout.connect(self._advance_flow_particles)
        self.flow_timer.start()

    def _advance_flow_particles(self):
        if not self.isVisible():
            self.flow_timer.stop()
            return
        self.flow_phase = (self.flow_phase + 0.008) % 1.0
        if self.experiment == "Glacier Flow Simulator":
            self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.flow_timer.isActive():
            self.flow_timer.start()

    def hideEvent(self, event):
        self.flow_timer.stop()
        super().hideEvent(event)

    def set_experiment(self, name):
        self.experiment = name
        self.update()

    def set_values(self, values):
        self.values = dict(values)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0, 0, -1, -1)
        frame_bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
        frame_bg.setColorAt(0, QColor("#0d2238"))
        frame_bg.setColorAt(0.55, QColor("#081525"))
        frame_bg.setColorAt(1, QColor("#0f1328"))
        painter.setBrush(frame_bg)
        painter.setPen(QPen(QColor(190, 226, 255, 42), 1))
        painter.drawRoundedRect(rect, 18, 18)
        if self.experiment == "Ice Shelf Buttressing Lab":
            self._draw_buttressing(painter, rect)
        elif self.experiment == "Hydrofracture & Ice Shelf Collapse Lab":
            self._draw_hydrofracture(painter, rect)
        else:
            self._draw_glacier_flow(painter, rect)

    @staticmethod
    def _clip(value, minimum=0.0, maximum=1.0):
        return max(minimum, min(maximum, float(value)))

    def _number(self, key, default=0):
        try:
            return float(self.values.get(key, default))
        except (TypeError, ValueError):
            return float(default)

    def _draw_arrow(self, painter, start, end, color, width=3):
        pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)
        angle = atan2(end.y() - start.y(), end.x() - start.x())
        size = 9 + width * 1.3
        left = QPointF(end.x() - size * cos(angle - pi / 6), end.y() - size * sin(angle - pi / 6))
        right = QPointF(end.x() - size * cos(angle + pi / 6), end.y() - size * sin(angle + pi / 6))
        painter.drawLine(end, left)
        painter.drawLine(end, right)

    def _draw_tag(self, painter, x, y, text, accent="#5aa7ff", min_width=92):
        width = max(min_width, min(250, len(text) * 7 + 22))
        rect = QRectF(x, y, width, 28)
        painter.setPen(QPen(QColor(accent), 1))
        painter.setBrush(QColor(245, 251, 255, 228))
        painter.drawRoundedRect(rect, 14, 14)
        painter.setPen(QColor("#17314d"))
        painter.setFont(ui_font(8, QFont.Bold))
        painter.drawText(rect.adjusted(10, 0, -10, 0), Qt.AlignVCenter, text)
        return rect

    def _draw_bar(self, painter, rect, label, value, accent, text_color="#1f2937"):
        value = self._clip(value)
        painter.setPen(text_color if isinstance(text_color, QColor) else QColor(text_color))
        painter.setFont(ui_font(8, QFont.Bold))
        painter.drawText(QRectF(rect.left(), rect.top() - 20, rect.width(), 18), label)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(226, 238, 247))
        painter.drawRoundedRect(rect, 6, 6)
        fill = QRectF(rect.left(), rect.top(), rect.width() * value, rect.height())
        painter.setBrush(accent)
        painter.drawRoundedRect(fill, 6, 6)

    def _draw_glacier_flow(self, painter, rect):
        plot = rect.adjusted(28, 26, -28, -18)
        retreat = self._number("retreat", 8)
        effective_ocean = self._number("effective_ocean", 0)
        effective_shelf = self._number("effective_shelf", 200)
        shelf_collapse = bool(self.values.get("shelf_collapse", False))
        cdw_intrusion = bool(self.values.get("cdw_intrusion", True))
        misi_on = bool(self.values.get("misi_on", True))
        velocity = self._number("velocity", 1.0)
        snowfall = self._number("snowfall", 1.0)
        bed_slope = self._number("bed", 1.0)
        ocean_strength = self._clip(max(effective_ocean, 0) / 5)
        speed_strength = self._clip(velocity / 4.4)
        shelf_strength = self._clip(effective_shelf / 500)
        grounding_fraction = self._clip((92 - retreat) / 92, 0.28, 0.86)
        grounding_x = 92 * grounding_fraction

        scene_path = QPainterPath()
        scene_path.addRoundedRect(plot, 8, 8)
        painter.save()
        painter.setClipPath(scene_path)
        scene_bg = QLinearGradient(plot.topLeft(), plot.bottomRight())
        scene_bg.setColorAt(0, QColor("#071529"))
        scene_bg.setColorAt(0.52, QColor("#0c2740"))
        scene_bg.setColorAt(1, QColor("#172446"))
        painter.fillRect(plot, scene_bg)

        def project(x, y, z):
            sx = plot.left() + plot.width() * (0.11 + 0.0071 * x + 0.0022 * y)
            sy = plot.top() + plot.height() * (0.67 - 0.0030 * x + 0.0035 * y - 0.00039 * z)
            return QPointF(sx, sy)

        def bed_z(x, y):
            return -155 - bed_slope * x * 9 + 65 * max(0, 1 - (abs(y) / 32) ** 1.7)

        def ice_z(x, y):
            base = 620 + snowfall * 110 - effective_ocean * 55 + effective_shelf * 0.35 - bed_slope * 38
            base = max(base, 120)
            center_shape = max(0.08, 1 - (abs(y) / 32) ** 1.8)
            downstream = max(0.08, (1 - x / 112) ** 1.45)
            texture = 1 + 0.04 * sin(x / 7) * cos(y / 6)
            return max(24, base * center_shape * downstream * texture)

        x_grid = [0, 9, 18, 27, 36, 45, 54, 63, 72, 82, min(105, grounding_x + 18)]
        y_grid = [-32, -24, -16, -8, 0, 8, 16, 24, 32]

        painter.setPen(QPen(QColor(180, 220, 245, 34), 1))
        for x in x_grid:
            painter.drawLine(project(x, -32, 0), project(x, 32, 0))
        for y in y_grid:
            painter.drawLine(project(0, y, 0), project(105, y, 0))

        ocean_poly = QPolygonF([project(max(0, grounding_x - 4), -34, 0), project(108, -34, 0), project(108, 34, 0), project(max(0, grounding_x - 4), 34, 0)])
        ocean_grad = QLinearGradient(ocean_poly.boundingRect().topLeft(), ocean_poly.boundingRect().bottomRight())
        ocean_grad.setColorAt(0, QColor(80, 204, 245, 92))
        ocean_grad.setColorAt(1, QColor(19, 92, 166, 172))
        painter.setBrush(ocean_grad)
        painter.setPen(QPen(QColor(90, 180, 230, 80), 1))
        painter.drawPolygon(ocean_poly)

        for xi0, xi1 in zip(x_grid[:-1], x_grid[1:]):
            if xi0 > grounding_x + 24:
                continue
            for yi0, yi1 in zip(y_grid[:-1], y_grid[1:]):
                poly = QPolygonF([project(xi0, yi0, bed_z(xi0, yi0)), project(xi1, yi0, bed_z(xi1, yi0)), project(xi1, yi1, bed_z(xi1, yi1)), project(xi0, yi1, bed_z(xi0, yi1))])
                shade = int(132 + 45 * (xi0 / 105) + 18 * ((yi0 + 32) / 64))
                painter.setBrush(QColor(shade, int(shade * 0.72), 82, 160))
                painter.setPen(QPen(QColor(174, 126, 78, 52), 1))
                painter.drawPolygon(poly)

        ice_x_grid = [x for x in x_grid if x <= grounding_x] + ([grounding_x] if grounding_x not in x_grid else [])
        ice_x_grid = sorted(set(round(x, 2) for x in ice_x_grid))
        for xi0, xi1 in zip(ice_x_grid[:-1], ice_x_grid[1:]):
            for yi0, yi1 in zip(y_grid[:-1], y_grid[1:]):
                avg = (ice_z(xi0, yi0) + ice_z(xi1, yi0) + ice_z(xi1, yi1) + ice_z(xi0, yi1)) / 4
                intensity = self._clip(avg / 720)
                red = int(252 - 205 * intensity)
                green = int(254 - 72 * intensity)
                blue = int(255 - 8 * intensity)
                poly = QPolygonF([project(xi0, yi0, ice_z(xi0, yi0)), project(xi1, yi0, ice_z(xi1, yi0)), project(xi1, yi1, ice_z(xi1, yi1)), project(xi0, yi1, ice_z(xi0, yi1))])
                painter.setBrush(QColor(red, green, blue, 235))
                painter.setPen(QPen(QColor(216, 246, 255, 72), 1))
                painter.drawPolygon(poly)

        if not shelf_collapse:
            shelf_end = min(106, grounding_x + 16 + 16 * shelf_strength)
            shelf_height = 60 + effective_shelf * 0.28
            shelf_poly = QPolygonF([project(grounding_x, -29, shelf_height), project(shelf_end, -29, shelf_height * 0.72), project(shelf_end, 29, shelf_height * 0.72), project(grounding_x, 29, shelf_height)])
            shelf_grad = QLinearGradient(shelf_poly.boundingRect().topLeft(), shelf_poly.boundingRect().bottomRight())
            shelf_grad.setColorAt(0, QColor(222, 252, 255, 220))
            shelf_grad.setColorAt(1, QColor(123, 210, 238, 198))
            painter.setBrush(shelf_grad)
            painter.setPen(QPen(QColor(74, 171, 216), 2))
            painter.drawPolygon(shelf_poly)
            shelf_label = project((grounding_x + shelf_end) / 2, -30, shelf_height + 35)
            self._draw_tag(painter, shelf_label.x() + 4, shelf_label.y() - 46, "Floating ice shelf", "#4aaad8", 132)
        else:
            lost_poly = QPolygonF([project(grounding_x + 2, -28, 90), project(grounding_x + 30, -28, 55), project(grounding_x + 30, 28, 55), project(grounding_x + 2, 28, 90)])
            painter.setBrush(QColor(128, 128, 128, 42))
            painter.setPen(QPen(QColor(116, 124, 139), 1.6, Qt.DashLine))
            painter.drawPolygon(lost_poly)
            label = project(grounding_x + 8, -31, 120)
            self._draw_tag(painter, label.x(), label.y(), "collapsed shelf area", "#ef4444", 136)

        gl_top = project(grounding_x, -32, 105)
        gl_bottom = project(grounding_x, 32, 105)
        painter.setPen(QPen(QColor(220, 20, 35), 4, Qt.DashLine, Qt.RoundCap))
        painter.drawLine(gl_top, gl_bottom)
        gl_label = project(grounding_x, -36, 145)
        self._draw_tag(painter, gl_label.x() - 106, gl_label.y() - 22, "Grounding line", "#ef4444", 118)

        if cdw_intrusion or ocean_strength > 0.08:
            heat_center = project(grounding_x + 20, 14, -18)
            heat = QRadialGradient(heat_center, 82 + ocean_strength * 80)
            heat.setColorAt(0, QColor(255, 92, 34, 175))
            heat.setColorAt(0.48, QColor(255, 169, 54, 82))
            heat.setColorAt(1, QColor(255, 169, 54, 0))
            painter.setBrush(heat)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(heat_center, 100 + ocean_strength * 90, 38 + ocean_strength * 26)
            self._draw_tag(painter, heat_center.x() - 44, heat_center.y() + 42, "warm CDW intrusion", "#f97316", 142)

        for i, y in enumerate([-22, -14, -6, 2, 10, 18]):
            x0 = 12 + i * 7
            z0 = ice_z(x0, y) + 18
            start = project(x0, y, z0)
            end = project(min(grounding_x - 3, x0 + 11 + speed_strength * 15), y - 3, z0 - 12)
            self._draw_arrow(painter, start, end, QColor(255, 140, 40), 3 + speed_strength * 3)

        particle_rows = 4 + int(self._clip(snowfall / 5) * 4)
        painter.setBrush(QColor(0, 218, 205, 220))
        painter.setPen(QPen(QColor(0, 116, 120, 120), 1))
        for row in range(particle_rows):
            y = -20 + row * (40 / max(1, particle_rows - 1))
            for k in range(13):
                flow_len = max(18, grounding_x - 6)
                x = ((k / 13 + self.flow_phase * (0.45 + speed_strength)) % 1.0) * flow_len
                z = ice_z(x, y) + 20
                pos = project(x, y + 1.5 * sin(x / 8 + row), z)
                painter.drawEllipse(pos, 3.2, 3.2)

        grounded_label = project(14, -31, ice_z(14, -22) + 58)
        ocean_label = project(98, 20, 38)
        bed_label = project(14, 30, bed_z(14, 30) - 12)
        self._draw_tag(painter, grounded_label.x() - 40, grounded_label.y() - 18, "Grounded ice", "#167ef8", 112)
        self._draw_tag(painter, ocean_label.x() - 58, ocean_label.y() - 18, "Ocean surface", "#238ad2", 122)
        self._draw_tag(painter, bed_label.x() - 24, bed_label.y() - 18, "Bedrock", "#99663c", 88)
        status = "MISI active" if misi_on and retreat > 20 else "MISI monitored"
        if shelf_collapse:
            status = "Buttressing lost"
        painter.restore()
        painter.setPen(QColor("#f4fbff"))
        painter.setFont(ui_font(13, QFont.Bold))
        painter.drawText(QRectF(plot.left() + 18, plot.top() + 16, plot.width() - 36, 28), "3D Conceptual Antarctic Ice Sheet Simulator")
        panel = QRectF(plot.right() - 270, plot.bottom() - 118, 236, 72)
        painter.setPen(QPen(QColor(190, 226, 255, 72), 1))
        painter.setBrush(QColor(7, 15, 29, 218))
        painter.drawRoundedRect(panel, 14, 14)
        self._draw_bar(painter, QRectF(panel.left() + 16, panel.top() + 28, panel.width() - 32, 10), "Ice-loss pressure", self._number("ice_loss", 1) / 8, QColor("#f97316"), "#eaf6ff")
        self._draw_bar(painter, QRectF(panel.left() + 16, panel.top() + 56, panel.width() - 32, 10), status, retreat / 68, QColor("#ef4444"), "#eaf6ff")

    def _draw_buttressing(self, painter, rect):
        plot = rect.adjusted(28, 36, -28, -30)
        painter.fillRect(plot, QColor("#f6fbff"))
        painter.setPen(QPen(QColor(218, 230, 239), 1))
        for i in range(6):
            y = plot.top() + i * plot.height() / 5
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

        shelf = self._number("shelf", 260)
        ocean_temp = self._number("ocean", 1)
        pinning = self._number("pinning", 55)
        calving = self._number("calving", 20)
        lateral = self._number("lateral", 60)
        buttressing = self._number("buttressing", 45)
        velocity_myr = self._number("velocity_myr", 650)
        bed_slope = self._number("bed", 1.5)
        thickness_factor = self._clip(shelf / 700)
        calving_factor = self._clip(calving / 100)
        pinning_factor = self._clip(pinning / 100)
        lateral_factor = self._clip(lateral / 100)
        ocean_factor = self._clip(max(ocean_temp, 0) / 5)

        gx = plot.left() + plot.width() * 0.43
        shelf_full_length = plot.width() * 0.42
        remaining_length = shelf_full_length * (1 - calving_factor)
        shelf_end = gx + remaining_length
        shelf_thick = 26 + 70 * thickness_factor
        shelf_mid = plot.top() + plot.height() * 0.48

        ocean_rect = QRectF(gx, plot.top() + plot.height() * 0.22, plot.right() - gx - 22, plot.height() * 0.48)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(120, 210, 245, 88))
        painter.drawRect(ocean_rect)

        bed = QPainterPath()
        bed.moveTo(plot.left(), plot.bottom() - 68)
        bed.cubicTo(plot.left() + plot.width() * 0.35, plot.bottom() - 60, gx + 70, plot.bottom() - 84, plot.right(), plot.bottom() - 96 - bed_slope * 11)
        bed.lineTo(plot.right(), plot.bottom())
        bed.lineTo(plot.left(), plot.bottom())
        bed.closeSubpath()
        painter.setBrush(QColor(174, 126, 78, 194))
        painter.drawPath(bed)

        grounded = QRectF(plot.left() + 26, shelf_mid - 58, gx - plot.left() - 26, 112)
        painter.setPen(QPen(QColor(0, 55, 160), 2))
        painter.setBrush(QColor(35, 118, 213, 230))
        painter.drawRect(grounded)

        shelf_rect = QRectF(gx, shelf_mid - shelf_thick / 2, max(0, remaining_length), shelf_thick)
        painter.setPen(QPen(QColor(70, 170, 220), 2))
        painter.setBrush(QColor(180, 239, 252, 220))
        painter.drawRect(shelf_rect)
        if calving > 0:
            removed = QRectF(shelf_end, shelf_mid - 42, shelf_full_length - remaining_length, 84)
            painter.setPen(QPen(QColor(120, 120, 120), 1.6, Qt.DashLine))
            painter.setBrush(QColor(150, 150, 150, 38))
            painter.drawRect(removed)
            self._draw_tag(painter, removed.left() + 8, removed.top() - 34, "calved / lost shelf area", "#777777", 170)

        painter.setPen(QPen(QColor(220, 20, 35), 3, Qt.DashLine))
        painter.drawLine(QPointF(gx, shelf_mid - 92), QPointF(gx, shelf_mid + 112))
        self._draw_tag(painter, gx - 60, shelf_mid - 128, "Grounding line", "#ef4444", 118)

        if remaining_length > 24 and pinning > 0:
            pin_x = gx + remaining_length * 0.58
            pin_radius = 18 + 28 * pinning_factor
            painter.setPen(QPen(QColor(120, 70, 35), 2))
            painter.setBrush(QColor(155, 95, 45, 225))
            painter.drawEllipse(QPointF(pin_x, shelf_mid + 74), pin_radius, pin_radius * 0.62)
            self._draw_tag(painter, pin_x - 54, shelf_mid + 98, "pinning point", "#996633", 108)

        if lateral > 0:
            wall_alpha = 42 + int(90 * lateral_factor)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(64, 99, 135, wall_alpha))
            painter.drawRect(QRectF(gx, shelf_mid - 84, max(16, remaining_length), 14))
            painter.drawRect(QRectF(gx, shelf_mid + 70, max(16, remaining_length), 14))
            self._draw_tag(painter, gx + max(20, remaining_length * 0.22), shelf_mid - 122, "lateral confinement", "#406387", 150)

        speed = self._clip((velocity_myr - 180) / 950, 0.15, 1)
        for i in range(6):
            y = shelf_mid - 36 + i * 14
            x0 = plot.left() + 66 + i * 26
            x1 = min(gx - 8, x0 + 42 + speed * 70)
            self._draw_arrow(painter, QPointF(x0, y), QPointF(x1, y), QColor(255, 140, 40), 2.4 + 3.2 * speed)

        backstress = self._clip(buttressing / 100)
        for i in range(4):
            y = shelf_mid - 32 + i * 22
            start = QPointF(gx + 16 + 96 * backstress, y)
            end = QPointF(gx - 10 - 62 * backstress, y)
            self._draw_arrow(painter, start, end, QColor(40, 90, 190, 105 + int(100 * backstress)), 2 + 3 * backstress)

        if ocean_factor > 0.02:
            heat = QRadialGradient(QPointF(gx + plot.width() * 0.25, shelf_mid + 86), 70 + 90 * ocean_factor)
            heat.setColorAt(0, QColor(255, 92, 34, 150))
            heat.setColorAt(0.56, QColor(255, 169, 54, 65))
            heat.setColorAt(1, QColor(255, 169, 54, 0))
            painter.setBrush(heat)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(gx + plot.width() * 0.25, shelf_mid + 86), 100, 36)

        self._draw_tag(painter, plot.left() + 44, grounded.top() - 40, "Grounded ice", "#167ef8", 112)
        self._draw_tag(painter, gx + 42, shelf_rect.top() - 42, "Floating ice shelf", "#4aaad8", 132)
        self._draw_tag(painter, plot.right() - 128, ocean_rect.bottom() - 30, "Ocean", "#238ad2", 86)
        painter.setPen(QColor("#1f2937"))
        painter.setFont(ui_font(13, QFont.Bold))
        painter.drawText(QRectF(plot.left() + 18, plot.top() + 16, plot.width() - 36, 28), "Conceptual Ice Shelf Buttressing Experiment")
        panel = QRectF(plot.right() - 284, plot.bottom() - 96, 250, 70)
        painter.setPen(QPen(QColor(195, 213, 226), 1))
        painter.setBrush(QColor(255, 255, 255, 222))
        painter.drawRoundedRect(panel, 14, 14)
        self._draw_bar(painter, QRectF(panel.left() + 16, panel.top() + 28, panel.width() - 32, 10), "Buttressing index", buttressing / 100, QColor("#2563eb"))
        self._draw_bar(painter, QRectF(panel.left() + 16, panel.top() + 56, panel.width() - 32, 10), "Calving + ocean forcing", self._clip(calving_factor * 0.65 + ocean_factor * 0.35), QColor("#f97316"))

    def _draw_hydrofracture(self, painter, rect):
        plot = rect.adjusted(28, 36, -28, -30)
        ocean = QLinearGradient(plot.topLeft(), plot.bottomRight())
        ocean.setColorAt(0, QColor("#0b3763"))
        ocean.setColorAt(1, QColor("#061f42"))
        painter.fillRect(plot, ocean)
        painter.setPen(QPen(QColor(255, 255, 255, 24), 1))
        for i in range(6):
            y = plot.top() + 36 + i * 42
            painter.drawLine(QPointF(plot.left() + 24, y), QPointF(plot.right() - 24, y + 12))

        stage = int(self._clip(self._number("stage", 2), 0, 4))
        auto_stage = int(self._clip(self._number("auto_stage", stage), 0, 4))
        ponding = self._clip(self._number("ponding", 0.4))
        fracture = self._clip(self._number("fracture", 0.35))
        collapse_risk = self._clip(self._number("collapse_risk", 40) / 100)
        buttressing_remaining = self._clip(self._number("buttressing_remaining", 60) / 100)
        velocity_myr = self._number("post_collapse_velocity", 900)
        stage_labels = [
            "0 Intact shelf",
            "1 Melt ponds form",
            "2 Water-filled cracks deepen",
            "3 Shelf fragments",
            "4 Breakup and flow acceleration",
        ]

        shelf_y0 = plot.top() + plot.height() * 0.34
        shelf_h = plot.height() * 0.26
        shelf_x0 = plot.left() + plot.width() * 0.12
        shelf_x1 = plot.right() - plot.width() * 0.08
        shelf = QRectF(shelf_x0, shelf_y0, shelf_x1 - shelf_x0, shelf_h)

        if stage < 3:
            painter.setBrush(QColor(190, 240, 255, 235))
            painter.setPen(QPen(QColor(120, 220, 250), 2))
            painter.drawRoundedRect(shelf, 10, 10)
        else:
            blocks = [
                (0.00, 0.20, 0.03, -0.04),
                (0.24, 0.17, -0.02, 0.06),
                (0.45, 0.18, 0.05, -0.03),
                (0.67, 0.17, -0.05, 0.04),
                (0.87, 0.13, 0.04, -0.06),
            ]
            painter.setPen(QPen(QColor(165, 220, 235), 2))
            painter.setBrush(QColor(200, 245, 255, 198))
            for start, width, dy_top, dy_bottom in blocks:
                block = QRectF(
                    shelf.left() + shelf.width() * start,
                    shelf.top() + shelf.height() * dy_top,
                    shelf.width() * width,
                    shelf.height() * (0.86 + dy_bottom),
                )
                painter.drawRoundedRect(block, 6, 6)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(5, 35, 75, 226))
            for gx in [0.21, 0.43, 0.64, 0.82]:
                painter.drawRect(QRectF(shelf.left() + shelf.width() * gx, shelf.top() - 8, 8, shelf.height() + 22))

        grounded = QRectF(plot.left() + 28, shelf.top() - 16, plot.width() * 0.12, shelf.height() + 32)
        painter.setBrush(QColor(40, 120, 215, 235))
        painter.setPen(QPen(QColor(0, 65, 160), 2))
        painter.drawRect(grounded)

        pond_positions = [
            (0.20, 0.22, 28, 9),
            (0.36, 0.42, 34, 10),
            (0.52, 0.24, 31, 9),
            (0.68, 0.45, 35, 11),
            (0.82, 0.26, 28, 8),
        ]
        n_ponds = int(max(0, min(len(pond_positions), round(ponding * len(pond_positions) + (2 if stage >= 1 else 0)))))
        if stage >= 1:
            painter.setBrush(QColor(0, 120, 255, 196))
            painter.setPen(QPen(QColor(0, 95, 210), 2))
            for px, py, w, h in pond_positions[:n_ponds]:
                painter.drawEllipse(QPointF(shelf.left() + shelf.width() * px, shelf.top() + shelf.height() * py), w, h)

        crack_xs = [0.21, 0.37, 0.54, 0.70, 0.84]
        if stage >= 2:
            crack_count = max(2, min(5, int(2 + self._number("crevasse", 40) / 25)))
            painter.setPen(QPen(QColor(220, 20, 35), 4 + stage, Qt.SolidLine, Qt.RoundCap))
            crack_depth = shelf.height() * (0.45 + fracture * 0.75) + stage * 4
            for i, frac in enumerate(crack_xs[:crack_count]):
                x = shelf.left() + shelf.width() * frac
                path = QPainterPath()
                path.moveTo(x, shelf.top() + 8)
                path.lineTo(x + 7 * sin(i + 1), shelf.top() + 22 + crack_depth * 0.35)
                path.lineTo(x - 6 * cos(i + 0.5), min(shelf.bottom() + 22, shelf.top() + 16 + crack_depth))
                painter.drawPath(path)

        if stage >= 4:
            center = QPointF(shelf.center().x(), shelf.center().y())
            painter.setPen(QPen(QColor(255, 255, 255, 175), 2))
            for i in range(18):
                angle = (2 * pi * i) / 18
                inner = QPointF(center.x() + 10 * cos(angle), center.y() + 10 * sin(angle))
                outer = QPointF(center.x() + (54 + 10 * sin(angle * 3)) * cos(angle), center.y() + (34 + 6 * cos(angle * 2)) * sin(angle))
                painter.drawLine(inner, outer)
            painter.setPen(QColor("#ff463d"))
            painter.setFont(ui_font(18, QFont.Bold))
            painter.drawText(QRectF(shelf.left(), shelf.center().y() - 16, shelf.width(), 34), Qt.AlignCenter, "ICE SHELF BREAKUP")

        speed = self._clip((velocity_myr - 300) / 1800, 0.15, 1)
        for i in range(5):
            y = grounded.top() + 18 + i * (grounded.height() - 36) / 4
            self._draw_arrow(painter, QPointF(plot.left() + 36, y), QPointF(grounded.right() + 32 + 72 * speed, y), QColor(255, 140, 35), 2.5 + 5 * speed)

        painter.setPen(QColor("#ffffff"))
        painter.setFont(ui_font(15, QFont.Bold))
        painter.drawText(QRectF(plot.left(), plot.top() + 24, plot.width(), 34), Qt.AlignCenter, stage_labels[stage])
        self._draw_tag(painter, grounded.left() - 4, grounded.top() - 40, "Grounded ice", "#167ef8", 112)
        self._draw_tag(painter, shelf.center().x() - 76, shelf.top() - 42, "Floating ice shelf", "#4aaad8", 142)
        self._draw_tag(painter, plot.right() - 132, plot.bottom() - 54, "Ocean", "#238ad2", 86)
        if stage >= 1:
            self._draw_tag(painter, shelf.left() + 32, shelf.top() + 16, "melt ponds", "#0078ff", 104)
        if stage >= 2:
            self._draw_tag(painter, shelf.left() + shelf.width() * 0.62, shelf.bottom() + 14, "hydrofracture", "#dc1423", 124)

        panel = QRectF(plot.right() - 284, plot.bottom() - 116, 250, 92)
        painter.setPen(QPen(QColor(126, 220, 255, 70), 1))
        painter.setBrush(QColor(6, 25, 52, 218))
        painter.drawRoundedRect(panel, 14, 14)
        self._draw_bar(painter, QRectF(panel.left() + 16, panel.top() + 42, panel.width() - 32, 10), "Collapse risk", collapse_risk, QColor("#ef4444"), "#eaf6ff")
        self._draw_bar(painter, QRectF(panel.left() + 16, panel.top() + 72, panel.width() - 32, 10), "Buttressing remaining", buttressing_remaining, QColor("#38bdf8"), "#eaf6ff")
        painter.setPen(QColor("#eaf6ff"))
        painter.setFont(ui_font(8, QFont.Bold))
        painter.drawText(QRectF(panel.left() + 16, panel.top() + 7, panel.width() - 32, 18), f"Auto stage {auto_stage} / displayed stage {stage}")


class CompassPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(390)
        self.mode = "Compass"
        self.direction = "Ocean heat pathways"
        self.direction_info = dict(DIRECTION_DATA[self.direction])
        self.all_directions = DIRECTION_DATA

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def set_direction(self, name, info=None, all_directions=None):
        self.direction = name
        self.direction_info = dict(info or DIRECTION_DATA.get(name, DIRECTION_DATA["Ocean heat pathways"]))
        self.all_directions = all_directions or DIRECTION_DATA
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0, 0, -1, -1)
        painter.setBrush(QColor(9, 18, 34, 215))
        painter.setPen(QPen(QColor(210, 238, 255, 52), 1.2))
        painter.drawRoundedRect(rect, 18, 18)
        if self.mode == "Timeline":
            self._draw_timeline(painter, rect)
            return
        if self.mode == "Region map":
            self._draw_region_map(painter, rect)
            return
        if self.mode == "Proposal builder":
            self._draw_proposal_builder(painter, rect)
            return
        plot = rect.adjusted(72, 42, -82, -56)
        painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
        for i in range(6):
            y = plot.top() + i * plot.height() / 5
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            x = plot.left() + i * plot.width() / 5
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
        painter.fillRect(QRectF(plot.left() + plot.width() * 0.5, plot.top(), plot.width() * 0.5, plot.height() * 0.52), QColor(140, 92, 40, 34))
        painter.fillRect(QRectF(plot.left(), plot.top(), plot.width() * 0.5, plot.height() * 0.52), QColor(20, 64, 95, 58))
        directions = self.all_directions or DIRECTION_DATA
        label_offsets = {
            "Ocean heat pathways": QPointF(22, -66),
            "Grounding-line instability": QPointF(-118, -68),
            "Ice-shelf fracture and calving": QPointF(-122, -22),
            "Subglacial water and basal sliding": QPointF(34, 24),
            "Solid-Earth feedbacks": QPointF(-138, 18),
            "Paleo constraints for future projections": QPointF(-170, -6),
            "AI-assisted Antarctic research": QPointF(-162, 30),
        }
        bubble_points = []
        for label, meta in directions.items():
            fx = max(0.04, min(0.96, (meta["uncertainty"] - 35) / 65))
            fy = max(0.06, min(0.94, 1 - ((meta["impact"] - 65) / 35)))
            selected = label == self.direction
            radius = 15 + meta["impact"] * 0.18
            pos = QPointF(plot.left() + plot.width() * fx, plot.top() + plot.height() * fy)
            color = QColor(58, 165, 224, 220 if selected else 118)
            if meta["observability"] < 55:
                color = QColor(220, 230, 238, 190 if selected else 135)
            elif meta["observability"] > 75:
                color = QColor(96, 205, 255, 225 if selected else 145)
            painter.setBrush(color)
            painter.setPen(QPen(QColor("#ffffff"), 4 if selected else 1))
            painter.drawEllipse(pos, radius, radius)
            bubble_points.append((label, meta, pos, radius, selected))

        painter.setPen(QColor(255, 255, 255, 205))
        painter.setFont(ui_font(9, QFont.Bold))
        painter.drawText(QRectF(plot.left() + plot.width() * 0.52, plot.top() + 22, 360, 30), "High impact + high uncertainty = frontier zone")

        for label, meta, pos, radius, selected in bubble_points:
            offset = label_offsets.get(label, QPointF(-92, -radius - 30))
            width = 196 if selected else 184
            height = 42 if selected else 34
            label_rect = QRectF(pos.x() + offset.x(), pos.y() + offset.y(), width, height)
            label_rect.moveLeft(max(plot.left() + 8, min(label_rect.left(), plot.right() - label_rect.width() - 8)))
            label_rect.moveTop(max(plot.top() + 8, min(label_rect.top(), plot.bottom() - label_rect.height() - 8)))
            anchor = QPointF(
                label_rect.left() if label_rect.center().x() > pos.x() else label_rect.right(),
                label_rect.center().y(),
            )
            painter.setPen(QPen(QColor(210, 238, 255, 82), 1))
            painter.drawLine(pos, anchor)
            painter.setBrush(QColor(2, 6, 23, 150 if selected else 110))
            painter.setPen(QPen(QColor(255, 255, 255, 118 if selected else 62), 1))
            painter.drawRoundedRect(label_rect, 8, 8)
            painter.setPen(QColor("#ffffff"))
            painter.setFont(ui_font(8 if selected else 7, QFont.Bold if selected else QFont.Normal))
            painter.drawText(label_rect.adjusted(7, 3, -7, -3), Qt.AlignCenter | Qt.TextWordWrap, label)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(ui_font(8))
        painter.drawText(QRectF(plot.left(), plot.top() - 28, 220, 24), "Sea-level impact")
        painter.drawText(QRectF(plot.center().x() - 90, plot.bottom() + 22, 180, 24), Qt.AlignCenter, "Scientific uncertainty")
        painter.drawText(QRectF(plot.right() - 168, plot.bottom() - 34, 160, 28), Qt.AlignRight, "Directly observable")
        legend = QRectF(plot.right() + 20, plot.top() + 18, 18, plot.height() - 54)
        gradient = QLinearGradient(legend.bottomLeft(), legend.topLeft())
        gradient.setColorAt(0, QColor(220, 230, 238))
        gradient.setColorAt(0.55, QColor(58, 165, 224))
        gradient.setColorAt(1, QColor(96, 205, 255))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(255, 255, 255, 82), 1))
        painter.drawRoundedRect(legend, 7, 7)
        painter.setPen(QColor(220, 236, 248, 210))
        painter.setFont(ui_font(7, QFont.Bold))
        painter.drawText(QRectF(legend.left() - 32, legend.top() - 28, 82, 22), Qt.AlignCenter, "Observability")
        painter.setFont(ui_font(7))
        painter.drawText(QRectF(legend.right() + 6, legend.top() - 6, 36, 16), "High")
        painter.drawText(QRectF(legend.right() + 6, legend.bottom() - 10, 36, 16), "Low")

    def _draw_timeline(self, painter, rect):
        plot = rect.adjusted(70, 48, -70, -64)
        info = self.direction_info
        painter.setPen(QColor("#f8fbff"))
        painter.setFont(ui_font(18, QFont.Bold))
        painter.drawText(QRectF(rect.left() + 28, rect.top() + 20, rect.width() - 56, 34), f"{self.direction} research pathway")
        painter.setPen(QPen(QColor(126, 220, 255, 150), 3, Qt.SolidLine, Qt.RoundCap))
        y = plot.center().y()
        painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
        events = [
            ("Past evidence", 0.08, "Use paleo records to test whether the mechanism happened before."),
            ("Present observation", 0.30, "Use satellites, field data, and process observations to identify active signals."),
            ("Process model", 0.52, f"Represent the mechanism with {', '.join(info['methods'][:2])}."),
            ("Coupled projection", 0.74, f"Connect the mechanism to uncertainty: {info['gap']}"),
            ("Research product", 0.93, "Turn the result into a map, figure, interactive tool, or proposal."),
        ]
        for label, frac, detail in events:
            x = plot.left() + plot.width() * frac
            painter.setBrush(QColor(78, 163, 241, 190))
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawEllipse(QPointF(x, y), 20, 20)
            painter.setPen(QColor("#ffffff"))
            painter.setFont(ui_font(10, QFont.Bold))
            painter.drawText(QRectF(x - 90, y - 68, 180, 24), Qt.AlignCenter, label)
            painter.setFont(ui_font(9))
            painter.setPen(QColor(220, 236, 248, 205))
            painter.drawText(QRectF(x - 95, y + 34, 190, 56), Qt.AlignHCenter | Qt.TextWordWrap, detail)

    def _draw_region_map(self, painter, rect):
        info = self.direction_info
        painter.setPen(QColor("#f8fbff"))
        painter.setFont(ui_font(18, QFont.Bold))
        painter.drawText(QRectF(rect.left() + 28, rect.top() + 24, rect.width() - 56, 30), "Conceptual Region Map")
        map_rect = rect.adjusted(90, 74, -90, -52)
        ocean = QLinearGradient(map_rect.topLeft(), map_rect.bottomRight())
        ocean.setColorAt(0, QColor("#0b3555"))
        ocean.setColorAt(1, QColor("#061527"))
        painter.setBrush(ocean)
        painter.setPen(QPen(QColor(210, 238, 255, 45), 1))
        painter.drawRoundedRect(map_rect, 18, 18)
        antarctica = QPainterPath()
        antarctica.moveTo(map_rect.center().x() - 170, map_rect.center().y() + 40)
        antarctica.cubicTo(map_rect.center().x() - 90, map_rect.top() + 80, map_rect.center().x() + 110, map_rect.top() + 62, map_rect.center().x() + 180, map_rect.center().y() + 20)
        antarctica.cubicTo(map_rect.center().x() + 112, map_rect.bottom() - 60, map_rect.center().x() - 40, map_rect.bottom() - 40, map_rect.center().x() - 170, map_rect.center().y() + 40)
        painter.setBrush(QColor(228, 245, 255, 215))
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawPath(antarctica)
        colors = ["#FF8A65", "#4EA3F1", "#F6C85F", "#9CCC65"]
        for index, name in enumerate(info["regions"]):
            lat, lon = DIRECTION_REGION_COORDS.get(name, (-75, 0))
            fx = max(0.12, min(0.88, 0.5 + lon / 360))
            fy = max(0.16, min(0.84, 0.52 + (lat + 75) / 70))
            color = colors[index % len(colors)]
            p = QPointF(map_rect.left() + map_rect.width() * fx, map_rect.top() + map_rect.height() * fy)
            painter.setBrush(QColor(color))
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawEllipse(p, 12, 12)
            painter.setPen(QColor("#ffffff"))
            painter.setFont(ui_font(9, QFont.Bold))
            painter.drawText(QRectF(p.x() + 14, p.y() - 10, 190, 26), name)
        painter.setPen(QColor(220, 236, 248, 205))
        painter.setFont(ui_font(9))
        painter.drawText(QRectF(map_rect.left() + 22, map_rect.bottom() - 42, map_rect.width() - 44, 28), Qt.AlignCenter, "Conceptual locator for research planning, not a precise GIS layer.")

    def _draw_proposal_builder(self, painter, rect):
        info = self.direction_info
        question = info.get("active_question") or info["starter_questions"][0]
        methods = info.get("active_methods") or info["methods"][:2]
        regions = info.get("active_regions") or info["regions"][:2]
        ambition = info.get("active_ambition", 3)
        ambition_text = {
            1: "a small class-project style literature synthesis",
            2: "a focused exploratory analysis",
            3: "a feasible undergraduate research proposal",
            4: "an ambitious portfolio project with visualization or modeling",
            5: "a high-end PhD-style frontier proposal",
        }.get(ambition, "a feasible undergraduate research proposal")
        painter.setPen(QColor("#f8fbff"))
        painter.setFont(ui_font(18, QFont.Bold))
        painter.drawText(QRectF(rect.left() + 28, rect.top() + 24, rect.width() - 56, 30), "Generated Research Proposal Seed")
        box = rect.adjusted(36, 78, -36, -36)
        painter.setBrush(QColor(255, 255, 255, 18))
        painter.setPen(QPen(QColor(210, 238, 255, 56), 1))
        painter.drawRoundedRect(box, 16, 16)
        proposal = (
            f"Title: {self.direction}: {question}\n\n"
            f"Research style: {ambition_text}\n\n"
            "Motivation:\n"
            f"{info['why_now']}\n\n"
            "Knowledge gap:\n"
            f"{info['gap']}\n\n"
            "Possible approach:\n"
            f"Use {', '.join(methods)} focused on {', '.join(regions)}. The goal is to connect mechanism, observation, and uncertainty rather than only summarize the paper.\n\n"
            "Expected output:\n"
            "1. A concept map of the mechanism.\n"
            "2. A small evidence table linking observations to physical interpretation.\n"
            "3. A visual figure or interactive module that explains the research direction.\n"
            "4. A short uncertainty paragraph explaining what remains unknown.\n\n"
            "Why this fits your Atlas:\n"
            f"{info['student_angle']}"
        )
        painter.setPen(QColor(245, 250, 255, 220))
        painter.setFont(ui_font(9))
        painter.drawText(box.adjusted(22, 20, -22, -20), Qt.TextWordWrap, proposal)


class NativeAtlasWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        localize_runtime_globals(globals())
        self.pages = []
        self._main_ready = False
        self._main_building = False
        self._landing_progress_value = 0.0
        self._landing_progress_phase = 0
        self._landing_progress_cap = 82
        self._prepare_worker = None
        self._shutting_down = False
        self._page_builders = []
        self._page_widgets = []
        self._stack_fade = None
        self._stack_fade_label = None
        self._entering_project = False
        self.setWindowTitle(t("app.title", APP_TITLE))
        self.setMinimumSize(980, 680)
        icon_path = _application_icon_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        available = QApplication.primaryScreen().availableGeometry() if QApplication.primaryScreen() else None
        if available:
            width = min(1320, max(900, int(available.width() * 0.92)), available.width())
            height = min(860, max(680, int(available.height() * 0.90)), available.height())
            self.resize(width, height)
        else:
            self.resize(1320, 860)
        self._build_ui()
        self._build_app_menu()
        self._landing_progress_timer = QTimer(self)
        self._landing_progress_timer.setTimerType(Qt.PreciseTimer)
        self._landing_progress_timer.timeout.connect(self._tick_landing_progress)
        self._landing_progress_timer.start(33)
        QTimer.singleShot(350, self._prepare_main_app)

    def _load_data(self):
        return load_pdf_pages(PDF_PATH)

    def _build_app_menu(self):
        is_zh = current_locale().startswith("zh")
        app_menu = self.menuBar().addMenu("帮助" if is_zh else "Help")
        about_action = QAction("关于 Antarctic Atlas" if is_zh else "About Antarctic Atlas", self)
        about_action.triggered.connect(self._show_about_dialog)
        releases_action = QAction("查看 GitHub Releases" if is_zh else "GitHub Releases", self)
        releases_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/OmicaChow/antarctic-atlas/releases"))
        )
        issues_action = QAction("报告问题" if is_zh else "Report an Issue", self)
        issues_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/OmicaChow/antarctic-atlas/issues"))
        )
        app_menu.addAction(about_action)
        app_menu.addSeparator()
        app_menu.addAction(releases_action)
        app_menu.addAction(issues_action)

    def _show_about_dialog(self):
        is_zh = current_locale().startswith("zh")
        if is_zh:
            text = (
                f"<h3>Antarctic Atlas {APP_VERSION}</h3>"
                "<p>面向 Apple Silicon 的南极冰盖论文探索工具。</p>"
                "<p>内置论文：Noble et al. (2020)，DOI 10.1029/2019RG000663，"
                "按 Creative Commons Attribution License 提供。</p>"
                "<p>纯证据模式不联网；选择在线 AI 服务时，问题和检索段落会发送给所选服务商。API 密钥仅保留在本次运行中。</p>"
            )
        else:
            text = (
                f"<h3>Antarctic Atlas {APP_VERSION}</h3>"
                "<p>An Apple Silicon explorer for an Antarctic Ice Sheet review paper.</p>"
                "<p>Included paper: Noble et al. (2020), DOI 10.1029/2019RG000663, "
                "provided under the Creative Commons Attribution License.</p>"
                "<p>Evidence-only mode stays offline. When an online AI provider is selected, the question and retrieved passages are sent to that provider. API keys remain in memory for this run only.</p>"
            )
        QMessageBox.about(self, "关于 Antarctic Atlas" if is_zh else "About Antarctic Atlas", text)

    def _build_ui(self):
        self.shell = QStackedWidget()
        self.shell.setObjectName("Shell")
        self.shell.addWidget(self._landing_page())
        self.setCentralWidget(self.shell)
        self._apply_styles()

    def _landing_page(self):
        page = QWidget()
        page.setObjectName("LandingRoot")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 28, 24, 28)
        outer.setSpacing(0)
        outer.addStretch(1)

        card = Card()
        card.setObjectName("LandingCard")
        card.setMaximumWidth(860)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(58, 56, 58, 56)
        layout.setSpacing(20)

        title = QLabel(t("landing.title", "🌎 Antarctic Ice Sheet Research Atlas"))
        title.setObjectName("LandingTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        title.setMinimumHeight(64)
        subtitle = QLabel(t("landing.subtitle", "An interactive research universe for exploring the Antarctic Ice Sheet review paper."))
        subtitle.setObjectName("LandingSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        status = QLabel(t("landing.status.initial", "Loading atlas workspace..."))
        status.setObjectName("LandingStatus")
        status.setAlignment(Qt.AlignCenter)
        self.landing_status = status
        progress = QProgressBar()
        progress.setObjectName("LandingProgress")
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setFixedWidth(320)
        self.landing_progress = progress
        enter = QPushButton(t("landing.button.enter", "Enter Project"))
        enter.setObjectName("EnterButton")
        enter.setMinimumSize(150, 46)
        enter.setEnabled(False)
        enter.setVisible(False)
        enter.clicked.connect(self._enter_project)
        self.enter_button = enter

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(status, 0, Qt.AlignCenter)
        layout.addWidget(progress, 0, Qt.AlignCenter)
        layout.addWidget(enter, 0, Qt.AlignCenter)
        outer.addWidget(card, 0, Qt.AlignCenter)
        outer.addStretch(1)
        return localize_widget_tree(page)

    def _tick_landing_progress(self):
        if not hasattr(self, "landing_progress") or self._main_ready:
            return
        self._landing_progress_phase += 1
        cap = self._landing_progress_cap
        remaining = max(0.25, cap - self._landing_progress_value)
        wave = 0.5 + 0.5 * sin(self._landing_progress_phase / 13)
        step = min(0.48, max(0.035, remaining * 0.006 + wave * 0.08))
        self._landing_progress_value = min(cap, self._landing_progress_value + step)
        self.landing_progress.setValue(int(self._landing_progress_value))

    def _prepare_main_app(self):
        if self._shutting_down or self._main_ready or self._main_building:
            return
        self._main_building = True
        try:
            if hasattr(self, "landing_status"):
                self.landing_status.setText(t("landing.status.loading_modules", "Loading paper evidence and visual modules..."))
            if hasattr(self, "landing_progress"):
                self._landing_progress_cap = 84
                self._landing_progress_value = max(self._landing_progress_value, 12)
                self.landing_progress.setValue(int(self._landing_progress_value))
            self._prepare_worker = FunctionWorker(self._load_data)
            self._prepare_worker.resultReady.connect(self._on_pages_loaded)
            self._prepare_worker.errorReady.connect(self._on_prepare_failed)
            self._prepare_worker.finished.connect(self._prepare_worker.deleteLater)
            self._prepare_worker.start()
        except Exception as exc:
            self._on_prepare_failed(str(exc))

    def _on_pages_loaded(self, pages):
        if self._shutting_down:
            return
        self.pages = pages
        if hasattr(self, "landing_status"):
            self.landing_status.setText(t("landing.status.preparing_workspace", "Preparing interactive workspace..."))
        if hasattr(self, "landing_progress"):
            self._landing_progress_cap = 94
            self._landing_progress_value = max(self._landing_progress_value, 62)
            self.landing_progress.setValue(int(self._landing_progress_value))
        QTimer.singleShot(30, self._finish_prepare_main_app)

    def _finish_prepare_main_app(self):
        if self._shutting_down:
            self._main_building = False
            return
        try:
            self.shell.addWidget(self._main_app())
            self._ensure_page_built(0)
            self.stack.setCurrentIndex(0)
            self._main_ready = True
            if hasattr(self, "landing_status"):
                self.landing_status.setText(t("landing.status.loaded", "PDF loaded successfully, {pages} pages", pages=len(self.pages)))
            if hasattr(self, "landing_progress"):
                self._landing_progress_cap = 100
                self._landing_progress_value = 100
                self.landing_progress.setValue(100)
                self.landing_progress.setVisible(False)
            if hasattr(self, "_landing_progress_timer"):
                self._landing_progress_timer.stop()
            if hasattr(self, "enter_button"):
                self.enter_button.setText(t("landing.button.enter", "Enter Project"))
                self.enter_button.setEnabled(True)
                self.enter_button.setVisible(True)
        except Exception as exc:
            self._on_prepare_failed(str(exc))
        finally:
            self._main_building = False

    def _on_prepare_failed(self, message):
        if self._shutting_down:
            self._main_building = False
            return
        if hasattr(self, "_landing_progress_timer"):
            self._landing_progress_timer.stop()
        if hasattr(self, "landing_status"):
            self.landing_status.setText(t("landing.status.failed", "Atlas preparation failed: {message}", message=message))
        if hasattr(self, "landing_progress"):
            self.landing_progress.setVisible(False)
        if hasattr(self, "enter_button"):
            self.enter_button.setText(t("landing.button.retry", "Retry"))
            self.enter_button.setEnabled(True)
            self.enter_button.setVisible(True)
        self._main_building = False

    def _enter_project(self):
        if self._entering_project:
            return
        if not self._main_ready:
            if hasattr(self, "landing_status"):
                self.landing_status.setText(t("landing.status.still_preparing", "Still preparing the atlas workspace..."))
            self._prepare_main_app()
        if self._main_ready:
            self._entering_project = True
            if hasattr(self, "enter_button"):
                self.enter_button.setEnabled(False)
            self.shell.setCurrentIndex(1)
            QTimer.singleShot(0, self._finish_enter_transition)

    def _finish_enter_transition(self):
        self._entering_project = False
        if hasattr(self, "enter_button"):
            self.enter_button.setEnabled(True)

    def _fade_in_widget(self, widget, duration=180, pixmap=None):
        if not widget or not hasattr(self, "stack"):
            return
        pixmap = pixmap or self.stack.grab()
        if pixmap.isNull():
            return
        if self._stack_fade_label:
            self._stack_fade_label.deleteLater()
            self._stack_fade_label = None
        label = QLabel(self.stack)
        label.setPixmap(pixmap)
        label.setGeometry(self.stack.rect())
        label.setScaledContents(True)
        label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        label.show()
        label.raise_()
        effect = QGraphicsOpacityEffect(label)
        label.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.OutQuart)
        animation.finished.connect(lambda label=label: label.deleteLater())
        animation.finished.connect(lambda: setattr(self, "_stack_fade_label", None))
        self._stack_fade = animation
        self._stack_fade_label = label
        animation.start()

    def _main_app(self):
        root = QWidget()
        root.setObjectName("Root")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(270)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 72, 20, 18)
        sidebar_layout.setSpacing(12)

        brand = QLabel(t("nav.brand", "Navigation"))
        brand.setObjectName("Brand")
        section = QLabel(t("nav.section", "Select"))
        section.setObjectName("SidebarCaption")

        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        self.nav.setAccessibleName(t("nav.brand", "Navigation"))
        self.nav.setFixedWidth(220)
        self.nav_labels = [
            t("nav.research_universe", "Research Universe"),
            t("nav.antarctic_system", "Antarctic System"),
            t("nav.ai_visualizer", "AI Visualizer"),
            t("nav.mini_research_lab", "Mini Research Lab"),
            t("nav.research_directions", "Research Directions"),
            t("nav.raw_paper", "Read Raw Paper"),
        ]
        for label in self.nav_labels:
            item = QListWidgetItem(label)
            item.setSizeHint(QSize(220, 34))
            self.nav.addItem(item)

        language_label = QLabel(t("nav.language", "Language"))
        language_label.setObjectName("SidebarCaption")
        self.language_combo = QComboBox()
        self.language_combo.setAccessibleName(t("nav.language", "Language"))
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("中文", "zh")
        active_locale = "zh" if current_locale().startswith("zh") else "en"
        for index in range(self.language_combo.count()):
            if self.language_combo.itemData(index) == active_locale:
                self.language_combo.setCurrentIndex(index)
                break
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)

        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(section)
        sidebar_layout.addWidget(self.nav, 1)
        sidebar_layout.addWidget(language_label)
        sidebar_layout.addWidget(self.language_combo)

        self.stack = QStackedWidget()
        self.stack.setObjectName("Stack")
        self._page_builders = [
            self._research_universe_page,
            self._antarctic_system_page,
            self._ai_visualizer_page,
            self._mini_lab_page,
            self._research_directions_page,
            self._raw_paper_page,
        ]
        self._page_widgets = [None for _ in self._page_builders]
        for label in self.nav_labels:
            self.stack.addWidget(self._lazy_page_placeholder(label))

        self.nav.setCurrentRow(0)
        for index, label in enumerate(self.nav_labels):
            marker = ">" if index == 0 else " "
            self.nav.item(index).setText(f"{marker}  {label}")
        self.nav.currentRowChanged.connect(self._on_nav_changed)

        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        return localize_widget_tree(root)

    def _on_language_changed(self, _index):
        if not hasattr(self, "language_combo"):
            return
        selected = self.language_combo.currentData()
        active = "zh" if current_locale().startswith("zh") else "en"
        if not selected or selected == active:
            return
        set_locale(selected)
        restart_args = sys.argv if not getattr(sys, "frozen", False) else sys.argv[1:]
        detached = QProcess.startDetached(sys.executable, restart_args)
        started = bool(detached[0] if isinstance(detached, tuple) else detached)
        if not started:
            set_locale(active)
            self.language_combo.blockSignals(True)
            for index in range(self.language_combo.count()):
                if self.language_combo.itemData(index) == active:
                    self.language_combo.setCurrentIndex(index)
                    break
            self.language_combo.blockSignals(False)
            QMessageBox.warning(
                self,
                "无法切换语言" if current_locale().startswith("zh") else "Language switch failed",
                "无法重新启动 Antarctic Atlas，语言设置未更改。" if current_locale().startswith("zh") else "Antarctic Atlas could not restart, so the language setting was left unchanged.",
            )
            return
        QApplication.quit()

    def _running_workers(self):
        candidates = [getattr(self, "_prepare_worker", None)]
        candidates.extend(getattr(self, "_universe_workers", []) or [])
        running = []
        seen = set()
        for worker in candidates:
            if worker is None or id(worker) in seen:
                continue
            seen.add(id(worker))
            try:
                if worker.isRunning():
                    running.append(worker)
            except RuntimeError:
                continue
        return running

    def _shutdown_workers(self, timeout_ms=3000):
        self._shutting_down = True
        for timer in self.findChildren(QTimer):
            timer.stop()
        self._universe_answer_token = getattr(self, "_universe_answer_token", 0) + 1
        self._universe_classifier_token = getattr(self, "_universe_classifier_token", 0) + 1
        workers = self._running_workers()
        for worker in workers:
            worker.requestInterruption()
        deadline = time.monotonic() + max(0, timeout_ms) / 1000
        for worker in workers:
            remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
            try:
                worker.wait(remaining_ms)
            except RuntimeError:
                continue
        # A requests call can be blocked inside native networking code.  At
        # process shutdown only, make the last resort explicit so Qt never
        # destroys a live QThread and aborts the application.
        for worker in self._running_workers():
            try:
                worker.terminate()
                worker.wait(1000)
            except RuntimeError:
                continue

    def closeEvent(self, event):
        self._shutdown_workers()
        super().closeEvent(event)

    def _lazy_page_placeholder(self, label):
        page = QWidget()
        page.setObjectName("LazyPagePlaceholder")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addStretch(1)
        status = QLabel(t("placeholder.preparing", "Preparing {label}...", label=label))
        status.setObjectName("LazyPageStatus")
        status.setAlignment(Qt.AlignCenter)
        layout.addWidget(status, 0, Qt.AlignCenter)
        layout.addStretch(1)
        return localize_widget_tree(page)

    def _ensure_page_built(self, row):
        if row < 0 or row >= len(self._page_builders):
            return
        if self._page_widgets[row] is not None:
            return
        current_row = self.stack.currentIndex()
        old_widget = self.stack.widget(row)
        widget = self._page_builders[row]()
        localize_widget_tree(widget)
        self._page_widgets[row] = widget
        self.stack.removeWidget(old_widget)
        old_widget.deleteLater()
        self.stack.insertWidget(row, widget)
        if current_row == row:
            self.stack.setCurrentIndex(row)

    def _on_nav_changed(self, row):
        if row < 0:
            return
        old_widget = self.stack.widget(row) if hasattr(self, "stack") else None
        self._ensure_page_built(row)
        previous_widget = self.stack.currentWidget() if hasattr(self, "stack") else None
        next_widget = self.stack.widget(row) if hasattr(self, "stack") else None
        page_was_placeholder = old_widget is not next_widget
        heavy_transition = any(
            widget and widget.findChild(QWebEngineView)
            for widget in [previous_widget, next_widget]
        ) or page_was_placeholder
        previous_pixmap = QPixmap()
        if previous_widget and not heavy_transition:
            previous_pixmap = self.stack.grab()
        if self.stack.currentWidget():
            self.stack.currentWidget().setGraphicsEffect(None)
        self.stack.setCurrentIndex(row)
        if not heavy_transition:
            self._fade_in_widget(self.stack.currentWidget(), duration=160, pixmap=previous_pixmap)
        for index, label in enumerate(self.nav_labels):
            marker = ">" if index == row else " "
            self.nav.item(index).setText(f"{marker}  {label}")
        if row == 0:
            QTimer.singleShot(80, self._restore_universe_interaction)

    def _restore_universe_interaction(self):
        for name in [
            "universe_backend",
            "universe_model_combo",
            "universe_api_key",
            "universe_save_key",
            "universe_search",
            "universe_focus_button",
            "universe_passages_toggle",
            "universe_answer",
            "universe_evidence",
            "universe_passages",
        ]:
            widget = getattr(self, name, None)
            if widget:
                widget.setGraphicsEffect(None)
                widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
                if name not in ["universe_focus_button", "universe_save_key"]:
                    widget.setEnabled(True)
        if hasattr(self, "universe_focus_button") and not self._worker_is_running(getattr(self, "_universe_classifier_worker", None)):
            self.universe_focus_button.setEnabled(True)
        if hasattr(self, "universe_save_key") and not self._worker_is_running(getattr(self, "_universe_test_worker", None)):
            self.universe_save_key.setEnabled(True)
        if hasattr(self, "universe_map"):
            self.universe_map.setGraphicsEffect(None)
            self.universe_map.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.universe_map.setEnabled(True)

    def _page_shell(self, title, subtitle):
        scroll = QScrollArea()
        scroll.setObjectName("PageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setAttribute(Qt.WA_StaticContents, True)
        scroll.verticalScrollBar().setSingleStep(22)
        scroll.verticalScrollBar().setPageStep(180)
        page = QWidget()
        page.setObjectName("PageRoot")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(HeroHeader(title, subtitle))
        scroll.setWidget(page)
        return scroll, layout


















































































    def _apply_styles(self):
        stylesheet = """
            QMainWindow, QStackedWidget#Shell, QWidget#Root {
                background: #050816;
                color: #eef6ff;
                font-family: "__SYSTEM_UI_FONT__";
                font-size: 14px;
            }
            QWidget#LandingRoot {
                background: qradialgradient(cx:.24, cy:.22, radius:.92, fx:.24, fy:.22, stop:0 rgba(98,183,255,.24), stop:.30 rgba(8,18,33,.94), stop:.64 #07111f, stop:1 #020617);
            }
            QFrame#LandingCard {
                background: rgba(9, 20, 38, .72);
                border: 1px solid rgba(220, 242, 255, .30);
                border-radius: 38px;
            }
            QLabel#LandingTitle {
                color: #f8fbff;
                font-size: 36px;
                font-weight: 800;
            }
            QLabel#LandingSubtitle {
                color: rgba(238, 246, 255, .78);
                font-size: 16px;
            }
            QLabel#LandingStatus {
                padding: 12px 18px;
                border-radius: 999px;
                background: rgba(78, 163, 241, .14);
                border: 1px solid rgba(126, 220, 255, .28);
                color: #d9f4ff;
                font-weight: 650;
            }
            QProgressBar#LandingProgress {
                background: rgba(11, 23, 43, .72);
                border: 1px solid rgba(190, 226, 255, .22);
                border-radius: 999px;
                min-height: 12px;
                max-height: 12px;
                text-align: center;
            }
            QProgressBar#LandingProgress::chunk {
                border-radius: 999px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #73f0a2, stop:1 #5aa7ff);
            }
            QPushButton#EnterButton {
                border-radius: 23px;
                padding: 0 20px;
                background: #3b9cff;
                border: 1px solid rgba(170, 215, 255, .20);
                color: white;
                font-weight: 700;
            }
            QPushButton#EnterButton:hover {
                background: #57aaff;
                border: 1px solid rgba(210, 238, 255, .38);
            }
            QPushButton#EnterButton:disabled {
                background: rgba(78, 163, 241, .18);
                border: 1px solid rgba(190, 226, 255, .14);
                color: rgba(238, 246, 255, .46);
            }
            QWidget#Sidebar {
                background: rgba(7, 15, 30, .68);
                border-right: 1px solid rgba(220, 242, 255, .14);
            }
            QWidget#PageRoot {
                background: qradialgradient(cx:.18, cy:.12, radius:.75, fx:.18, fy:.12, stop:0 rgba(90, 167, 255, .18), stop:.34 rgba(7, 17, 31, .96), stop:1 #020617);
            }
            QScrollArea#PageScroll {
                border: 0;
                background: transparent;
                border-radius: 0;
            }
            QScrollArea#PageScroll > QWidget > QWidget {
                background: transparent;
            }
            QStackedWidget#Stack {
                background: transparent;
            }
            QLabel#Brand {
                color: #f8fbff;
                font-size: 20px;
                font-weight: 800;
            }
            QLabel#SidebarCaption {
                color: rgba(220, 236, 248, .62);
                font-size: 12px;
                text-transform: uppercase;
            }
            QListWidget#Nav {
                background: transparent;
                border: 0;
                outline: 0;
                padding: 4px 0;
            }
            QListWidget#Nav::item {
                border-radius: 999px;
                margin: 3px 0;
                padding: 8px 13px;
                color: rgba(238, 246, 255, .78);
            }
            QListWidget#Nav::item:selected {
                background: rgba(90, 167, 255, .20);
                border: 1px solid rgba(210, 238, 255, .20);
                color: white;
            }
            QListWidget#Nav::item:hover {
                background: rgba(90, 167, 255, .08);
                color: white;
            }
            QFrame#HeroHeader, QFrame#Card, QFrame#StatCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(34, 62, 98, .70), stop:.55 rgba(14, 30, 54, .62), stop:1 rgba(6, 15, 31, .52));
                border: 1px solid rgba(226, 245, 255, .25);
                border-radius: 34px;
            }
            QLabel#PageTitle {
                font-size: 34px;
                font-weight: 800;
                color: #f8fbff;
            }
            QLabel#Subtitle {
                color: rgba(220, 236, 248, .74);
                line-height: 1.35;
            }
            QLabel#Kicker {
                color: #7edcff;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: .08em;
                text-transform: uppercase;
            }
            QLabel#PanelTitle, QLabel#SectionTitle {
                color: #f8fbff;
                font-size: 20px;
                font-weight: 800;
            }
            QLabel#CardTitle {
                color: #f8fbff;
                font-size: 19px;
                font-weight: 800;
            }
            QLabel#SmallLabel {
                color: #f8fbff;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#MethodChip {
                color: #eaf7ff;
                background: rgba(42, 94, 135, .62);
                border: 1px solid rgba(126, 220, 255, .24);
                border-radius: 16px;
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#SliderValue {
                color: #7edcff;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#InfoBubble {
                padding: 14px 15px;
                border-radius: 25px;
                background: rgba(50, 130, 210, .28);
                border: 1px solid rgba(170, 226, 255, .34);
                color: rgba(214, 238, 255, .86);
            }
            QLabel#InfoBubble[state="connected"] {
                background: rgba(34, 197, 94, .16);
                border: 1px solid rgba(74, 222, 128, .42);
                color: #bfffd0;
            }
            QLabel#InfoBubble[state="testing"] {
                background: rgba(78, 163, 241, .18);
                border: 1px solid rgba(126, 220, 255, .36);
                color: #d9f4ff;
            }
            QLabel#InfoBubble[state="failed"] {
                background: rgba(248, 113, 113, .14);
                border: 1px solid rgba(252, 165, 165, .36);
                color: #ffd7d7;
            }
            QWidget#InlinePanel {
                background: rgba(8, 17, 32, .50);
                border: 1px solid rgba(226, 245, 255, .22);
                border-radius: 28px;
            }
            QLabel#StatValue {
                color: white;
                font-size: 23px;
                font-weight: 800;
            }
            QLabel#Muted {
                color: rgba(220, 236, 248, .68);
            }
            QLineEdit, QTextBrowser, QTreeWidget, QComboBox, QListWidget, QPlainTextEdit, QTextEdit {
                background: rgba(12, 25, 47, .78);
                border: 1px solid rgba(220, 242, 255, .26);
                border-radius: 25px;
                padding: 9px;
                color: #eef6ff;
                selection-background-color: rgba(90, 167, 255, .35);
            }
            QLineEdit:focus, QTextBrowser:focus, QTreeWidget:focus, QComboBox:focus, QListWidget:focus, QPlainTextEdit:focus, QTextEdit:focus {
                border: 1px solid rgba(154, 220, 255, .66);
                background: rgba(15, 31, 58, .88);
            }
            QListWidget::item, QTreeWidget::item {
                border-radius: 18px;
                padding: 7px 9px;
                margin: 2px 4px;
            }
            QListWidget::item:selected, QTreeWidget::item:selected {
                background: rgba(90, 167, 255, .22);
                color: #ffffff;
            }
            QListWidget::item:hover, QTreeWidget::item:hover {
                background: rgba(90, 167, 255, .12);
            }
            QListWidget#Nav {
                background: transparent;
                border: 0;
                border-radius: 0;
                outline: 0;
                padding: 4px 0;
            }
            QListWidget#Nav::item {
                border-radius: 999px;
                margin: 3px 0;
                padding: 8px 13px;
                color: rgba(238, 246, 255, .78);
            }
            QListWidget#Nav::item:selected {
                background: rgba(90, 167, 255, .20);
                border: 1px solid rgba(210, 238, 255, .20);
                color: white;
            }
            QListWidget#Nav::item:hover {
                background: rgba(90, 167, 255, .08);
                color: white;
            }
            QComboBox::drop-down {
                border: 0;
                width: 26px;
            }
            QComboBox QAbstractItemView {
                background: rgba(8, 18, 34, .96);
                border: 1px solid rgba(220, 242, 255, .30);
                border-radius: 22px;
                padding: 6px;
                selection-background-color: rgba(90, 167, 255, .24);
                color: #eef6ff;
                outline: 0;
            }
            QTextBrowser#KnowledgeCard {
                background: rgba(8, 17, 32, .72);
                border: 1px solid rgba(226, 245, 255, .28);
                border-radius: 30px;
                padding: 15px;
            }
            QFrame#KnowledgeCard {
                background: rgba(8, 17, 32, .72);
                border: 1px solid rgba(226, 245, 255, .28);
                border-radius: 30px;
            }
            QTextBrowser#KnowledgeCard h2 {
                color: #ffffff;
            }
            QTextBrowser#KnowledgeCard p, QTextBrowser#KnowledgeCard li {
                color: rgba(239, 248, 255, .84);
            }
            QTextBrowser#KnowledgeCard mark {
                background: rgba(255, 214, 102, .32);
                color: #fff7d6;
            }
            QWidget#UniverseMap {
                border: 1px solid rgba(226, 245, 255, .22);
                border-radius: 34px;
                background: #020617;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5aa7ff, stop:1 #167ef8);
                border: 1px solid rgba(226, 245, 255, .30);
                border-radius: 999px;
                padding: 10px 18px;
                color: white;
                font-weight: 700;
            }
            QPushButton:disabled {
                background: rgba(78, 163, 241, .16);
                border: 1px solid rgba(190, 226, 255, .12);
                color: rgba(238, 246, 255, .42);
            }
            QPushButton:checked {
                border: 1px solid rgba(186, 230, 253, .90);
                background: rgba(56, 189, 248, .52);
            }
            QPushButton:hover {
                background: #5aa7ff;
            }
            QPushButton#ExpanderButton {
                background: rgba(8, 17, 32, .72);
                border: 1px solid rgba(226, 245, 255, .26);
                border-radius: 24px;
                padding: 9px 14px;
                color: rgba(238, 246, 255, .92);
                font-weight: 700;
                text-align: left;
            }
            QPushButton#ExpanderButton:hover {
                background: rgba(78, 163, 241, .18);
                border-color: rgba(142, 207, 255, .42);
            }
            QPushButton#ExpanderButton:checked {
                background: rgba(78, 163, 241, .13);
                border: 1px solid rgba(186, 230, 253, .38);
                color: white;
            }
            QPushButton#LayerButton {
                background: rgba(43, 112, 152, .64);
                border: 1px solid rgba(170, 226, 255, .48);
                border-radius: 25px;
                padding: 10px 14px;
                color: rgba(238, 246, 255, .94);
                font-weight: 800;
            }
            QPushButton#LayerButton:hover {
                background: rgba(49, 139, 183, .76);
                border-color: rgba(186, 230, 253, .68);
            }
            QPushButton#LayerButton:checked {
                background: rgba(56, 189, 248, .58);
                border: 1px solid rgba(186, 230, 253, .82);
                color: white;
            }
            QRadioButton, QCheckBox {
                color: rgba(238, 246, 255, .92);
                spacing: 8px;
                min-height: 22px;
            }
            QRadioButton::indicator, QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked, QCheckBox::indicator:unchecked {
                border: 1px solid rgba(210, 238, 255, .46);
                border-radius: 9px;
                background: transparent;
            }
            QRadioButton::indicator:checked, QCheckBox::indicator:checked {
                border: 1px solid #5aa7ff;
                border-radius: 9px;
                background: #5aa7ff;
            }
            QCheckBox {
                padding: 7px 8px;
                border-radius: 18px;
                color: rgba(238, 246, 255, .86);
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1f2a44;
                border-radius: 999px;
            }
            QSlider::handle:horizontal {
                background: #7edcff;
                width: 16px;
                margin: -5px 0;
                border-radius: 999px;
            }
            QProgressBar {
                background: rgba(17, 28, 50, .82);
                border: 1px solid rgba(220, 242, 255, .24);
                border-radius: 14px;
                height: 18px;
                color: white;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 13px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #73f0a2, stop:1 #5aa7ff);
            }
            QScrollBar:vertical {
                background: rgba(2, 6, 23, .18);
                width: 12px;
                margin: 4px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(126, 220, 255, .30);
                border-radius: 6px;
                min-height: 34px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
                border: 0;
                background: transparent;
            }
            QScrollBar:horizontal {
                background: rgba(2, 6, 23, .18);
                height: 12px;
                margin: 4px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(126, 220, 255, .30);
                border-radius: 6px;
                min-width: 34px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
                border: 0;
                background: transparent;
            }
            QSplitter::handle {
                background: rgba(190, 226, 255, .08);
                width: 2px;
                border-radius: 999px;
            }
            """
        system_font = QApplication.font().family().replace('"', '\\"')
        self.setStyleSheet(stylesheet.replace("__SYSTEM_UI_FONT__", system_font))


from qt_app.pages import (
    ai_visualizer as _qt_ai_visualizer,
    antarctic_system as _qt_antarctic_system,
    mini_research_lab as _qt_mini_research_lab,
    raw_paper as _qt_raw_paper,
    research_directions as _qt_research_directions,
    research_universe as _qt_research_universe,
)

_QT_PAGE_MODULES = [
    _qt_research_universe,
    _qt_antarctic_system,
    _qt_ai_visualizer,
    _qt_mini_research_lab,
    _qt_research_directions,
    _qt_raw_paper,
]

for _qt_page_module in _QT_PAGE_MODULES:
    for _qt_name in getattr(_qt_page_module, "__all__", None) or [name for name in dir(_qt_page_module) if name.startswith("_") and not name.startswith("__")]:
        _qt_value = getattr(_qt_page_module, _qt_name)
        if callable(_qt_value):
            setattr(NativeAtlasWindow, _qt_name, _qt_value)

del _qt_page_module, _qt_name, _qt_value


def _install_packaged_smoke_probe(app, window):
    """Exit a packaged app after its bundled resources and all pages load."""

    started = time.monotonic()
    result = {"finished": False}

    def finish(code, message):
        if result["finished"]:
            return
        result["finished"] = True
        print(message, flush=True)
        window.close()
        app.exit(code)

    def poll():
        status_widget = getattr(window, "landing_status", None)
        status_text = status_widget.text() if status_widget else ""
        if "failed" in status_text.lower():
            finish(1, f"MACOS_APP_SMOKE_FAILED: {status_text}")
            return
        if getattr(window, "_main_ready", False):
            try:
                for index in range(len(window._page_builders)):
                    window._ensure_page_built(index)
                built = sum(widget is not None for widget in window._page_widgets)
                if built != 6:
                    raise RuntimeError(f"expected 6 pages, built {built}")
                if not window.pages:
                    raise RuntimeError("bundled paper returned no readable pages")
            except Exception as exc:
                finish(1, f"MACOS_APP_SMOKE_FAILED: {exc}")
                return
            QTimer.singleShot(
                1000,
                lambda: finish(
                    0,
                    f"MACOS_APP_SMOKE_OK pages={len(window.pages)} modules={built}",
                ),
            )
            return
        if time.monotonic() - started > 120:
            finish(1, f"MACOS_APP_SMOKE_TIMEOUT: {status_text}")
            return
        QTimer.singleShot(100, poll)

    QTimer.singleShot(0, poll)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(t("app.title", APP_TITLE))
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Omica Chow")
    icon_path = _application_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = NativeAtlasWindow()
    app.aboutToQuit.connect(window._shutdown_workers)
    window.show()
    window.raise_()
    window.activateWindow()
    if os.environ.get(PACKAGED_SMOKE_ENV) == "1":
        _install_packaged_smoke_probe(app, window)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
