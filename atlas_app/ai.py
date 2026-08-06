"""Streamlit AI helpers — thin wrappers over the shared core.ai client.

The HTTP/payload/parsing logic lives in core/ai.py (dependency-free). This module
keeps only the Streamlit-coupled bits: key lookups via st.secrets/st.session_state
and widget-drawing stream helpers for the legacy web app.
"""
import os

import streamlit as st

from .config import DEEPSEEK_MODEL, OPENAI_MODEL
from core.ai import (
    BACKEND_DEEPSEEK,
    BACKEND_OPENAI,
    BACKEND_OLLAMA,
    apply_deepseek_v4_defaults,
    chat,
    check_ollama,
    classify,
    env_api_key,
    extract_openai_text,
    test_connection,
)

__all__ = [
    "apply_deepseek_v4_defaults",
    "check_ollama",
    "extract_openai_text",
    "stream_ai_answer",
    "stream_deepseek",
    "stream_ollama",
    "stream_openai",
    "test_deepseek_connection",
    "test_openai_connection",
    "classify_universe_question_with_deepseek",
    "classify_universe_question_with_openai",
    "get_deepseek_api_key",
    "get_openai_api_key",
]


def get_deepseek_api_key():
    """Read DeepSeek API key from Streamlit secrets, environment variable, or saved session state."""
    try:
        key = st.secrets.get("DEEPSEEK_API_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass
    return env_api_key(BACKEND_DEEPSEEK) or st.session_state.get("deepseek_api_key_saved", "").strip()


def get_openai_api_key():
    """Read OpenAI API key from Streamlit secrets, environment variable, or saved session state."""
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass
    return env_api_key(BACKEND_OPENAI) or st.session_state.get("openai_api_key_saved", "").strip()


def get_selected_deepseek_model():
    """Return the currently selected DeepSeek model."""
    return st.session_state.get("deepseek_model_select", DEEPSEEK_MODEL)


def get_selected_openai_model():
    """Return the currently selected OpenAI model."""
    return st.session_state.get("openai_model_select", OPENAI_MODEL)


def test_deepseek_connection(api_key=None, model=None):
    """Actively test whether the DeepSeek API key and selected model work."""
    key = (api_key or get_deepseek_api_key()).strip()
    if not key:
        return False, "DeepSeek API key not configured."
    ok, message = test_connection(BACKEND_DEEPSEEK, model=model or get_selected_deepseek_model(), api_key=key)
    return ok, message


def test_openai_connection(api_key=None, model=None):
    """Actively test whether the OpenAI API key and selected model work."""
    key = (api_key or get_openai_api_key()).strip()
    if not key:
        return False, "OpenAI API key not configured."
    ok, message = test_connection(BACKEND_OPENAI, model=model or get_selected_openai_model(), api_key=key)
    return ok, message


def check_deepseek(api_key=None):
    key = (api_key or get_deepseek_api_key()).strip()
    if not key:
        return False, "DeepSeek API key not configured."
    if st.session_state.get("deepseek_verified", False):
        return True, None
    return True, "DeepSeek API key is present but not verified in this session."


def check_openai(api_key=None):
    key = (api_key or get_openai_api_key()).strip()
    if not key:
        return False, "OpenAI API key not configured."
    if st.session_state.get("openai_verified", False):
        return True, None
    return True, "OpenAI API key is present but not verified in this session."


def build_paper_prompt(question, passages):
    context = "\n\n".join([f"Page {r['page']}:\n{r['text'][:1000]}" for r in passages[:3]])
    return f"""
You are helping a student understand a review paper about the Antarctic Ice Sheet.
Use ONLY the excerpts below.
Answer in Chinese, but keep important scientific terms in English.
If an answer prefix is provided by the app, continue after it and do not repeat it.

Question:
{question}

Paper excerpts:
{context}
"""


def _stream_into_widget(backend, on_chunk, question, passages, text_box, progress_bar, answer_prefix="", api_key=None):
    prompt = build_paper_prompt(question, passages)
    answer = answer_prefix.strip() + ("\n\n" if answer_prefix.strip() else "")
    if answer:
        text_box.markdown(answer)
    progress_bar.progress(0.08)
    estimated_chars = 2500

    def on_piece(piece):
        nonlocal answer
        answer += piece
        text_box.markdown(answer)
        progress_bar.progress(min(len(answer) / estimated_chars, 1.0))

    if backend == BACKEND_DEEPSEEK:
        model = get_selected_deepseek_model()
    elif backend == BACKEND_OPENAI:
        model = get_selected_openai_model()
    else:
        # Ollama: pass no model so core.ai falls back to OLLAMA_MODEL. The OpenAI
        # selector default (gpt-4o) is not an Ollama model and 404s.
        model = None
    answer += chat(
        backend,
        prompt,
        system="You are a careful scientific reading assistant. Answer in Chinese, keep key scientific terms in English, and stay grounded in the provided excerpts.",
        model=model,
        api_key=api_key,
        max_tokens=1800,
        temperature=0.2,
        timeout=600,
        on_chunk=on_piece,
    )
    progress_bar.progress(1.0)
    return answer


def stream_deepseek(question, passages, text_box, progress_bar, answer_prefix="", api_key=None):
    key = (api_key or get_deepseek_api_key()).strip()
    if not key:
        raise RuntimeError("Missing DeepSeek API key. Add DEEPSEEK_API_KEY to .streamlit/secrets.toml, set an environment variable, or enter it in the app.")
    return _stream_into_widget(BACKEND_DEEPSEEK, None, question, passages, text_box, progress_bar, answer_prefix, key)


def stream_openai(question, passages, text_box, progress_bar, answer_prefix="", api_key=None):
    key = (api_key or get_openai_api_key()).strip()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Add OPENAI_API_KEY to .streamlit/secrets.toml, set an environment variable, or enter it in the app.")
    return _stream_into_widget(BACKEND_OPENAI, None, question, passages, text_box, progress_bar, answer_prefix, key)


def stream_ollama(question, passages, text_box, progress_bar, answer_prefix=""):
    return _stream_into_widget(BACKEND_OLLAMA, None, question, passages, text_box, progress_bar, answer_prefix)


def stream_ai_answer(backend, question, passages, text_box, progress_bar, answer_prefix=""):
    if backend == BACKEND_DEEPSEEK:
        return stream_deepseek(question, passages, text_box, progress_bar, answer_prefix=answer_prefix)
    if backend == BACKEND_OPENAI:
        return stream_openai(question, passages, text_box, progress_bar, answer_prefix=answer_prefix)
    return stream_ollama(question, passages, text_box, progress_bar, answer_prefix=answer_prefix)


def classify_universe_question_with_openai(question, topic_index, api_key=None):
    key = (api_key or get_openai_api_key()).strip()
    if not key:
        return None
    allowed = [(topic, meta.get("parent", "Research area")) for topic, meta in topic_index.items()]
    result = classify(question, allowed, BACKEND_OPENAI, model=get_selected_openai_model(), api_key=key)
    if not result:
        return None
    topic, confidence = result
    return topic, topic_index.get(topic, {}).get("parent", "Research area"), confidence, "openai"


def classify_universe_question_with_deepseek(question, topic_index, api_key=None):
    key = (api_key or get_deepseek_api_key()).strip()
    if not key:
        return None
    allowed = [(topic, meta.get("parent", "Research area")) for topic, meta in topic_index.items()]
    result = classify(question, allowed, BACKEND_DEEPSEEK, model=get_selected_deepseek_model(), api_key=key)
    if not result:
        return None
    topic, confidence = result
    return topic, topic_index.get(topic, {}).get("parent", "Research area"), confidence, "deepseek"
