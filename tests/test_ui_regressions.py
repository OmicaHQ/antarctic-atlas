import builtins
import os
import time
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QPushButton, QVBoxLayout, QWidget

import desktop_qt_app  # noqa: F401  # establishes page mixins before direct imports
from core.models import PaperPage
from qt_app.pages import antarctic_system, mini_research_lab, raw_paper, research_directions, research_universe


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _bind_page_methods(host_type, module):
    for name in dir(module):
        value = getattr(module, name)
        if name.startswith("_") and not name.startswith("__") and callable(value):
            setattr(host_type, name, value)


class _PageHost:
    def _page_shell(self, _title, _subtitle):
        page = QWidget()
        self.page_layout = QVBoxLayout(page)
        return page, self.page_layout


class _SystemHost(_PageHost):
    pass


class _RawPaperHost(_PageHost):
    pass


_bind_page_methods(_SystemHost, antarctic_system)
_bind_page_methods(_RawPaperHost, raw_paper)


def test_system_synthesis_is_in_layout_and_visible(qapp):
    host = _SystemHost()
    page = host._antarctic_system_page()

    assert host.page_layout.indexOf(host.system_synthesis) >= 0
    assert not host.system_synthesis.isHidden()
    assert host.system_synthesis.toPlainText().strip()

    page.deleteLater()
    qapp.processEvents()


def test_raw_paper_return_key_runs_search_without_dead_results_list(qapp):
    host = _RawPaperHost()
    host.pages = [
        PaperPage(1, "An overview of the Antarctic Ice Sheet."),
        PaperPage(2, "Grounding line retreat follows sustained basal melting."),
    ]
    page = host._raw_paper_page()

    assert not hasattr(host, "paper_results")
    host.paper_query.setText("grounding line")
    host.paper_query.returnPressed.emit()

    assert host.paper_match_combo.count() == 1
    assert host.paper_match_combo.currentData() == 2
    assert host.paper_text_label.text() == "Page 2"
    assert "Grounding line retreat" in host.paper_text.toPlainText()

    page.deleteLater()
    qapp.processEvents()


def test_provider_switch_keeps_api_key_drafts_separate(qapp):
    host = SimpleNamespace(
        universe_api_key=QLineEdit(),
        _universe_saved_keys={"DeepSeek API": "", "OpenAI API": ""},
        _universe_draft_keys={"DeepSeek API": "", "OpenAI API": ""},
        _universe_key_field_backend="",
    )

    research_universe._switch_universe_key_field(host, "DeepSeek API")
    host.universe_api_key.setText("deep-secret")
    research_universe._switch_universe_key_field(host, "OpenAI API")
    assert host.universe_api_key.text() == ""
    host.universe_api_key.setText("open-secret")
    research_universe._switch_universe_key_field(host, "DeepSeek API")
    assert host.universe_api_key.text() == "deep-secret"
    research_universe._switch_universe_key_field(host, "OpenAI API")
    assert host.universe_api_key.text() == "open-secret"


class _InterruptibleWorker:
    def __init__(self):
        self.interruptions = 0

    def isRunning(self):
        return True

    def requestInterruption(self):
        self.interruptions += 1


def test_provider_switch_interrupts_workers_and_invalidates_all_result_tokens():
    workers = [_InterruptibleWorker() for _ in range(3)]
    host = SimpleNamespace(
        _universe_active_backend="DeepSeek API",
        _universe_answer_token=4,
        _universe_classifier_token=7,
        _universe_test_token=2,
        _universe_answer_worker=workers[0],
        _universe_classifier_worker=workers[1],
        _universe_test_worker=workers[2],
        _universe_connection_status={
            "DeepSeek API|deepseek-v4-pro": {"state": "testing", "message": "working"},
        },
    )

    research_universe._activate_universe_backend(host, "OpenAI API")

    assert (host._universe_answer_token, host._universe_classifier_token, host._universe_test_token) == (5, 8, 3)
    assert [worker.interruptions for worker in workers] == [1, 1, 1]
    assert host._universe_answer_worker is None
    assert host._universe_classifier_worker is None
    assert host._universe_test_worker is None
    assert host._universe_connection_status["DeepSeek API|deepseek-v4-pro"] == {
        "state": "unknown",
        "message": "",
    }


def test_stale_connection_test_result_is_ignored_after_provider_switch():
    status_updates = []
    host = SimpleNamespace(
        _shutting_down=False,
        _universe_test_token=3,
        _set_universe_connection_status=lambda *args: status_updates.append(args),
    )

    research_universe._finish_universe_backend_test(
        host,
        2,
        {"ok": True, "backend": "DeepSeek API", "model": "deepseek-v4-pro", "message": "connected"},
    )

    assert status_updates == []


class _FakeSignal:
    def connect(self, _slot):
        pass


class _CapturingWorker:
    created = []

    def __init__(self, fn, *args, **kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.resultReady = _FakeSignal()
        self.errorReady = _FakeSignal()
        self.finished = _FakeSignal()
        self.created.append(self)

    def start(self):
        pass

    def deleteLater(self):
        pass


class _NoOnlineAPIKeyReads(dict):
    def get(self, key, default=None):
        if key in {"DEEPSEEK_API_KEY", "OPENAI_API_KEY"}:
            raise AssertionError(f"Local Ollama attempted to read {key}")
        return super().get(key, default)


def test_local_ollama_connection_test_never_reads_or_carries_online_api_key(qapp, monkeypatch):
    backend = QComboBox()
    backend.addItem("Local Ollama")
    model = QComboBox()
    model.addItem("local-model")
    _CapturingWorker.created.clear()
    monkeypatch.setattr(research_universe, "FunctionWorker", _CapturingWorker)
    monkeypatch.setattr(research_universe.os, "environ", _NoOnlineAPIKeyReads())
    host = SimpleNamespace(
        universe_backend=backend,
        universe_model_combo=model,
        universe_api_key=QLineEdit(),
        universe_save_key=QPushButton(),
        _universe_key_field_backend="",
        _universe_saved_keys={"DeepSeek API": "deep-secret", "OpenAI API": "open-secret"},
        _universe_draft_keys={"DeepSeek API": "", "OpenAI API": ""},
        _universe_workers=[],
        _universe_test_token=0,
        _test_universe_backend_connection_sync=lambda *_args: None,
        _set_universe_backend_info=lambda *_args: None,
        _set_universe_connection_status=lambda *_args: None,
        _show_current_universe_connection_status=lambda: None,
        _cleanup_universe_worker=lambda *_args: None,
    )

    research_universe._test_universe_backend_connection(host)

    assert len(_CapturingWorker.created) == 1
    assert _CapturingWorker.created[0].args == ("Local Ollama", "local-model", "")


def test_mini_lab_formats_snowfall_in_calculation_units():
    assert mini_research_lab._format_lab_control_value(None, "Snowfall / Accumulation (m/yr)", 10) == "1.0"


def test_window_shutdown_waits_for_active_worker(qapp):
    window = desktop_qt_app.NativeAtlasWindow()
    worker = desktop_qt_app.FunctionWorker(lambda: time.sleep(0.15))
    window._prepare_worker = worker
    worker.start()

    window.close()

    assert window._shutting_down is True
    assert not worker.isRunning()
    window.deleteLater()
    qapp.processEvents()


class _ExportHost:
    def __init__(self):
        self.direction_combo = object()
        self.direction_ambition = SimpleNamespace(value=lambda: 3)
        self.direction_download_status = SimpleNamespace(text="")
        self.direction_download_status.setText = self._set_status

    def _set_status(self, message):
        self.direction_download_status.text = message

    def _direction_selected_focus(self, _info):
        return "Question", ["Method"], ["Region"]

    def _direction_proposal_text(self, *_args):
        return "proposal body"

    def _direction_proposal_filename(self, name):
        return research_directions._direction_proposal_filename(self, name)


def _prepare_export(monkeypatch, path, locale="en"):
    monkeypatch.setattr(
        research_directions,
        "QFileDialog",
        SimpleNamespace(getSaveFileName=lambda *_args: (str(path), "Text files (*.txt)")),
    )
    monkeypatch.setattr(research_directions, "current_locale", lambda: locale)
    monkeypatch.setattr(research_directions, "combo_current_key", lambda _combo: "Ocean heat pathways")


def test_proposal_export_appends_txt_and_reports_english_success(tmp_path, monkeypatch):
    destination = tmp_path / "proposal"
    _prepare_export(monkeypatch, destination, locale="en")
    host = _ExportHost()

    research_directions._download_direction_proposal(host)

    output = tmp_path / "proposal.txt"
    assert output.read_text(encoding="utf-8") == "proposal body"
    assert host.direction_download_status.text == f"Saved proposal seed to {output}"


def test_chinese_proposal_scaffold_is_fully_localized(monkeypatch):
    monkeypatch.setattr(research_directions, "current_locale", lambda: "zh")
    info = {
        "why_now": "Why now",
        "gap": "Knowledge gap",
        "student_angle": "Student angle",
    }

    proposal = research_directions._direction_proposal_text(
        None,
        "Ocean heat pathways",
        info,
        "How does heat reach ice shelves?",
        ["Ocean observations"],
        ["Amundsen Sea"],
        3,
    )

    assert "标题：" in proposal
    assert "研究动机：" in proposal
    assert "预期产出：" in proposal
    assert "Title:" not in proposal
    assert "Expected output:" not in proposal


def test_proposal_export_reports_chinese_os_error(tmp_path, monkeypatch):
    _prepare_export(monkeypatch, tmp_path / "proposal", locale="zh")
    monkeypatch.setattr(builtins, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")))
    host = _ExportHost()

    research_directions._download_direction_proposal(host)

    assert host.direction_download_status.text == "保存失败：disk full"


@pytest.mark.parametrize(
    ("locale", "expected"),
    [("en", "Save cancelled."), ("zh", "已取消保存。")],
)
def test_proposal_export_cancel_status_is_localized(monkeypatch, locale, expected):
    _prepare_export(monkeypatch, "", locale=locale)
    host = _ExportHost()

    research_directions._download_direction_proposal(host)

    assert host.direction_download_status.text == expected
