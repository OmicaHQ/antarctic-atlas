from desktop_qt_app import *

from core.ai import (
    chat as ai_chat,
    classify as ai_classify,
    extract_backend_text,
    resolve_api_key,
)
from core.paper import extract_search_window
from core.universe import match_topic

def _u_zh():
    return current_locale().startswith("zh")


def _u_text(en_text, zh_text=None):
    if zh_text and _u_zh():
        return zh_text
    return translate_text(en_text)


def _u_display_name(name):
    return translate_text(name)


def _u_display_module(parent, topic):
    if parent in ["Core system", "Research area", topic]:
        return _u_display_name(topic)
    return f"{_u_display_name(parent)} / {_u_display_name(topic)}"


def _research_universe_page(self):
    self._universe_saved_keys = {"DeepSeek API": "", "OpenAI API": ""}
    self._universe_draft_keys = {"DeepSeek API": "", "OpenAI API": ""}
    self._universe_key_field_backend = ""
    page, layout = self._page_shell(
        "🌌 Research Universe Explorer",
        "",
    )

    splitter = QSplitter(Qt.Horizontal)
    left = QWidget()
    left_layout = QVBoxLayout(left)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(10)
    caption = QLabel(_u_text(
        "Explore the review paper as a knowledge universe. Ask on the right; the map stays visible, locates the matching node, and updates the concise card inside the map.",
        "把综述论文作为知识宇宙来探索。在右侧提问，图谱会保持可见、定位匹配节点，并更新图中的简明知识卡。",
    ))
    caption.setObjectName("Muted")
    caption.setWordWrap(True)
    self.universe_map = OriginalUniverseWebWidget()
    left_layout.addWidget(caption)
    left_layout.addWidget(self.universe_map, 1)

    copilot = QWidget()
    copilot_layout = QVBoxLayout(copilot)
    copilot_layout.setContentsMargins(18, 0, 0, 0)
    copilot_layout.setSpacing(14)
    copilot_title = QLabel("Research Copilot")
    copilot_title.setObjectName("PanelTitle")
    backend_label = QLabel("AI Backend")
    backend_label.setObjectName("SmallLabel")
    self.universe_backend = QComboBox()
    self.universe_backend.setAccessibleName(_u_text("AI backend", "AI 后端"))
    self.universe_backend.addItems(["Evidence only", "Local Ollama", "DeepSeek API", "OpenAI API"])
    self.universe_backend.currentTextChanged.connect(self._update_universe_backend_controls)
    self.universe_backend_info = QLabel(_u_text(
        "Evidence-only mode is active. Questions will focus the map and retrieve relevant passages without calling an AI API.",
        "纯证据模式已启用。提问会定位图谱并检索相关论文段落，不调用 AI API。",
    ))
    self.universe_backend_info.setObjectName("InfoBubble")
    self.universe_backend_info.setWordWrap(True)
    self.universe_model_label = QLabel("Model")
    self.universe_model_label.setObjectName("SmallLabel")
    self.universe_model_combo = QComboBox()
    self.universe_model_combo.setAccessibleName(_u_text("AI model", "AI 模型"))
    self.universe_model_combo.currentTextChanged.connect(self._on_universe_model_changed)
    self.universe_api_label = QLabel(_u_text("API key (this session only)", "API 密钥（仅本次运行）"))
    self.universe_api_label.setObjectName("SmallLabel")
    self.universe_api_key = QLineEdit()
    self.universe_api_key.setAccessibleName(_u_text("Provider API key for this session", "本次运行使用的服务商 API 密钥"))
    self.universe_api_key.setEchoMode(QLineEdit.Password)
    self.universe_api_key.setPlaceholderText("sk-...")
    self.universe_api_key.textChanged.connect(lambda _text: self._show_current_universe_connection_status())
    self.universe_save_key = QPushButton(_u_text("Use & Test Connection", "本次会话使用并测试"))
    self.universe_save_key.clicked.connect(self._test_universe_backend_connection)
    question_label = QLabel(_u_text("Ask a question about the Antarctic Ice Sheet review paper:", "询问有关南极冰盖综述论文的问题："))
    question_label.setObjectName("SmallLabel")
    question_label.setWordWrap(True)
    self.universe_search = QLineEdit()
    self.universe_search.setAccessibleName(_u_text("Research question", "研究问题"))
    self.universe_search.setPlaceholderText(_u_text("Example: Why is grounding line retreat important?", "示例：为什么接地线后退很重要？"))
    self.universe_focus_button = QPushButton("Search evidence")
    self.universe_focus_button.clicked.connect(self._focus_universe_topic)
    self.universe_search.returnPressed.connect(self._focus_universe_topic)
    self.universe_match_label = QLabel("")
    self.universe_match_label.setObjectName("Muted")
    self.universe_match_label.setWordWrap(True)
    copilot_layout.addWidget(copilot_title)
    copilot_layout.addWidget(backend_label)
    copilot_layout.addWidget(self.universe_backend)
    copilot_layout.addWidget(self.universe_backend_info)
    copilot_layout.addWidget(self.universe_model_label)
    copilot_layout.addWidget(self.universe_model_combo)
    copilot_layout.addWidget(self.universe_api_label)
    copilot_layout.addWidget(self.universe_api_key)
    copilot_layout.addWidget(self.universe_save_key)
    copilot_layout.addWidget(question_label)
    copilot_layout.addWidget(self.universe_search)
    copilot_layout.addWidget(self.universe_focus_button)
    copilot_layout.addWidget(self.universe_match_label)
    copilot_layout.addStretch(1)

    self.universe_map.topicSelected.connect(self._show_universe_topic)
    self.topic_names = ["Antarctic Ice Sheet"]
    for area_name, area in RESEARCH_AREAS.items():
        self.topic_names.append(area_name)
        self.topic_names.extend(area["topics"].keys())
    splitter.addWidget(left)
    splitter.addWidget(copilot)
    splitter.setSizes([880, 280])
    splitter.setStretchFactor(0, 1)
    layout.addWidget(splitter, 1)

    self.universe_evidence = QTextBrowser()
    self.universe_evidence.setObjectName("KnowledgeCard")
    self.universe_evidence.setMinimumHeight(160)
    self.universe_evidence.setVisible(False)
    layout.addWidget(self.universe_evidence)
    self.universe_passages_toggle = QPushButton("Retrieved passages from the paper")
    self.universe_passages_toggle.setObjectName("ExpanderButton")
    self.universe_passages_toggle.setCheckable(True)
    self.universe_passages_toggle.clicked.connect(self._toggle_universe_passages)
    self.universe_passages_toggle.setVisible(False)
    layout.addWidget(self.universe_passages_toggle)
    self.universe_passages = QTextBrowser()
    self.universe_passages.setObjectName("KnowledgeCard")
    self.universe_passages.setMinimumHeight(260)
    self.universe_passages.setVisible(False)
    layout.addWidget(self.universe_passages)
    self.universe_work_status = QLabel("")
    self.universe_work_status.setObjectName("Muted")
    self.universe_work_status.setWordWrap(True)
    self.universe_work_status.setVisible(False)
    layout.addWidget(self.universe_work_status)
    self.universe_answer_progress = QProgressBar()
    self.universe_answer_progress.setRange(0, 100)
    self.universe_answer_progress.setValue(0)
    self.universe_answer_progress.setVisible(False)
    layout.addWidget(self.universe_answer_progress)
    self.universe_answer = QTextBrowser()
    self.universe_answer.setObjectName("KnowledgeCard")
    self.universe_answer.setMinimumHeight(150)
    self.universe_answer.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.universe_answer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
    self.universe_answer.setVisible(False)
    layout.addWidget(self.universe_answer)

    self._universe_answer_worker = None
    self._universe_test_worker = None
    self._universe_classifier_worker = None
    self._universe_workers = []
    self._universe_answer_token = 0
    self._universe_classifier_token = 0
    self._universe_test_token = 0
    self._ollama_auto_test_started = False
    self._universe_type_timer = QTimer(self)
    self._universe_type_timer.setInterval(18)
    self._universe_type_token = 0
    self._universe_type_prefix = ""
    self._universe_type_answer = ""
    self._universe_type_index = 0
    self._universe_stream_prefix = ""
    self._universe_stream_answer = ""
    self._universe_connection_status = {}
    self._update_universe_backend_controls()
    QTimer.singleShot(300, self._auto_test_ollama_if_needed)
    return page


def _universe_status_key(self, backend=None, model=None):
    backend = backend or (combo_current_key(self.universe_backend) if hasattr(self, "universe_backend") else "Evidence only")
    model = model or (combo_current_key(self.universe_model_combo) if hasattr(self, "universe_model_combo") else "")
    return f"{backend}|{model or 'default'}"


def _set_universe_connection_status(self, backend, model, state, message=""):
    if not hasattr(self, "_universe_connection_status"):
        self._universe_connection_status = {}
    self._universe_connection_status[self._universe_status_key(backend, model)] = {
        "state": state,
        "message": message,
    }


def _current_universe_connection_status(self, backend, model=""):
    if not hasattr(self, "_universe_connection_status"):
        self._universe_connection_status = {}
    return self._universe_connection_status.get(self._universe_status_key(backend, model), {"state": "unknown", "message": ""})


def _set_universe_backend_info(self, message, state="neutral"):
    if not hasattr(self, "universe_backend_info"):
        return
    self.universe_backend_info.setProperty("state", state)
    self.universe_backend_info.setText(message)
    self.universe_backend_info.style().unpolish(self.universe_backend_info)
    self.universe_backend_info.style().polish(self.universe_backend_info)
    self.universe_backend_info.update()


def _set_universe_work_status(self, message="", active=False):
    if not hasattr(self, "universe_work_status"):
        return
    self.universe_work_status.setText(message)
    self.universe_work_status.setVisible(bool(active and message))


def _set_universe_answer_markdown(self, markdown_text):
    if not hasattr(self, "universe_answer"):
        return
    text = clean_answer_markdown(markdown_text)
    if hasattr(self.universe_answer, "setMarkdown"):
        self.universe_answer.setMarkdown(text)
    else:
        html_text = html.escape(text).replace("\n", "<br>")
        self.universe_answer.setHtml(f"<p>{html_text}</p>")
    doc = self.universe_answer.document()
    text_width = max(260, self.universe_answer.viewport().width() - 24)
    doc.setTextWidth(text_width)
    target_height = max(150, min(1400, int(doc.size().height()) + 38))
    self.universe_answer.setMinimumHeight(target_height)
    self.universe_answer.setMaximumHeight(target_height)


def _show_current_universe_connection_status(self):
    if not hasattr(self, "universe_backend_info"):
        return
    backend = combo_current_key(self.universe_backend)
    model = combo_current_key(self.universe_model_combo) if hasattr(self, "universe_model_combo") else ""
    if backend == "Evidence only":
        self._set_universe_backend_info(_u_text(
            "Evidence-only mode is active. Questions use local evidence search and do not call an AI model.",
            "纯证据模式已启用。问题使用本地证据检索，不调用 AI 模型。",
        ), "neutral")
        return
    typed_key = (
        self.universe_api_key.text().strip()
        if backend in ["DeepSeek API", "OpenAI API"]
        and getattr(self, "_universe_key_field_backend", "") == backend
        and hasattr(self, "universe_api_key")
        else ""
    )
    saved_key = getattr(self, "_universe_saved_keys", {}).get(backend, "") if backend in ["DeepSeek API", "OpenAI API"] else ""
    if backend in ["DeepSeek API", "OpenAI API"] and not self._universe_api_key(backend):
        self._set_universe_backend_info(_u_text(
            f"{backend} / {model}: enter your API key, then Use & Test to enable AI module matching.",
            f"{backend} / {model}：请输入 API 密钥，然后在本次会话中使用并测试，以启用 AI 模块匹配。",
        ), "neutral")
        return
    if backend in ["DeepSeek API", "OpenAI API"] and typed_key and typed_key != saved_key:
        self._set_universe_backend_info(_u_text(
            f"{backend} / {model}: key entered for this provider. Use & Test verifies it for this session.",
            f"{backend} / {model}：已为当前服务商输入密钥。使用并测试会在本次会话中验证它。",
        ), "testing")
        return
    status = self._current_universe_connection_status(backend, model)
    if status["state"] == "connected":
        self._set_universe_backend_info(status["message"] or _u_text(
            f"{backend} / {model}: connection verified. AI module matching is ready.",
            f"{backend} / {model}：连接已验证，AI 模块匹配已就绪。",
        ), "connected")
    elif status["state"] == "testing":
        self._set_universe_backend_info(status["message"] or _u_text(
            f"{backend} / {model}: testing connection...",
            f"{backend} / {model}：正在测试连接...",
        ), "testing")
    elif status["state"] == "failed":
        self._set_universe_backend_info(status["message"] or _u_text(
            f"{backend} / {model}: connection test failed.",
            f"{backend} / {model}：连接测试失败。",
        ), "failed")
    else:
        self._set_universe_backend_info(_u_text(
            f"{backend} / {model}: a session or environment key is available. Run Use & Test to verify the connection.",
            f"{backend} / {model}：本次会话或环境变量中已有密钥。请运行“使用并测试”来验证连接。",
        ), "neutral")


def _on_universe_model_changed(self, _model):
    self._show_current_universe_connection_status()


def _update_universe_backend_controls(self):
    if not hasattr(self, "universe_backend"):
        return
    backend = combo_current_key(self.universe_backend)
    _activate_universe_backend(self, backend)
    model_options = []
    if backend == "Local Ollama":
        model_options = [OLLAMA_MODEL]
        status = _u_text(
            f"Local Ollama mode selected. Current local model: {OLLAMA_MODEL}. Connection status is not tested yet.",
            f"已选择本地 Ollama。当前本地模型：{OLLAMA_MODEL}。连接状态尚未测试。",
        )
    elif backend == "DeepSeek API":
        model_options = [DEEPSEEK_MODEL, "deepseek-v4-flash"]
        configured = bool(os.environ.get("DEEPSEEK_API_KEY") or self._universe_saved_keys.get("DeepSeek API", ""))
        status = _u_text("A DeepSeek key is available for this session. Use & Test verifies the connection.", "本次会话已有 DeepSeek 密钥。使用并测试会验证连接。") if configured else _u_text("DeepSeek API key is not configured.", "DeepSeek API 密钥尚未配置。")
    elif backend == "OpenAI API":
        model_options = OPENAI_MODEL_OPTIONS or [OPENAI_MODEL]
        configured = bool(os.environ.get("OPENAI_API_KEY") or self._universe_saved_keys.get("OpenAI API", ""))
        status = _u_text("An OpenAI key is available for this session. Use & Test verifies the connection.", "本次会话已有 OpenAI 密钥。使用并测试会验证连接。") if configured else _u_text("OpenAI API key is not configured.", "OpenAI API 密钥尚未配置。")
    else:
        status = _u_text(
            "Evidence-only mode is active. Questions will focus the map and retrieve relevant passages without calling an AI API.",
            "纯证据模式已启用。提问会定位图谱并检索相关论文段落，不调用 AI API。",
        )

    self._set_universe_backend_info(status, "neutral")
    self.universe_focus_button.setText("Search evidence" if backend == "Evidence only" else "Ask AI and focus map")
    has_model = bool(model_options)
    for widget in [self.universe_model_label, self.universe_model_combo]:
        widget.setVisible(has_model)
    self.universe_model_combo.blockSignals(True)
    self.universe_model_combo.clear()
    self.universe_model_combo.addItems(model_options)
    self.universe_model_combo.blockSignals(False)
    needs_key = backend in ["DeepSeek API", "OpenAI API"]
    for widget in [self.universe_api_label, self.universe_api_key]:
        widget.setVisible(needs_key)
    self._switch_universe_key_field(backend)
    self.universe_save_key.setVisible(backend != "Evidence only")
    if backend == "Local Ollama":
        self.universe_save_key.setText("Test Local Ollama")
    elif backend == "DeepSeek API":
        self.universe_save_key.setText(_u_text("Use & Test DeepSeek", "使用并测试 DeepSeek"))
    else:
        self.universe_save_key.setText(_u_text("Use & Test OpenAI", "使用并测试 OpenAI"))
    self._show_current_universe_connection_status()
    if backend == "Local Ollama":
        QTimer.singleShot(100, self._auto_test_ollama_if_needed)


def _activate_universe_backend(self, backend):
    """Make a provider switch an explicit cancellation and result boundary."""

    previous = getattr(self, "_universe_active_backend", None)
    if previous is not None and previous != backend:
        _invalidate_universe_backend_work(self)
    self._universe_active_backend = backend


def _invalidate_universe_backend_work(self):
    """Interrupt provider work and reject any result already queued for the UI."""

    self._universe_answer_token = getattr(self, "_universe_answer_token", 0) + 1
    self._universe_classifier_token = getattr(self, "_universe_classifier_token", 0) + 1
    self._universe_test_token = getattr(self, "_universe_test_token", 0) + 1

    had_answer = getattr(self, "_universe_answer_worker", None) is not None
    had_classifier = getattr(self, "_universe_classifier_worker", None) is not None
    seen = set()
    for attribute in [
        "_universe_answer_worker",
        "_universe_classifier_worker",
        "_universe_test_worker",
    ]:
        worker = getattr(self, attribute, None)
        if worker is not None and id(worker) not in seen:
            seen.add(id(worker))
            try:
                if worker.isRunning():
                    worker.requestInterruption()
            except RuntimeError:
                pass
        setattr(self, attribute, None)

    for status in getattr(self, "_universe_connection_status", {}).values():
        if status.get("state") == "testing":
            status.update(state="unknown", message="")

    if hasattr(self, "universe_focus_button"):
        self.universe_focus_button.setEnabled(True)
    if hasattr(self, "universe_save_key"):
        self.universe_save_key.setEnabled(True)
    if hasattr(self, "universe_answer_progress"):
        self.universe_answer_progress.setRange(0, 100)
        self.universe_answer_progress.setVisible(False)
    if had_classifier and hasattr(self, "universe_evidence"):
        self.universe_evidence.setVisible(False)
    if had_answer and hasattr(self, "universe_answer"):
        self.universe_answer.setVisible(False)
    if hasattr(self, "_set_universe_work_status"):
        self._set_universe_work_status("", False)


def _switch_universe_key_field(self, backend):
    if not hasattr(self, "universe_api_key"):
        return
    previous = getattr(self, "_universe_key_field_backend", "")
    if previous in ["DeepSeek API", "OpenAI API"]:
        self._universe_draft_keys[previous] = self.universe_api_key.text().strip()
    self._universe_key_field_backend = backend if backend in ["DeepSeek API", "OpenAI API"] else ""
    value = ""
    if self._universe_key_field_backend:
        value = (
            self._universe_draft_keys.get(backend, "")
            or self._universe_saved_keys.get(backend, "")
        )
    self.universe_api_key.blockSignals(True)
    self.universe_api_key.setText(value)
    self.universe_api_key.setPlaceholderText(
        "DeepSeek API key" if backend == "DeepSeek API" else "OpenAI API key"
    )
    self.universe_api_key.blockSignals(False)


def _auto_test_ollama_if_needed(self):
    if getattr(self, "_shutting_down", False):
        return
    if not hasattr(self, "universe_backend") or not hasattr(self, "universe_model_combo"):
        return
    if combo_current_key(self.universe_backend) != "Local Ollama":
        return
    model = combo_current_key(self.universe_model_combo) or OLLAMA_MODEL
    status = self._current_universe_connection_status("Local Ollama", model)
    if status.get("state") in ["connected", "testing"] or self._worker_is_running(getattr(self, "_universe_test_worker", None)):
        return
    self._ollama_auto_test_started = True
    self._set_universe_connection_status("Local Ollama", model, "testing", _u_text(
        f"Local Ollama / {model}: automatically checking local model...",
        f"本地 Ollama / {model}：正在自动检查本地模型...",
    ))
    self._show_current_universe_connection_status()
    self._universe_test_token += 1
    token = self._universe_test_token
    worker = FunctionWorker(self._test_universe_backend_connection_sync, "Local Ollama", model, "")
    self._universe_test_worker = worker
    worker.resultReady.connect(
        lambda result, token=token: self._finish_universe_backend_test(token, result)
    )
    worker.errorReady.connect(
        lambda message, token=token, model=model: self._finish_universe_backend_test(
            token,
            {"ok": False, "backend": "Local Ollama", "model": model, "message": _u_text(
                f"Local Ollama / {model}: automatic check failed. {message}",
                f"本地 Ollama / {model}：自动检查失败。{message}",
            )}
        )
    )
    self._universe_workers.append(worker)
    worker.finished.connect(lambda worker=worker: self._cleanup_universe_worker(worker))
    worker.finished.connect(worker.deleteLater)
    worker.start()


def _test_universe_backend_connection(self):
    backend = combo_current_key(self.universe_backend) if hasattr(self, "universe_backend") else "Evidence only"
    if backend == "Evidence only":
        return
    key = (
        self.universe_api_key.text().strip()
        if getattr(self, "_universe_key_field_backend", "") == backend
        else ""
    )
    needs_key = backend in ["DeepSeek API", "OpenAI API"]
    saved_key = getattr(self, "_universe_saved_keys", {}).get(backend, "")
    env_key = ""
    if backend == "DeepSeek API":
        env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    elif backend == "OpenAI API":
        env_key = os.environ.get("OPENAI_API_KEY", "")
    if needs_key and not key and not saved_key and not env_key:
        self._set_universe_backend_info(_u_text(
            f"{backend}: enter an API key first, or set the matching environment variable.",
            f"{backend}：请先输入 API 密钥，或设置对应环境变量。",
        ), "failed")
        return
    if needs_key and key:
        self._universe_saved_keys[backend] = key
        self._universe_draft_keys[backend] = key
    active_key = (key or saved_key or env_key or "") if needs_key else ""
    model = combo_current_key(self.universe_model_combo) if hasattr(self, "universe_model_combo") else ""
    verb = "using the key for this session; testing connection" if needs_key else "testing local connection"
    zh_verb = "正在本次会话中使用该密钥并测试连接" if needs_key else "正在测试本地连接"
    self._set_universe_connection_status(backend, model, "testing", _u_text(
        f"{backend} / {model}: {verb}...",
        f"{backend} / {model}：{zh_verb}...",
    ))
    self._show_current_universe_connection_status()
    self.universe_save_key.setEnabled(False)
    self._universe_test_token += 1
    token = self._universe_test_token
    worker = FunctionWorker(self._test_universe_backend_connection_sync, backend, model, active_key)
    self._universe_test_worker = worker
    worker.resultReady.connect(
        lambda result, token=token: self._finish_universe_backend_test(token, result)
    )
    worker.errorReady.connect(
        lambda message, token=token, backend=backend, model=model: self._finish_universe_backend_test(
            token,
            {"ok": False, "backend": backend, "model": model, "message": _u_text(
                f"{backend} / {model}: request failed. {message}",
                f"{backend} / {model}：请求失败。{message}",
            )}
        )
    )
    self._universe_workers.append(worker)
    worker.finished.connect(lambda worker=worker: self._cleanup_universe_worker(worker))
    worker.finished.connect(worker.deleteLater)
    worker.start()


def _test_universe_backend_connection_sync(self, backend, model, api_key=""):
    try:
        text = self._call_universe_backend_text(
            backend,
            "Reply with exactly: connection-ok",
            system="You are a connectivity probe. Reply with one short sentence only.",
            max_tokens=48,
            temperature=0.0,
            timeout=35,
            model=model,
            api_key=api_key,
        )
    except Exception as exc:
        return {"ok": False, "backend": backend, "model": model, "message": _u_text(
            f"{backend} / {model}: request failed. {exc}",
            f"{backend} / {model}：请求失败。{exc}",
        )}
    if text.strip():
        preview = clean_text(text)[:80]
        return {"ok": True, "backend": backend, "model": model, "message": _u_text(
            f"{backend} / {model}: connected. Model replied: {preview}",
            f"{backend} / {model}：连接成功。模型回复：{preview}",
        )}
    return {"ok": False, "backend": backend, "model": model, "message": _u_text(
        f"{backend} / {model}: request completed but the model returned no readable text.",
        f"{backend} / {model}：请求完成，但模型没有返回可读文本。",
    )}


def _finish_universe_backend_test(self, token, result):
    if (
        getattr(self, "_shutting_down", False)
        or token != getattr(self, "_universe_test_token", 0)
    ):
        return
    if isinstance(result, str):
        backend = combo_current_key(self.universe_backend)
        model = combo_current_key(self.universe_model_combo) if hasattr(self, "universe_model_combo") else ""
        ok = "connected" in result.lower()
        message = result
    else:
        backend = result.get("backend", combo_current_key(self.universe_backend))
        model = result.get("model", combo_current_key(self.universe_model_combo) if hasattr(self, "universe_model_combo") else "")
        ok = bool(result.get("ok"))
        message = result.get("message", "")
    self._set_universe_connection_status(backend, model, "connected" if ok else "failed", message)
    self._show_current_universe_connection_status()
    self.universe_save_key.setEnabled(True)


def _cleanup_universe_worker(self, worker):
    if hasattr(self, "_universe_workers") and worker in self._universe_workers:
        self._universe_workers.remove(worker)
    if worker is getattr(self, "_universe_answer_worker", None):
        self._universe_answer_worker = None
    if worker is getattr(self, "_universe_test_worker", None):
        self._universe_test_worker = None
    if worker is getattr(self, "_universe_classifier_worker", None):
        self._universe_classifier_worker = None


def _worker_is_running(self, worker):
    if not worker:
        return False
    try:
        return worker.isRunning()
    except RuntimeError:
        return False


def _universe_api_key(self, backend):
    typed_key = self.universe_api_key.text() if hasattr(self, "universe_api_key") else ""
    return resolve_api_key(
        backend,
        typed_backend=getattr(self, "_universe_key_field_backend", ""),
        typed_key=typed_key,
        session_keys=getattr(self, "_universe_saved_keys", {}),
    )


def _universe_model(self, backend):
    selected = combo_current_key(self.universe_model_combo) if hasattr(self, "universe_model_combo") else ""
    if selected:
        return selected
    if backend == "DeepSeek API":
        return DEEPSEEK_MODEL
    if backend == "OpenAI API":
        return OPENAI_MODEL
    return OLLAMA_MODEL


def _call_universe_backend_text(self, backend, prompt, system="", max_tokens=1200, temperature=0.2, timeout=120, model=None, api_key=None):
    """Thin wrapper over core.ai.chat. model/api_key must be snapshot on the GUI
    thread before this runs on a worker thread (never read widgets here)."""
    return ai_chat(
        backend,
        prompt,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
        model=model,
        api_key=api_key or "",
    )


def _stream_universe_backend_text(self, on_chunk, backend, prompt, system="", max_tokens=1200, temperature=0.2, timeout=120, model=None, api_key=None):
    return ai_chat(
        backend,
        prompt,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
        model=model,
        api_key=api_key or "",
        on_chunk=on_chunk,
    )


def _classify_universe_topic_with_backend(self, question, backend, api_key="", model=""):
    if backend == "Evidence only":
        return None
    allowed = []
    for topic in self.topic_names:
        parent = next(
            (area for area, meta in RESEARCH_AREAS.items() if topic in meta["topics"]),
            "Core system" if topic == "Antarctic Ice Sheet" else "Research area",
        )
        allowed.append((topic, parent))
    return ai_classify(question, allowed, backend, model=model or None, api_key=api_key)


def _stream_universe_answer(self, on_chunk, backend, topic, query, passages, display, api_key="", model=""):
    context = "\n\n".join([f"Excerpt {index + 1}:\n{item['text']}" for index, item in enumerate(passages)])
    if not context:
        context = "No retrieved paper excerpts were available. Say that no passages were retrieved and ask the user to try a more specific research term."
    answer_language = "Chinese, but keep important scientific terms in English" if _u_zh() else "English"
    prompt = f"""
You are helping a student understand a review paper about the Antarctic Ice Sheet.
Use ONLY the excerpts below when making scientific claims.
Answer in {answer_language}.
Use clean Markdown formatting with short paragraphs and bullet lists only when useful.
Do not output page numbers, Page citations, bracketed source markers, or citation-style symbols.
If the excerpts are insufficient, explain what is missing instead of pretending to know.

Question:
{query or topic}

Matched knowledge-graph node:
{display}

Paper excerpts:
{context}
"""
    system_language = (
        "Answer in Chinese, keep key scientific terms in English,"
        if _u_zh()
        else "Answer in English,"
    )
    return self._stream_universe_backend_text(
        on_chunk,
        backend,
        prompt,
        system=f"You are a careful scientific reading assistant. {system_language} and stay grounded in the provided excerpts.",
        max_tokens=1600,
        temperature=0.2,
        model=model,
        api_key=api_key,
    )


def _show_universe_topic(self, name):
    if not name:
        return
    self._stop_universe_answer_typewriter()
    if hasattr(self, "universe_match_label"):
        parent = next((area for area, meta in RESEARCH_AREAS.items() if name in meta["topics"]), "Core system" if name == "Antarctic Ice Sheet" else "Research area")
        display = _u_display_module(parent, name)
        self.universe_match_label.setText(_u_text(
            f"Selected module: {parent} / {name}. Ask a question to retrieve paper passages below.",
            f"已选模块：{display}。在下方提问即可检索论文段落。",
        ))
    if hasattr(self, "universe_evidence"):
        self.universe_evidence.setVisible(False)
    if hasattr(self, "universe_passages_toggle"):
        self.universe_passages_toggle.setChecked(False)
        self.universe_passages_toggle.setVisible(False)
        self.universe_passages_toggle.setText(_u_text("Retrieved passages from the paper", "已检索到的论文段落"))
    if hasattr(self, "universe_passages"):
        self.universe_passages.setVisible(False)
    if hasattr(self, "universe_answer_progress"):
        self.universe_answer_progress.setVisible(False)
    if hasattr(self, "universe_answer"):
        self.universe_answer.setVisible(False)


def _toggle_universe_passages(self, checked=False):
    if hasattr(self, "universe_passages"):
        self.universe_passages.setVisible(bool(checked))
    if hasattr(self, "universe_passages_toggle"):
        self.universe_passages_toggle.setText(
            _u_text("Retrieved passages from the paper (open)", "已检索到的论文段落（已展开）") if checked else _u_text("Retrieved passages from the paper", "已检索到的论文段落")
        )


def _focus_universe_topic(self):
    raw_query = self.universe_search.text().strip()
    query = raw_query.lower()
    if not query:
        return
    topic_context = {"Antarctic Ice Sheet": "Antarctic climate ice sheet"}
    for area_name, meta in RESEARCH_AREAS.items():
        topic_context[area_name] = f"{meta['question']} {meta['why']}"
        for name, detail in meta["topics"].items():
            topic_context[name] = f"{area_name} {detail}"
    best_name, best_score = match_topic(
        raw_query,
        self.topic_names,
        topic_keywords=UNIVERSE_TOPIC_KEYWORDS,
        topic_context=topic_context,
    )
    backend = combo_current_key(self.universe_backend) if hasattr(self, "universe_backend") else "Evidence only"
    source = "keyword_fallback"
    if backend != "Evidence only":
        if backend in ["DeepSeek API", "OpenAI API"] and not self._universe_api_key(backend):
            self._set_universe_backend_info(_u_text(
                f"{backend} cannot classify this question yet because the API key is not configured.",
                f"{backend} 暂时无法分类这个问题，因为 API 密钥尚未配置。",
            ), "failed")
        else:
            self._start_universe_ai_classification(raw_query, backend, best_name, best_score)
            return
    self.universe_map.set_focus(best_name, pulse=True)
    parent = next((area for area, meta in RESEARCH_AREAS.items() if best_name in meta["topics"]), "Core system" if best_name == "Antarctic Ice Sheet" else "Research area")
    display = _u_display_module(parent, best_name)
    if hasattr(self, "universe_match_label"):
        if backend == "Evidence only":
            self.universe_match_label.setText(_u_text(
                f"This question matches {display}. Evidence-only mode used keyword matching; paper passages appear below.",
                f"这个问题匹配到 {display}。纯证据模式使用关键词匹配，论文段落会显示在下方。",
            ))
        else:
            self.universe_match_label.setText(_u_text(
                f"{backend} was unavailable, so this question fell back to {display}.",
                f"{backend} 暂不可用，因此这个问题回退匹配到 {display}。",
            ))
    self._render_universe_context(best_name, raw_query, best_score=best_score, classifier_source=source)


def _start_universe_ai_classification(self, raw_query, backend, fallback_name, fallback_score):
    self._universe_classifier_token += 1
    token = self._universe_classifier_token
    model = self._universe_model(backend)
    api_key = self._universe_api_key(backend) if backend in ("DeepSeek API", "OpenAI API") else ""
    self.universe_focus_button.setEnabled(False)
    self.universe_match_label.setText(_u_text(
        f"{backend} / {model} is identifying the best knowledge module...",
        f"{backend} / {model} 正在识别最匹配的知识模块...",
    ))
    self._set_universe_work_status(_u_text(
        f"{backend} / {model}: classifying the question before moving the Universe map.",
        f"{backend} / {model}：正在分类问题，随后移动 Universe 图谱。",
    ), True)
    self.universe_evidence.setVisible(True)
    self.universe_evidence.setHtml(
        "<div class='ios-kicker'>AI MODULE MATCHING</div>"
        f"<h2>{html.escape(_u_text(f'{backend} is reading the question', f'{backend} 正在读取问题'))}</h2>"
        f"<p>{html.escape(_u_text('The selected AI model is choosing the closest Research Universe knowledge module. The map will move after the model returns.', '已选 AI 模型正在选择最接近的研究宇宙知识模块。模型返回后图谱会自动移动。'))}</p>"
    )
    self.universe_answer_progress.setVisible(True)
    self.universe_answer_progress.setRange(0, 0)
    worker = FunctionWorker(self._classify_universe_topic_with_backend, raw_query, backend, api_key, model)
    self._universe_classifier_worker = worker
    worker.resultReady.connect(
        lambda result, token=token, backend=backend, query=raw_query, fallback_name=fallback_name, fallback_score=fallback_score:
            self._finish_universe_ai_classification(token, backend, query, fallback_name, fallback_score, result)
    )
    worker.errorReady.connect(
        lambda message, token=token, backend=backend, query=raw_query, fallback_name=fallback_name, fallback_score=fallback_score:
            self._fail_universe_ai_classification(token, backend, query, fallback_name, fallback_score, message)
    )
    self._universe_workers.append(worker)
    worker.finished.connect(lambda worker=worker: self._cleanup_universe_worker(worker))
    worker.finished.connect(worker.deleteLater)
    worker.start()


def _finish_universe_ai_classification(self, token, backend, raw_query, fallback_name, fallback_score, result):
    if getattr(self, "_shutting_down", False) or token != self._universe_classifier_token:
        return
    self.universe_focus_button.setEnabled(True)
    self.universe_answer_progress.setRange(0, 100)
    self.universe_answer_progress.setVisible(False)
    self._set_universe_work_status("", False)
    if result:
        best_name, confidence = result
        best_score = max(fallback_score, int(float(confidence or 0) * 100))
        source = backend
    else:
        best_name = fallback_name
        best_score = fallback_score
        source = "keyword_fallback"
    self.universe_map.set_focus(best_name, pulse=True)
    parent = next((area for area, meta in RESEARCH_AREAS.items() if best_name in meta["topics"]), "Core system" if best_name == "Antarctic Ice Sheet" else "Research area")
    display = _u_display_module(parent, best_name)
    if source == backend:
        self.universe_match_label.setText(_u_text(
            f"{backend} matched this question to {display}. Confidence: {best_score}%.",
            f"{backend} 将这个问题匹配到 {display}。置信度：{best_score}%。",
        ))
    else:
        self.universe_match_label.setText(_u_text(
            f"{backend} returned no valid module, so the app fell back to {display}.",
            f"{backend} 没有返回有效模块，因此应用回退匹配到 {display}。",
        ))
    self._render_universe_context(best_name, raw_query, best_score=best_score, classifier_source=source)


def _fail_universe_ai_classification(self, token, backend, raw_query, fallback_name, fallback_score, message):
    if getattr(self, "_shutting_down", False) or token != self._universe_classifier_token:
        return
    self.universe_focus_button.setEnabled(True)
    self.universe_answer_progress.setRange(0, 100)
    self.universe_answer_progress.setVisible(False)
    self._set_universe_work_status(_u_text(
        f"{backend} could not classify the question: {message}",
        f"{backend} 无法分类这个问题：{message}",
    ), True)
    self.universe_map.set_focus(fallback_name, pulse=True)
    parent = next((area for area, meta in RESEARCH_AREAS.items() if fallback_name in meta["topics"]), "Core system" if fallback_name == "Antarctic Ice Sheet" else "Research area")
    display = _u_display_module(parent, fallback_name)
    self.universe_match_label.setText(_u_text(
        f"{backend} classification failed, so the app used local fallback: {display}.",
        f"{backend} 分类失败，因此应用使用本地回退匹配：{display}。",
    ))
    self._render_universe_context(fallback_name, raw_query, best_score=fallback_score, classifier_source="keyword_fallback")


def _render_universe_context(self, topic, query="", best_score=0, classifier_source="keyword_fallback"):
    parent = next(
        (area for area, meta in RESEARCH_AREAS.items() if topic in meta["topics"]),
        "Core system" if topic == "Antarctic Ice Sheet" else "Research area",
    )
    topic_text = ""
    for area_name, meta in RESEARCH_AREAS.items():
        if topic == area_name:
            topic_text = f"{meta['question']} {meta['why']}"
        elif topic in meta["topics"]:
            topic_text = meta["topics"][topic]
    search_query = query or topic
    topic_keywords = [topic]
    if parent not in ["Core system", "Research area"]:
        topic_keywords.append(parent)
    if topic in UNIVERSE_TOPIC_KEYWORDS:
        topic_keywords.extend(UNIVERSE_TOPIC_KEYWORDS.get(topic, []))
    paper_keywords = list(dict.fromkeys(
        extract_paper_keywords(search_query)
        + extract_paper_keywords(" ".join(topic_keywords))
        + [term.lower() for term in topic_keywords if len(term) > 1]
    ))
    scored_pages = scored_search_pages_by_keywords(self.pages, paper_keywords, max_results=5) if self.pages else []
    if not scored_pages and self.pages:
        scored_pages = scored_search_pages(self.pages, search_query, max_results=5)
    if self.pages and is_overview_question(search_query):
        intro_pages = [(100 - page.page, page) for page in self.pages[:5]]
        seen_pages = {page.page for _, page in intro_pages}
        useful_matches = [
            (score, page)
            for score, page in scored_pages
            if page.page not in seen_pages and not is_low_value_reference_page(page.text)
        ]
        scored_pages = (intro_pages + useful_matches)[:5]
    snippets = []
    retrieved_passages = []
    for score, page in scored_pages:
        excerpt_text = extract_search_window(page.text, paper_keywords, radius=650)
        retrieved_passages.append({"page": page.page, "text": excerpt_text, "score": score})
        excerpt = html.escape(excerpt_text)
        page_label = _u_text(f"PAGE {page.page} | SCORE {score}", f"第 {page.page} 页 | 匹配分 {score}")
        snippets.append(f'<div class="ios-result-card"><div class="ios-kicker">{html.escape(page_label)}</div><p>{excerpt}</p></div>')
    display = _u_display_module(parent, topic)
    match_note = _u_text(
        "Evidence-only mode used keyword matching.",
        "纯证据模式使用关键词匹配。",
    ) if classifier_source in ["keyword_fallback", "manual"] else _u_text(
        f"{classifier_source} selected this module, with local retrieval as the evidence layer.",
        f"{classifier_source} 选择了这个模块，并使用本地检索作为证据层。",
    )
    self.universe_evidence.setHtml(
        f"<div class='ios-kicker'>EVIDENCE AND AI ANSWER</div><h2>{html.escape(display)}</h2>"
        f"<p><b>{html.escape(_u_text('Matched question:', '匹配问题：'))}</b> {html.escape(query or _u_display_name(topic))}</p>"
        f"<p>{html.escape(match_note)} {html.escape(_u_text(f'Match score: {best_score}.', f'匹配分：{best_score}。'))}</p>"
    )
    self.universe_evidence.setVisible(True)
    if hasattr(self, "universe_passages_toggle"):
        has_results = bool(scored_pages)
        self.universe_passages_toggle.setChecked(False)
        self.universe_passages_toggle.setVisible(True)
        self.universe_passages_toggle.setEnabled(has_results)
        self.universe_passages_toggle.setText(_u_text("Retrieved passages from the paper", "已检索到的论文段落"))
    if hasattr(self, "universe_passages"):
        passages = "".join(snippets) or f"<p>{html.escape(_u_text('No relevant passages found. Try grounding line, basal melt, CDW, ice shelf, GRACE, or paleoclimate.', '未找到相关段落。可以尝试“接地线”“基底融化”“CDW”“冰架”“GRACE”或“古气候”等关键词。'))}</p>"
        self.universe_passages.setHtml(passages)
        self.universe_passages.setVisible(False)
    if hasattr(self, "universe_answer"):
        backend = combo_current_key(self.universe_backend) if hasattr(self, "universe_backend") else "Evidence only"
        if backend != "Evidence only":
            self._stop_universe_answer_typewriter()
            self._universe_answer_token += 1
            token = self._universe_answer_token
            model = self._universe_model(backend)
            self._set_universe_work_status(_u_text(
                f"{backend} / {model}: generating a grounded answer from retrieved passages...",
                f"{backend} / {model}：正在基于检索段落生成有依据的回答...",
            ), True)
            self.universe_answer_progress.setVisible(True)
            self.universe_answer_progress.setRange(0, 0)
            self.universe_answer.setVisible(True)
            self._universe_stream_prefix = (
                f"{_u_text('AI ANSWER', 'AI 答案')}\n\n"
                f"### {_u_text(f'Generating with {backend}', f'正在使用 {backend} 生成')}\n\n"
                f"**{_u_text('Backend:', '后端：')}** {backend} / {model}\n\n"
            )
            self._universe_stream_answer = ""
            self._set_universe_answer_markdown(self._universe_stream_prefix)
            answer_api_key = self._universe_api_key(backend) if backend in ("DeepSeek API", "OpenAI API") else ""
            worker = StreamWorker(
                self._stream_universe_answer,
                backend,
                topic,
                query or topic_text or topic,
                retrieved_passages[:4],
                display,
                answer_api_key,
                model,
            )
            self._universe_answer_worker = worker
            worker.chunkReady.connect(lambda piece, token=token: self._append_universe_answer_chunk(token, piece))
            worker.resultReady.connect(lambda answer, token=token, backend=backend: self._finish_universe_stream_answer(token, backend, str(answer)))
            worker.errorReady.connect(
                lambda message, token=token, backend=backend: self._fail_universe_answer(token, backend, message)
            )
            self._universe_workers.append(worker)
            worker.finished.connect(lambda worker=worker: self._cleanup_universe_worker(worker))
            worker.finished.connect(worker.deleteLater)
            worker.start()
        else:
            self._stop_universe_answer_typewriter()
            self.universe_answer_progress.setVisible(False)
            self.universe_answer_progress.setRange(0, 100)
            self._set_universe_work_status("", False)
            self.universe_answer.setHtml(
                "<div class='ios-kicker'>AI ANSWER</div><h3>Evidence-only mode</h3>"
                f"<p>{html.escape(_u_text('Select Local Ollama, DeepSeek API, or OpenAI API to generate an answer from the retrieved passages.', '请选择本地 Ollama、DeepSeek API 或 OpenAI API，以基于检索段落生成回答。'))}</p>"
            )
        self.universe_answer.setVisible(True)


def _append_universe_answer_chunk(self, token, piece):
    if getattr(self, "_shutting_down", False) or token != self._universe_answer_token:
        return
    self._universe_stream_answer += str(piece)
    if hasattr(self, "universe_answer"):
        self._set_universe_answer_markdown(f"{self._universe_stream_prefix}{self._universe_stream_answer}")
        self.universe_answer.verticalScrollBar().setValue(self.universe_answer.verticalScrollBar().maximum())


def _finish_universe_stream_answer(self, token, backend, answer):
    if getattr(self, "_shutting_down", False) or token != self._universe_answer_token:
        return
    if answer and not self._universe_stream_answer:
        self._universe_stream_answer = answer
    visible = self._universe_stream_answer or answer or _u_text("The backend returned an empty answer.", "后端返回了空回答。")
    self.universe_answer_progress.setRange(0, 100)
    self.universe_answer_progress.setValue(100)
    self.universe_answer_progress.setVisible(False)
    self._set_universe_work_status(_u_text(
        f"{backend}: streaming answer complete.",
        f"{backend}：流式回答已完成。",
    ), True)
    if hasattr(self, "universe_answer"):
        self._set_universe_answer_markdown(f"{self._universe_stream_prefix}{visible}")
        self.universe_answer.verticalScrollBar().setValue(self.universe_answer.verticalScrollBar().maximum())


def _stop_universe_answer_typewriter(self, clear=True):
    if hasattr(self, "_universe_type_timer") and self._universe_type_timer.isActive():
        self._universe_type_timer.stop()
    if clear:
        self._universe_type_answer = ""
        self._universe_type_index = 0


def _fail_universe_answer(self, token, backend, message):
    if getattr(self, "_shutting_down", False) or token != self._universe_answer_token:
        return
    self._stop_universe_answer_typewriter()
    self.universe_answer_progress.setRange(0, 100)
    self.universe_answer_progress.setValue(0)
    self._set_universe_work_status(_u_text(
        f"{backend}: answer generation failed.",
        f"{backend}：回答生成失败。",
    ), True)
    self.universe_answer.setHtml(
        f"<div class='ios-kicker'>AI ANSWER</div><h3>{html.escape(_u_text(f'{backend} could not generate yet', f'{backend} 暂时无法生成回答'))}</h3>"
        f"<p>{html.escape(str(message))}</p>"
        f"<p>{html.escape(_u_text('Evidence retrieval above is still available. Check that the local model is running or that the API key is valid.', '上方的证据检索仍然可用。请检查本地模型是否正在运行，或 API 密钥是否有效。'))}</p>"
    )
