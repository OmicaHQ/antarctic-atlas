import json
import os
import re

import requests
import streamlit as st

from .config import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    OLLAMA_MODEL,
    OLLAMA_URL,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)


def check_ollama():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = r.json().get("models", [])
        model_names = [m.get("name") for m in models]
        return OLLAMA_MODEL in model_names, model_names, None
    except Exception as e:
        return False, [], str(e)


def get_selected_deepseek_model():
    """Return the currently selected DeepSeek model."""
    return st.session_state.get("deepseek_model_select", DEEPSEEK_MODEL)


def apply_deepseek_v4_defaults(payload, model):
    if str(model or "").startswith("deepseek-v4-"):
        payload.setdefault("thinking", {"type": "disabled"})
    return payload


def get_deepseek_api_key():
    """Read DeepSeek API key from Streamlit secrets, environment variable, or saved session state."""
    try:
        key = st.secrets.get("DEEPSEEK_API_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key.strip()
    return st.session_state.get("deepseek_api_key_saved", "").strip()


def test_deepseek_connection(api_key=None, model=None):
    """Actively test whether the DeepSeek API key and selected model work."""
    key = (api_key or get_deepseek_api_key()).strip()
    selected_model = model or get_selected_deepseek_model()
    if not key:
        return False, "DeepSeek API key not configured."
    payload = apply_deepseek_v4_defaults({
        "model": selected_model,
        "messages": [
            {"role": "system", "content": "Reply with pong only."},
            {"role": "user", "content": "ping"},
        ],
        "temperature": 0,
        "max_tokens": 8,
        "stream": False,
    }, selected_model)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        r = requests.post(f"{DEEPSEEK_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=25)
        if r.status_code == 200:
            return True, "DeepSeek API connected."
        return False, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return False, str(e)


def check_deepseek(api_key=None):
    key = (api_key or get_deepseek_api_key()).strip()
    if not key:
        return False, "DeepSeek API key not configured."
    if st.session_state.get("deepseek_verified", False):
        return True, None
    return True, "DeepSeek API key is present but not verified in this session."


def get_selected_openai_model():
    """Return the currently selected OpenAI model."""
    return st.session_state.get("openai_model_select", OPENAI_MODEL)


def get_openai_api_key():
    """Read OpenAI API key from Streamlit secrets, environment variable, or saved session state."""
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        return key.strip()
    return st.session_state.get("openai_api_key_saved", "").strip()


def extract_openai_text(response_json):
    """Extract text from an OpenAI Responses API response."""
    if not isinstance(response_json, dict):
        return ""
    if response_json.get("output_text"):
        return str(response_json.get("output_text", ""))
    chunks = []
    for item in response_json.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") in ["output_text", "text"] and content.get("text"):
                chunks.append(str(content.get("text")))
    return "".join(chunks).strip()


def test_openai_connection(api_key=None, model=None):
    """Actively test whether the OpenAI API key and selected model work."""
    key = (api_key or get_openai_api_key()).strip()
    selected_model = model or get_selected_openai_model()
    if not key:
        return False, "OpenAI API key not configured."
    payload = {
        "model": selected_model,
        "input": "Reply with pong only.",
        "max_output_tokens": 12,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        r = requests.post(f"{OPENAI_BASE_URL}/responses", headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            return True, "OpenAI API connected."
        return False, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return False, str(e)


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


def stream_deepseek(question, passages, text_box, progress_bar, answer_prefix="", api_key=None):
    key = (api_key or get_deepseek_api_key()).strip()
    if not key:
        raise RuntimeError("Missing DeepSeek API key. Add DEEPSEEK_API_KEY to .streamlit/secrets.toml, set an environment variable, or enter it in the app.")

    prompt = build_paper_prompt(question, passages)
    answer = answer_prefix.strip() + ("\n\n" if answer_prefix.strip() else "")
    if answer:
        text_box.markdown(answer)

    selected_model = get_selected_deepseek_model()
    payload = apply_deepseek_v4_defaults({
        "model": selected_model,
        "messages": [
            {"role": "system", "content": "You are a careful scientific reading assistant. Answer in Chinese, keep key scientific terms in English, and stay grounded in the provided excerpts."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "stream": True,
    }, selected_model)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    estimated_chars = 2500
    with requests.post(f"{DEEPSEEK_BASE_URL}/chat/completions", headers=headers, json=payload, stream=True, timeout=600) as r:
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
        for raw_line in r.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            line = raw_line.strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
            except Exception:
                continue
            delta = data.get("choices", [{}])[0].get("delta", {})
            piece = delta.get("content", "") or ""
            if piece:
                answer += piece
                text_box.markdown(answer)
                progress_bar.progress(min(len(answer) / estimated_chars, 1.0))
    progress_bar.progress(1.0)
    return answer


def stream_openai(question, passages, text_box, progress_bar, answer_prefix="", api_key=None):
    key = (api_key or get_openai_api_key()).strip()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Add OPENAI_API_KEY to .streamlit/secrets.toml, set an environment variable, or enter it in the app.")

    prompt = build_paper_prompt(question, passages)
    answer = answer_prefix.strip() + ("\n\n" if answer_prefix.strip() else "")
    if answer:
        text_box.markdown(answer)
    progress_bar.progress(0.08)

    payload = {
        "model": get_selected_openai_model(),
        "input": [
            {
                "role": "system",
                "content": "You are a careful scientific reading assistant. Answer in Chinese, keep key scientific terms in English, and stay grounded in the provided excerpts.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "max_output_tokens": 1800,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    r = requests.post(f"{OPENAI_BASE_URL}/responses", headers=headers, json=payload, timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
    progress_bar.progress(0.75)
    generated = extract_openai_text(r.json())
    answer += generated
    text_box.markdown(answer)
    progress_bar.progress(1.0)
    return answer


def classify_universe_question_with_openai(question, topic_index, api_key=None):
    key = (api_key or get_openai_api_key()).strip()
    if not key:
        return None
    valid_topics = list(topic_index.keys())
    topic_lines = []
    for topic in valid_topics:
        parent = topic_index.get(topic, {}).get("parent", "Research area")
        topic_lines.append(f"- {topic} | parent: {parent}")
    prompt = f"""
You are a strict classifier for an Antarctic Ice Sheet research knowledge graph.
Choose exactly ONE best matching node from the allowed node list.
Return only valid JSON. Do not explain.

Allowed nodes:
{chr(10).join(topic_lines)}

Question:
{question}

Return JSON in this exact format:
{{"topic":"one allowed node name", "confidence":0.0}}
"""
    payload = {
        "model": get_selected_openai_model(),
        "input": [
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "max_output_tokens": 200,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        r = requests.post(f"{OPENAI_BASE_URL}/responses", headers=headers, json=payload, timeout=90)
        r.raise_for_status()
        raw = extract_openai_text(r.json()).strip()
        match = re.search(r"\{.*\}", raw, re.S)
        obj = json.loads(match.group(0) if match else raw)
        topic = str(obj.get("topic", "")).strip()
        confidence = float(obj.get("confidence", 0.0) or 0.0)
        if topic not in valid_topics:
            lowered = {t.lower(): t for t in valid_topics}
            topic = lowered.get(topic.lower(), "")
        if topic in valid_topics:
            return topic, topic_index.get(topic, {}).get("parent", "Research area"), confidence, "openai"
    except Exception:
        return None
    return None


def classify_universe_question_with_deepseek(question, topic_index, api_key=None):
    key = (api_key or get_deepseek_api_key()).strip()
    if not key:
        return None
    valid_topics = list(topic_index.keys())
    topic_lines = []
    for topic in valid_topics:
        parent = topic_index.get(topic, {}).get("parent", "Research area")
        topic_lines.append(f"- {topic} | parent: {parent}")
    prompt = f"""
You are a strict classifier for an Antarctic Ice Sheet research knowledge graph.
Choose exactly ONE best matching node from the allowed node list.
Return only valid JSON. Do not explain.

Allowed nodes:
{chr(10).join(topic_lines)}

Question:
{question}

Return JSON in this exact format:
{{"topic":"one allowed node name", "confidence":0.0}}
"""
    selected_model = get_selected_deepseek_model()
    payload = apply_deepseek_v4_defaults({
        "model": selected_model,
        "messages": [
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "stream": False,
        "response_format": {"type": "json_object"},
    }, selected_model)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        r = requests.post(f"{DEEPSEEK_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=90)
        r.raise_for_status()
        raw = r.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        match = re.search(r"\{.*\}", raw, re.S)
        obj = json.loads(match.group(0) if match else raw)
        topic = str(obj.get("topic", "")).strip()
        confidence = float(obj.get("confidence", 0.0) or 0.0)
        if topic not in valid_topics:
            lowered = {t.lower(): t for t in valid_topics}
            topic = lowered.get(topic.lower(), "")
        if topic in valid_topics:
            return topic, topic_index.get(topic, {}).get("parent", "Research area"), confidence, "deepseek"
    except Exception:
        return None
    return None


def stream_ai_answer(backend, question, passages, text_box, progress_bar, answer_prefix=""):
    if backend == "DeepSeek API":
        return stream_deepseek(question, passages, text_box, progress_bar, answer_prefix=answer_prefix)
    if backend == "OpenAI API":
        return stream_openai(question, passages, text_box, progress_bar, answer_prefix=answer_prefix)
    return stream_ollama(question, passages, text_box, progress_bar, answer_prefix=answer_prefix)


def stream_ollama(question, passages, text_box, progress_bar, answer_prefix=""):
    context = "\n\n".join([f"Page {r['page']}:\n{r['text'][:1000]}" for r in passages[:3]])
    prompt = f"""
You are helping a student understand a review paper about the Antarctic Ice Sheet.
Use ONLY the excerpts below.
Answer in Chinese, but keep important scientific terms in English.
If an answer prefix is provided by the app, continue after it and do not repeat it.

Question:
{question}

Paper excerpts:
{context}
"""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.2, "num_ctx": 4096, "num_gpu": -1},
    }

    answer = answer_prefix.strip() + ("\n\n" if answer_prefix.strip() else "")
    if answer:
        text_box.markdown(answer)
    estimated_chars = 2500

    with requests.post(f"{OLLAMA_URL}/api/generate", json=payload, stream=True, timeout=600) as r:
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
        for line in r.iter_lines():
            if not line:
                continue
            data = json.loads(line.decode("utf-8"))
            piece = data.get("response", "")
            answer += piece
            text_box.markdown(answer)
            progress_bar.progress(min(len(answer) / estimated_chars, 1.0))
            if data.get("done", False):
                break

    progress_bar.progress(1.0)
    return answer
