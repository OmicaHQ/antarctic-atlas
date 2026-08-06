"""Dependency-free AI backend client for Ollama / DeepSeek / OpenAI.

No Qt or Streamlit imports — presentation (Streamlit widgets, Qt signals) is
handled by the calling surface. All functions take plain values and return
plain values, so they can run on any thread.
"""
import json
import os
import re

import requests

from config import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    OLLAMA_MODEL,
    OLLAMA_URL,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

BACKEND_OLLAMA = "Local Ollama"
BACKEND_DEEPSEEK = "DeepSeek API"
BACKEND_OPENAI = "OpenAI API"
BACKENDS = (BACKEND_OLLAMA, BACKEND_DEEPSEEK, BACKEND_OPENAI)

_ENV_KEY = {
    BACKEND_DEEPSEEK: "DEEPSEEK_API_KEY",
    BACKEND_OPENAI: "OPENAI_API_KEY",
}


def default_model(backend):
    if backend == BACKEND_DEEPSEEK:
        return DEEPSEEK_MODEL
    if backend == BACKEND_OPENAI:
        return OPENAI_MODEL
    return OLLAMA_MODEL


def env_api_key(backend):
    var = _ENV_KEY.get(backend)
    return os.environ.get(var, "").strip() if var else ""


def check_ollama():
    """Return (ok, model_names, error). ok is True only when OLLAMA_MODEL is
    actually served — callers render 'connected' / 'not ready' status off this."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        model_names = [m.get("name") for m in r.json().get("models", [])]
        return OLLAMA_MODEL in model_names, model_names, None
    except Exception as exc:
        return False, [], str(exc)


def apply_deepseek_v4_defaults(payload, model):
    if str(model or "").startswith("deepseek-v4-"):
        payload.setdefault("thinking", {"type": "disabled"})
    return payload


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


def extract_backend_text(backend, response_json):
    if backend == BACKEND_OLLAMA:
        return str(response_json.get("response", "")).strip()
    if backend == BACKEND_DEEPSEEK:
        return str(response_json.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
    if backend == BACKEND_OPENAI:
        return extract_openai_text(response_json)
    return ""


def _headers(api_key):
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _ollama_payload(model, prompt, system, temperature, stream):
    return {
        "model": model or OLLAMA_MODEL,
        "prompt": f"{system}\n\n{prompt}" if system else prompt,
        "stream": stream,
        "options": {"temperature": temperature, "num_ctx": 4096, "num_gpu": -1},
    }


def _deepseek_payload(model, prompt, system, temperature, max_tokens, stream):
    payload = {
        "model": model or DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system or "You are a careful scientific reading assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    return apply_deepseek_v4_defaults(payload, model or DEEPSEEK_MODEL)


def _openai_payload(model, prompt, system, max_tokens):
    return {
        "model": model or OPENAI_MODEL,
        "input": [
            {"role": "system", "content": system or "You are a careful scientific reading assistant."},
            {"role": "user", "content": prompt},
        ],
        "max_output_tokens": max_tokens,
    }


def _chat_ollama(prompt, system, model, temperature, timeout, on_chunk=None):
    payload = _ollama_payload(model, prompt, system, temperature, stream=on_chunk is not None)
    with requests.post(f"{OLLAMA_URL}/api/generate", json=payload, stream=on_chunk is not None, timeout=timeout) as r:
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
        if on_chunk is None:
            return extract_backend_text(BACKEND_OLLAMA, r.json())
        answer = ""
        for raw_line in r.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            try:
                data = json.loads(raw_line)
            except Exception:
                continue
            piece = data.get("response", "") or ""
            if piece:
                answer += piece
                on_chunk(piece)
            if data.get("done"):
                break
        return answer.strip()


def _chat_deepseek(prompt, system, model, api_key, max_tokens, temperature, timeout, on_chunk=None):
    payload = _deepseek_payload(model, prompt, system, temperature, max_tokens, stream=on_chunk is not None)
    with requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers=_headers(api_key),
        json=payload,
        stream=on_chunk is not None,
        timeout=timeout,
    ) as r:
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
        if on_chunk is None:
            return extract_backend_text(BACKEND_DEEPSEEK, r.json())
        answer = ""
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
            piece = data.get("choices", [{}])[0].get("delta", {}).get("content", "") or ""
            if piece:
                answer += piece
                on_chunk(piece)
        return answer.strip()


def _chat_openai(prompt, system, model, api_key, max_tokens, timeout, on_chunk=None):
    payload = _openai_payload(model, prompt, system, max_tokens)
    r = requests.post(f"{OPENAI_BASE_URL}/responses", headers=_headers(api_key), json=payload, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
    text = extract_openai_text(r.json())
    if on_chunk is not None and text:
        on_chunk(text)
    return text


def chat(backend, prompt, *, system="", model=None, api_key="", max_tokens=1200, temperature=0.2, timeout=120, on_chunk=None):
    """Call a backend and return the full response text.

    If on_chunk is provided, the call streams and on_chunk(str) fires per piece.
    api_key may be empty for the local Ollama backend.
    """
    model = model or default_model(backend)
    if backend == BACKEND_OLLAMA:
        return _chat_ollama(prompt, system=system, model=model, temperature=temperature, timeout=timeout, on_chunk=on_chunk)
    key = (api_key or env_api_key(backend)).strip()
    if not key:
        raise RuntimeError(f"{backend} API key is missing.")
    if backend == BACKEND_DEEPSEEK:
        return _chat_deepseek(prompt, system=system, model=model, api_key=key, max_tokens=max_tokens, temperature=temperature, timeout=timeout, on_chunk=on_chunk)
    if backend == BACKEND_OPENAI:
        return _chat_openai(prompt, system=system, model=model, api_key=key, max_tokens=max_tokens, timeout=timeout, on_chunk=on_chunk)
    raise RuntimeError("AI backend is not enabled.")


def test_connection(backend, model=None, api_key=""):
    """Actively test a backend. Returns (ok: bool, message: str)."""
    model = model or default_model(backend)
    if backend == BACKEND_OLLAMA:
        ok, models, err = check_ollama()
        if not ok:
            return False, f"Local Ollama / {model}: {err or 'no models available'}"
        return True, f"Local Ollama / {model}: connected."
    key = (api_key or env_api_key(backend)).strip()
    if not key:
        return False, f"{backend} API key not configured."
    try:
        text = chat(
            backend,
            "Reply with exactly: connection-ok",
            system="You are a connectivity probe. Reply with one short sentence only.",
            model=model,
            api_key=key,
            max_tokens=48,
            temperature=0.0,
            timeout=35,
        )
    except Exception as exc:
        return False, f"{backend} / {model}: request failed. {exc}"
    if text.strip():
        return True, f"{backend} / {model}: connected. Model replied: {text.strip()[:80]}"
    return False, f"{backend} / {model}: request completed but the model returned no readable text."


def classifier_prompt(question, allowed_nodes):
    """Build the strict-classifier prompt. allowed_nodes: list of (name, parent)."""
    topic_lines = [f"- {name} | parent: {parent}" for name, parent in allowed_nodes]
    return (
        "Choose exactly ONE best matching node from the allowed Antarctic Ice Sheet research graph. "
        "Return only JSON in this form: {\"topic\":\"one allowed node name\", \"confidence\":0.0}.\n\n"
        f"Allowed nodes:\n{chr(10).join(topic_lines)}\n\nQuestion:\n{question}"
    )


def parse_classification(raw):
    """Parse a classifier response into (topic, confidence) or None."""
    match = re.search(r"\{.*\}", str(raw or ""), re.S)
    try:
        obj = json.loads(match.group(0) if match else raw)
    except Exception:
        return None
    topic = str(obj.get("topic", "")).strip()
    if not topic:
        return None
    try:
        confidence = float(obj.get("confidence", 0) or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    return topic, confidence


def classify(question, allowed_nodes, backend, model=None, api_key=""):
    """Ask a backend to choose one allowed node. Returns (topic, confidence) or None.

    topic is matched case-insensitively against the allowed node names.
    """
    if not allowed_nodes:
        return None
    prompt = classifier_prompt(question, allowed_nodes)
    try:
        raw = chat(
            backend,
            prompt,
            system="Return only valid JSON. Do not explain.",
            model=model,
            api_key=api_key,
            max_tokens=220,
            temperature=0.0,
        )
    except Exception:
        return None
    parsed = parse_classification(raw)
    if not parsed:
        return None
    topic, confidence = parsed
    valid = [name for name, _ in allowed_nodes]
    if topic not in valid:
        lowered = {name.lower(): name for name in valid}
        topic = lowered.get(topic.lower(), "")
    if topic in valid:
        return topic, confidence
    return None
