import streamlit as st
import streamlit.components.v1 as components
import pdfplumber
import re
import requests
import pandas as pd
import plotly.graph_objects as go
import jieba
import json
import os
import numpy as np
import textwrap
import html
from pathlib import Path

st.set_page_config(page_title="Antarctic Research Atlas", layout="wide", initial_sidebar_state="collapsed")

BASE_DIR = Path(__file__).resolve().parent
PDF_FILENAME = "Reviews of Geophysics - 2020 - Noble - The Sensitivity of the Antarctic Ice Sheet to a Changing Climate  Past  Present  and.pdf"
PDF_PATH = BASE_DIR / PDF_FILENAME
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "gemma4:e4b"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_MODEL = "gpt-4o"
OPENAI_MODEL_OPTIONS = ["gpt-4o", "gpt-4.1"]

@st.cache_data
def load_pdf():
    if not PDF_PATH.exists():
        st.error(
            "Source PDF not found. Put the review paper in the project root with this exact filename: "
            f"{PDF_FILENAME}"
        )
        st.stop()

    pages = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                pages.append({"page": i + 1, "text": text})
    if not pages:
        st.error("The PDF was found, but no readable text could be extracted.")
        st.stop()
    return pages

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

def extract_keywords(question):
    words = list(jieba.cut(question))
    words += re.findall(r"\w+", question)
    return [w for w in words if len(w) > 1]

def search_pages(pages, keywords, max_results=5):
    results = []
    for item in pages:
        text_lower = item["text"].lower()
        score = sum(text_lower.count(k.lower()) for k in keywords)
        if score > 0:
            results.append({"page": item["page"], "score": score, "text": clean_text(item["text"])})
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:max_results]
    if not results:
        for item in pages:
            if item["page"] in [1, 2, 3, 4, 5]:
                results.append({"page": item["page"], "score": 0, "text": clean_text(item["text"])})
    return results

def build_search_excerpt(text, keywords, radius=220):
    cleaned = clean_text(text)
    lowered = cleaned.lower()
    hit_positions = [lowered.find(k.lower()) for k in keywords if k and lowered.find(k.lower()) >= 0]
    if hit_positions:
        center = min(hit_positions)
        start = max(0, center - radius)
        end = min(len(cleaned), center + radius)
    else:
        start, end = 0, min(len(cleaned), radius * 2)
    excerpt = cleaned[start:end]
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(cleaned) else ""
    escaped = html.escape(prefix + excerpt + suffix)
    for keyword in sorted(set(keywords), key=len, reverse=True):
        if len(keyword) > 1:
            escaped = re.sub(
                re.escape(html.escape(keyword)),
                lambda m: f"<mark>{m.group(0)}</mark>",
                escaped,
                flags=re.IGNORECASE,
            )
    return escaped

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
    payload = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": "Reply with pong only."},
            {"role": "user", "content": "ping"}
        ],
        "temperature": 0,
        "max_tokens": 8,
        "stream": False
    }
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
        "max_output_tokens": 12
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

    payload = {
        "model": get_selected_deepseek_model(),
        "messages": [
            {"role": "system", "content": "You are a careful scientific reading assistant. Answer in Chinese, keep key scientific terms in English, and stay grounded in the provided excerpts."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "stream": True
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
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
                "content": "You are a careful scientific reading assistant. Answer in Chinese, keep key scientific terms in English, and stay grounded in the provided excerpts."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_output_tokens": 1800
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
            {"role": "user", "content": prompt}
        ],
        "max_output_tokens": 200
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
    payload = {
        "model": get_selected_deepseek_model(),
        "messages": [
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "stream": False,
        "response_format": {"type": "json_object"}
    }
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
        "options": {"temperature": 0.2, "num_ctx": 4096, "num_gpu": -1}
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

pages = load_pdf()
total_pages = len(pages)

# -----------------------------
# Landing page + project shell
# -----------------------------
if "entered_project" not in st.session_state:
    st.session_state["entered_project"] = False

if not st.session_state["entered_project"]:
    st.markdown("""
    <style>
      [data-testid="stSidebar"] { display: none; }
      [data-testid="collapsedControl"] { display: none; }
      .block-container {
        max-width: 100% !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
      }
      .landing-wrap {
        min-height: 92vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background:
          radial-gradient(circle at 24% 22%, rgba(78,163,241,0.20), transparent 30%),
          radial-gradient(circle at 76% 70%, rgba(149,117,205,0.18), transparent 32%),
          linear-gradient(135deg, #030712 0%, #07111f 45%, #020617 100%);
        border-radius: 28px;
        color: #eef6ff;
        box-shadow: inset 0 0 90px rgba(78,163,241,0.12);
      }
      .landing-card {
        width: min(760px, 92vw);
        padding: 56px 58px;
        border-radius: 30px;
        border: 1px solid rgba(170,215,255,0.22);
        background: linear-gradient(180deg, rgba(8,18,34,0.80), rgba(7,15,29,0.62));
        backdrop-filter: blur(16px);
        box-shadow: 0 24px 80px rgba(0,0,0,0.42);
        text-align: center;
      }
      .landing-card h1 {
        margin: 0;
        font-size: 44px;
        letter-spacing: .2px;
      }
      .landing-card p {
        color: rgba(238,246,255,.78);
        font-size: 16px;
        margin: 18px 0 0 0;
      }
      .pdf-loaded {
        margin: 28px auto 22px auto;
        display: inline-block;
        padding: 10px 16px;
        border-radius: 999px;
        background: rgba(34,197,94,.12);
        border: 1px solid rgba(74,222,128,.28);
        color: #7CFF9B;
        font-weight: 650;
      }
      div.stButton > button {
        border-radius: 999px;
        padding: 0.7rem 1.35rem;
        font-weight: 700;
      }
    </style>
    <div class="landing-wrap">
      <div class="landing-card">
        <h1>&#127758; Antarctic Ice Sheet Research Atlas</h1>
        <p>An interactive research universe for exploring the Antarctic Ice Sheet review paper.</p>
        <div class="pdf-loaded">PDF loaded successfully, __TOTAL_PAGES__ pages</div>
      </div>
    </div>
    """.replace("__TOTAL_PAGES__", str(total_pages)), unsafe_allow_html=True)
    _, c, _ = st.columns([0.42, 0.16, 0.42])
    with c:
        if st.button("Enter Project", type="primary", use_container_width=True):
            st.session_state["entered_project"] = True
            st.rerun()
    st.stop()

st.sidebar.title("Navigation")

# Sidebar keeps clean text labels; page headers keep emoji.
sidebar_module_map = {
    "Research Universe": "Research Universe Explorer",
    "Antarctic System": "Antarctic System Explorer",
    "AI Visualizer": "AI Visualizer",
    "Mini Research Lab": "Mini Research Lab",
    "Research Directions": "Research Directions",
    "Read Raw Paper": "Read Raw Paper",
}
selected_sidebar_label = st.sidebar.radio(
    "Select",
    list(sidebar_module_map.keys()),
    key="sidebar_module_select"
)
module = sidebar_module_map[selected_sidebar_label]

# Global page styling.
# The former floating project topbar has been removed to avoid the black bar above the page title.
st.markdown("""
<style>
  .block-container {
    padding-top: 1.65rem !important;
    max-width: 1280px !important;
  }

  :root {
    --ios-bg-0: #030712;
    --ios-bg-1: #07111f;
    --ios-glass: rgba(11, 23, 43, .62);
    --ios-glass-strong: rgba(15, 31, 56, .78);
    --ios-stroke: rgba(190, 226, 255, .18);
    --ios-stroke-hot: rgba(132, 208, 255, .48);
    --ios-text: #f4f9ff;
    --ios-muted: rgba(220, 236, 248, .70);
    --ios-blue: #5aa7ff;
    --ios-cyan: #7edcff;
    --ios-green: #73f0a2;
    --ios-shadow: 0 24px 70px rgba(0, 0, 0, .34);
    --ios-glass-edge: rgba(225, 244, 255, .26);
    --ios-liquid-sheen: linear-gradient(120deg, transparent 0%, rgba(255,255,255,.13) 28%, rgba(126,220,255,.22) 46%, rgba(255,255,255,.10) 58%, transparent 76%);
  }

  @keyframes iosRiseIn {
    from { opacity: 0; transform: translateY(10px) scale(.992); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
  @keyframes iosSoftPulse {
    0%, 100% { box-shadow: 0 0 0 rgba(126, 220, 255, 0); }
    50% { box-shadow: 0 0 28px rgba(126, 220, 255, .18); }
  }
  @keyframes iosLiquidDrift {
    0% { background-position: 0% 0%, 100% 18%, 50% 50%; }
    50% { background-position: 8% 7%, 92% 25%, 53% 45%; }
    100% { background-position: 0% 0%, 100% 18%, 50% 50%; }
  }
  @keyframes iosSheenSweep {
    from { transform: translateX(-140%) rotate(10deg); opacity: 0; }
    28% { opacity: 1; }
    to { transform: translateX(140%) rotate(10deg); opacity: 0; }
  }
  @keyframes iosGlassBloom {
    0%, 100% { border-color: rgba(190, 226, 255, .16); box-shadow: inset 0 1px 0 rgba(255,255,255,.055), 0 14px 38px rgba(0,0,0,.18); }
    50% { border-color: rgba(126, 220, 255, .32); box-shadow: inset 0 1px 0 rgba(255,255,255,.11), 0 18px 46px rgba(72, 164, 255, .12); }
  }

  .stApp {
    color: var(--ios-text);
    background:
      radial-gradient(circle at 18% 10%, rgba(90, 167, 255, .16), transparent 28%),
      radial-gradient(circle at 86% 34%, rgba(126, 220, 255, .08), transparent 26%),
      linear-gradient(135deg, var(--ios-bg-0) 0%, var(--ios-bg-1) 48%, #020617 100%) !important;
    background-size: 140% 140%, 160% 160%, 100% 100% !important;
    animation: iosLiquidDrift 24s ease-in-out infinite;
  }
  .stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    background:
      linear-gradient(135deg, transparent 0%, rgba(255,255,255,.035) 38%, transparent 60%),
      radial-gradient(circle at 42% 12%, rgba(126,220,255,.08), transparent 28%);
    mix-blend-mode: screen;
  }
  .main .block-container {
    position: relative;
    z-index: 1;
    animation: iosRiseIn .34s cubic-bezier(.2,.8,.2,1) both;
  }

  h1, h2, h3 {
    letter-spacing: 0 !important;
    color: var(--ios-text) !important;
    text-wrap: balance;
  }
  h1 {
    margin-top: .35rem !important;
    line-height: 1.14 !important;
    margin-bottom: .55rem !important;
    animation: iosRiseIn .34s cubic-bezier(.2,.8,.2,1) both;
    text-shadow: 0 0 28px rgba(126, 220, 255, .10);
  }

  .atlas-module-title,
  .visualizer-intro,
  .directions-title-row,
  .system-title-row {
    position: relative !important;
    overflow: hidden !important;
    display: flex !important;
    align-items: center !important;
    gap: 18px !important;
    flex-wrap: wrap !important;
    margin: 1.12rem 0 .68rem 0 !important;
    padding: 18px 20px !important;
    border-radius: 28px !important;
    border: 1px solid rgba(210, 238, 255, .18) !important;
    background:
      radial-gradient(circle at 12% 0%, rgba(255,255,255,.11), transparent 35%),
      radial-gradient(circle at 82% 30%, rgba(126,220,255,.08), transparent 30%),
      linear-gradient(180deg, rgba(17,35,62,.62), rgba(5,13,27,.38)) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.12), 0 18px 52px rgba(0,0,0,.20) !important;
    backdrop-filter: blur(22px) saturate(1.32);
    animation: iosRiseIn .34s cubic-bezier(.2,.8,.2,1) both;
  }
  .atlas-module-title::before,
  .visualizer-intro::before,
  .directions-title-row::before,
  .system-title-row::before {
    content: "";
    position: absolute;
    inset: -80% -35%;
    background: var(--ios-liquid-sheen);
    transform: translateX(-28%) rotate(10deg);
    opacity: .36;
    pointer-events: none;
  }
  .atlas-module-title h1,
  .visualizer-intro h1,
  .directions-title-row h1 {
    position: relative;
    margin: 0 !important;
    font-size: clamp(2rem, 4vw, 2.65rem) !important;
    line-height: 1.1 !important;
    white-space: normal !important;
  }
  .system-title-row .system-title {
    position: relative;
    margin: 0 !important;
    font-size: clamp(2rem, 4vw, 2.65rem) !important;
    line-height: 1.1 !important;
  }
  .atlas-module-title p,
  .visualizer-intro p,
  .directions-title-row p,
  .system-title-row .system-inline-hint {
    position: relative;
    flex: 1 1 420px;
    min-width: 260px;
    margin: 0 !important;
    color: rgba(221, 240, 252, .76) !important;
    font-size: .9rem !important;
    line-height: 1.35 !important;
    max-width: 980px !important;
  }

  div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]),
  div[data-testid="stAlert"],
  div[data-testid="stExpander"],
  div[data-testid="stTextArea"] textarea {
    position: relative;
    overflow: hidden;
    border-radius: 18px !important;
    border: 1px solid var(--ios-glass-edge) !important;
    background:
      radial-gradient(circle at 12% 0%, rgba(255,255,255,.10), transparent 32%),
      linear-gradient(180deg, rgba(20, 38, 66, .78), rgba(7, 15, 29, .54)) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.12), inset 0 -1px 0 rgba(126,220,255,.07), 0 18px 48px rgba(0,0,0,.22) !important;
    backdrop-filter: blur(22px) saturate(1.35);
  }

  div[data-testid="stAlert"] {
    animation: iosRiseIn .28s cubic-bezier(.2,.8,.2,1) both;
  }

  div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
  div[data-testid="stTextInput"] input,
  div[data-testid="stTextArea"] textarea {
    border-radius: 14px !important;
    border-color: rgba(190, 226, 255, .20) !important;
    background: rgba(14, 27, 49, .82) !important;
    color: var(--ios-text) !important;
    transition: border-color .2s ease, box-shadow .2s ease, background .2s ease;
  }
  div[data-testid="stTextInput"] input:focus,
  div[data-testid="stTextArea"] textarea:focus {
    border-color: var(--ios-stroke-hot) !important;
    box-shadow: 0 0 0 3px rgba(90, 167, 255, .16) !important;
  }

  div.stButton > button {
    position: relative;
    overflow: hidden;
    border-radius: 999px !important;
    border: 1px solid rgba(190, 226, 255, .22) !important;
    background: linear-gradient(180deg, rgba(92, 171, 255, .98), rgba(22, 126, 248, .94)) !important;
    box-shadow: 0 10px 26px rgba(36, 135, 255, .24), inset 0 1px 0 rgba(255,255,255,.28) !important;
    transition: transform .16s ease, box-shadow .16s ease, filter .16s ease;
  }
  div.stButton > button::before {
    content: "";
    position: absolute;
    inset: -60% -30%;
    background: var(--ios-liquid-sheen);
    transform: translateX(-140%) rotate(10deg);
    opacity: 0;
    pointer-events: none;
  }
  div.stButton > button:hover {
    transform: translateY(-1px);
    filter: brightness(1.05);
    box-shadow: 0 16px 34px rgba(36, 135, 255, .30), inset 0 1px 0 rgba(255,255,255,.32) !important;
  }
  div.stButton > button:hover::before {
    animation: iosSheenSweep .82s cubic-bezier(.2,.8,.2,1);
  }
  div.stButton > button:active {
    transform: translateY(0) scale(.985);
  }

  div[data-testid="stSidebar"] {
    background: rgba(5, 11, 24, .74) !important;
    border-right: 1px solid rgba(190, 226, 255, .11);
    backdrop-filter: blur(20px) saturate(1.25);
  }
  div[data-testid="stSidebar"] [role="radio"] {
    border-radius: 999px;
    transition: background .18s ease, transform .18s ease;
  }
  div[data-testid="stSidebar"] [role="radio"]:hover {
    background: rgba(90, 167, 255, .08);
    transform: translateX(2px);
  }

  div[data-testid="stMetric"] {
    padding: 14px 16px;
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(13, 26, 48, .72), rgba(7, 15, 29, .54));
    border: 1px solid rgba(190, 226, 255, .16);
    box-shadow: 0 16px 42px rgba(0,0,0,.18);
    animation: iosRiseIn .32s cubic-bezier(.2,.8,.2,1) both;
  }

  div[data-testid="stPlotlyChart"],
  div[data-testid="stDataFrame"],
  div[data-testid="stCodeBlock"],
  div[data-testid="stJson"] {
    border-radius: 22px !important;
    overflow: hidden !important;
    border: 1px solid rgba(190, 226, 255, .16) !important;
    background:
      radial-gradient(circle at 18% 0%, rgba(255,255,255,.08), transparent 34%),
      linear-gradient(180deg, rgba(15, 31, 56, .62), rgba(5, 12, 25, .46)) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 20px 52px rgba(0,0,0,.22) !important;
    animation: iosRiseIn .34s cubic-bezier(.2,.8,.2,1) both;
  }
  div[data-testid="stIFrame"] iframe {
    border-radius: 28px !important;
    background:
      radial-gradient(circle at 18% 0%, rgba(255,255,255,.08), transparent 34%),
      rgba(5, 12, 25, .42) !important;
    box-shadow: 0 22px 62px rgba(0,0,0,.25);
  }
  div[data-testid="stIFrame"] {
    scroll-margin-top: 96px !important;
  }
  div[data-testid="stSlider"] {
    padding: 2px 0 8px 0;
  }
  div[data-testid="stSlider"] [data-baseweb="slider"] {
    filter: drop-shadow(0 0 14px rgba(126, 220, 255, .10));
  }
  div[data-testid="stRadio"] [role="radio"],
  div[data-testid="stCheckbox"] label,
  div[data-testid="stToggle"] label {
    transition: transform .16s ease, opacity .16s ease, color .16s ease;
  }
  div[data-testid="stRadio"] [role="radio"]:hover,
  div[data-testid="stCheckbox"] label:hover,
  div[data-testid="stToggle"] label:hover {
    transform: translateY(-1px);
  }

  mark {
    color: #05111f;
    background: linear-gradient(180deg, #bff0ff, #75d8ff);
    border-radius: 6px;
    padding: 0 .18em;
  }

  .ios-result-card {
    position: relative;
    overflow: hidden;
    margin: 10px 0;
    padding: 14px 16px;
    border-radius: 18px;
    border: 1px solid rgba(190, 226, 255, .22);
    background:
      radial-gradient(circle at 14% 0%, rgba(255,255,255,.10), transparent 34%),
      linear-gradient(180deg, rgba(17, 35, 62, .78), rgba(7, 15, 29, .54));
    box-shadow: 0 18px 48px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.10);
    animation: iosRiseIn .28s cubic-bezier(.2,.8,.2,1) both;
  }
  .ios-result-card::before {
    content: "";
    position: absolute;
    inset: -70% -30%;
    background: var(--ios-liquid-sheen);
    transform: translateX(-140%) rotate(10deg);
    opacity: .0;
    pointer-events: none;
  }
  .ios-result-card:hover {
    border-color: rgba(126, 220, 255, .38);
    animation: iosGlassBloom 1.8s ease-in-out infinite;
  }
  .ios-result-card:hover::before {
    animation: iosSheenSweep 1s cubic-bezier(.2,.8,.2,1);
  }
  .ios-kicker {
    color: var(--ios-cyan);
    font-size: 12px;
    font-weight: 800;
    letter-spacing: .08em;
    text-transform: uppercase;
  }
  .ios-muted {
    color: var(--ios-muted);
    line-height: 1.5;
  }

  /* Keep the page from visually dimming while AI requests are running. */
  [data-testid="stStatusWidget"],
  [data-testid="stDecoration"] {
    display: none !important;
    visibility: hidden !important;
  }
  [data-testid="stAppViewContainer"],
  .stApp,
  .main {
    opacity: 1 !important;
    filter: none !important;
  }

  /* Hide Streamlit's small "Press Enter to apply" input instruction. */
  [data-testid="InputInstructions"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
  }

  /* Keep sidebar navigation stable and prevent long radio labels from wrapping. */
  [data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] {
    gap: .46rem !important;
    min-height: auto !important;
    align-items: stretch !important;
  }
  [data-testid="stSidebar"] div[data-testid="stRadio"] [role="radio"] {
    padding-top: .12rem !important;
    padding-bottom: .12rem !important;
    min-height: 1.7rem !important;
  }
  [data-testid="stSidebar"] div[data-testid="stRadio"] label,
  [data-testid="stSidebar"] div[data-testid="stRadio"] p {
    white-space: nowrap !important;
    line-height: 1.25 !important;
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: .01ms !important;
      animation-iteration-count: 1 !important;
      scroll-behavior: auto !important;
      transition-duration: .01ms !important;
    }
  }

</style>
""", unsafe_allow_html=True)

if module == "Research Universe Explorer":

    research_areas = {
        "Ocean": {
            "color": "#4EA3F1",
            "angle": 160,
            "key_question": "How does Southern Ocean heat reach ice-shelf cavities?",
            "importance": "Controls basal melting and ice-shelf thinning.",
            "topics": [
                {
                    "name": "CDW Intrusion",
                    "key_question": "When and where can Circumpolar Deep Water access the continental shelf?",
                    "why": "Warm CDW is a major driver of sub-ice-shelf melt in vulnerable sectors.",
                    "status": "Active frontier",
                    "regions": "Amundsen Sea, Bellingshausen Sea, Totten Glacier"
                },
                {
                    "name": "Cross-shelf Heat Transport",
                    "key_question": "How do winds, eddies, tides, and bathymetry move heat toward the coast?",
                    "why": "Determines which ice shelves receive ocean heat.",
                    "status": "High uncertainty",
                    "regions": "Antarctic continental shelf"
                },
                {
                    "name": "Ice-shelf Basal Melt",
                    "key_question": "How fast do ice shelves melt from below?",
                    "why": "Basal melt thins ice shelves and weakens buttressing.",
                    "status": "Observed but hard to model",
                    "regions": "Pine Island, Thwaites, Totten"
                },
                {
                    "name": "Freshwater Feedback",
                    "key_question": "Can meltwater freshening trap subsurface heat?",
                    "why": "Links ice loss back to ocean stratification and future melt.",
                    "status": "Emerging feedback",
                    "regions": "Southern Ocean"
                }
            ]
        },
        "Ice Dynamics": {
            "color": "#FF8A65",
            "angle": 25,
            "key_question": "How does ice flow accelerate after ice shelves weaken?",
            "importance": "Connects local forcing to large-scale ice discharge.",
            "topics": [
                {
                    "name": "Buttressing",
                    "key_question": "How much resistance do ice shelves provide to inland ice?",
                    "why": "Loss of buttressing allows grounded ice to flow faster.",
                    "status": "Core mechanism",
                    "regions": "Antarctic Peninsula, Amundsen Sea"
                },
                {
                    "name": "Grounding Line Retreat",
                    "key_question": "What controls the retreat of the grounded-to-floating transition?",
                    "why": "Grounding line position strongly controls ice discharge.",
                    "status": "Central research target",
                    "regions": "Thwaites, Pine Island, Totten"
                },
                {
                    "name": "MISI",
                    "key_question": "Can retreat become self-sustaining on a retrograde bed?",
                    "why": "Marine Ice Sheet Instability may drive rapid, long-lasting retreat.",
                    "status": "High-impact uncertainty",
                    "regions": "WAIS, Wilkes Subglacial Basin"
                },
                {
                    "name": "MICI",
                    "key_question": "Can tall marine ice cliffs fail rapidly after ice-shelf collapse?",
                    "why": "Marine Ice Cliff Instability could raise high-end sea-level projections.",
                    "status": "Debated mechanism",
                    "regions": "Potentially marine-based Antarctic margins"
                },
                {
                    "name": "Basal Sliding",
                    "key_question": "How do basal water and sediment affect ice velocity?",
                    "why": "Basal conditions strongly control fast ice streams.",
                    "status": "Difficult to observe",
                    "regions": "Fast-flowing outlet glaciers"
                }
            ]
        },
        "Solid Earth": {
            "color": "#9CCC65",
            "angle": 270,
            "key_question": "How do bedrock, heat flow, and rebound affect ice stability?",
            "importance": "Sets boundary conditions and feedbacks for ice-sheet retreat.",
            "topics": [
                {
                    "name": "GIA",
                    "key_question": "How does bedrock rebound after ice loss?",
                    "why": "Glacial Isostatic Adjustment can alter relative sea level near grounding lines.",
                    "status": "Important feedback",
                    "regions": "West Antarctica"
                },
                {
                    "name": "Bed Topography",
                    "key_question": "Where do retrograde beds and subglacial basins create vulnerability?",
                    "why": "Bed geometry controls MISI-like retreat potential.",
                    "status": "Critical boundary data",
                    "regions": "Thwaites, Wilkes, Aurora, Sabrina"
                },
                {
                    "name": "Geothermal Heat Flux",
                    "key_question": "How much heat enters the ice base from below?",
                    "why": "Affects basal meltwater, sliding, and ice dynamics.",
                    "status": "Sparse observations",
                    "regions": "West Antarctica, South Pole region"
                },
                {
                    "name": "Subglacial Hydrology",
                    "key_question": "How does water move beneath the ice sheet?",
                    "why": "Water can lubricate the bed and modify ice flow.",
                    "status": "Hard-to-access frontier",
                    "regions": "Subglacial lakes and drainage systems"
                }
            ]
        },
        "Observations": {
            "color": "#9575CD",
            "angle": 90,
            "key_question": "How do we measure change in such a remote environment?",
            "importance": "Provides constraints for mechanisms and models.",
            "topics": [
                {
                    "name": "Satellite Altimetry",
                    "key_question": "Where is the ice surface thinning or thickening?",
                    "why": "Tracks elevation change over large areas.",
                    "status": "Mature remote sensing tool",
                    "regions": "Continent-wide"
                },
                {
                    "name": "InSAR Velocity",
                    "key_question": "How fast is the ice moving?",
                    "why": "Maps glacier acceleration and grounding-zone motion.",
                    "status": "Highly relevant to Bryan's field",
                    "regions": "Fast outlet glaciers"
                },
                {
                    "name": "GRACE / GRACE-FO",
                    "key_question": "How is total ice mass changing?",
                    "why": "Measures gravity change related to ice mass balance.",
                    "status": "Powerful but needs GIA correction",
                    "regions": "Continent-wide"
                },
                {
                    "name": "Radar & Field Data",
                    "key_question": "What lies beneath the ice?",
                    "why": "Reveals bed topography, internal layers, and basal conditions.",
                    "status": "Essential but incomplete",
                    "regions": "Ice streams, grounding zones, subglacial basins"
                }
            ]
        },
        "Paleoclimate": {
            "color": "#F6C85F",
            "angle": 215,
            "key_question": "What did the AIS do in past warm periods?",
            "importance": "Extends evidence beyond the short satellite record.",
            "topics": [
                {
                    "name": "Pliocene",
                    "key_question": "How much smaller was the AIS in a warmer-than-present world?",
                    "why": "Provides analogs for long-term future warmth.",
                    "status": "Important but uncertain",
                    "regions": "WAIS and marine-based EAIS"
                },
                {
                    "name": "Last Interglacial",
                    "key_question": "How did Antarctica contribute to high sea level?",
                    "why": "Tests model sensitivity to warm climate states.",
                    "status": "Useful constraint",
                    "regions": "Antarctic margins"
                },
                {
                    "name": "Ice Cores",
                    "key_question": "What do past temperature and accumulation records show?",
                    "why": "Records atmosphere and climate history.",
                    "status": "Foundational evidence",
                    "regions": "Interior Antarctica"
                },
                {
                    "name": "Marine Sediments",
                    "key_question": "Where and when did the ice margin retreat?",
                    "why": "Reconstructs past ice-sheet extent and ocean conditions.",
                    "status": "Key paleo archive",
                    "regions": "Continental shelf and deep ocean"
                }
            ]
        },
        "Future Projections": {
            "color": "#2F5597",
            "angle": 325,
            "key_question": "How much will Antarctica contribute to future sea-level rise?",
            "importance": "Connects science to societal risk.",
            "topics": [
                {
                    "name": "Sea-level Contribution",
                    "key_question": "How large and how fast could Antarctic sea-level rise be?",
                    "why": "Central societal impact of AIS change.",
                    "status": "Uncertain but crucial",
                    "regions": "Global coastlines"
                },
                {
                    "name": "Coupled Models",
                    "key_question": "How can ice, ocean, atmosphere, and solid Earth be simulated together?",
                    "why": "Feedbacks require coupled Earth-system modeling.",
                    "status": "Major modeling frontier",
                    "regions": "Antarctica and global climate system"
                },
                {
                    "name": "Uncertainty Quantification",
                    "key_question": "Which processes dominate projection uncertainty?",
                    "why": "Needed for useful risk assessment.",
                    "status": "High priority",
                    "regions": "Model ensembles"
                },
                {
                    "name": "AI for Earth Observation",
                    "key_question": "Can AI organize observations and detect patterns in ice-sheet change?",
                    "why": "Relevant to literature mapping, satellite analysis, and interactive learning tools.",
                    "status": "Emerging opportunity",
                    "regions": "Remote sensing and research synthesis"
                }
            ]
        }
    }

    def build_universe_topic_index(research_areas):
        topic_index = {
            "Antarctic Ice Sheet": {
                "parent": "Core system",
                "keywords": [
                    "antarctic ice sheet", "ais", "ice sheet", "antarctica",
                    "climate forcing", "earth system", "sea level"
                ]
            }
        }
        manual_keywords = {
            "Ocean": ["ocean", "southern ocean", "cdw", "circumpolar deep water", "basal melt", "heat transport", "shelf break", "warm water", "ocean forcing"],
            "CDW Intrusion": ["cdw", "circumpolar deep water", "intrusion", "warm deep water", "amundsen", "bellingshausen", "totten"],
            "Cross-shelf Heat Transport": ["cross shelf", "heat transport", "eddy", "eddies", "tide", "winds", "shelf break", "slope front"],
            "Ice-shelf Basal Melt": ["basal melt", "ice shelf melt", "melting from below", "sub ice shelf", "cavity"],
            "Freshwater Feedback": ["freshwater", "meltwater", "stratification", "aabw", "feedback"],
            "Ice Dynamics": ["ice dynamics", "ice flow", "grounding line", "buttressing", "misi", "mici", "basal sliding"],
            "Buttressing": ["buttressing", "back stress", "ice shelf support", "pinning point"],
            "Grounding Line Retreat": ["grounding line", "grounding zone", "retreat", "migration"],
            "MISI": ["misi", "marine ice sheet instability", "retrograde bed", "self sustaining retreat"],
            "MICI": ["mici", "marine ice cliff instability", "ice cliff", "hydrofracture", "cliff failure"],
            "Basal Sliding": ["basal sliding", "basal slip", "sliding", "friction", "till deformation", "water pressure"],
            "Solid Earth": ["solid earth", "bedrock", "gia", "topography", "geothermal", "subglacial hydrology"],
            "GIA": ["gia", "glacial isostatic adjustment", "isostatic", "bedrock uplift", "rebound", "viscosity"],
            "Bed Topography": ["bed topography", "bedmap", "subglacial basin", "trough", "bathymetry", "retrograde bed"],
            "Geothermal Heat Flux": ["geothermal", "heat flux", "basal temperature", "volcanism"],
            "Subglacial Hydrology": ["subglacial hydrology", "subglacial lake", "basal water", "drainage", "hydrology"],
            "Observations": ["observation", "satellite", "remote sensing", "insar", "grace", "altimetry", "radar"],
            "Satellite Altimetry": ["altimetry", "icesat", "cryosat", "elevation", "surface height"],
            "InSAR Velocity": ["insar", "sar", "velocity", "ice velocity", "interferometry"],
            "GRACE / GRACE-FO": ["grace", "grace-fo", "gravity", "mass balance", "gravimetry"],
            "Radar & Field Data": ["radar", "field data", "ice penetrating radar", "apres", "gnss", "gps"],
            "Paleoclimate": ["paleoclimate", "pliocene", "last interglacial", "ice core", "marine sediment", "past climate"],
            "Pliocene": ["pliocene", "mid pliocene", "warm period"],
            "Last Interglacial": ["last interglacial", "lig", "eemian"],
            "Ice Cores": ["ice core", "accumulation", "temperature record", "isotope"],
            "Marine Sediments": ["marine sediment", "sediment core", "paleo record", "foraminifera"],
            "Future Projections": ["future", "projection", "sea level", "uncertainty", "model", "rcp", "2100", "2300"],
            "Sea-level Contribution": ["sea level", "gmsl", "sea-level rise", "coast", "contribution"],
            "Coupled Models": ["coupled model", "ice ocean model", "earth system model", "ismip", "misomip"],
            "Uncertainty Quantification": ["uncertainty", "ensemble", "probability", "risk", "projection uncertainty"],
            "AI for Earth Observation": ["ai", "machine learning", "deep learning", "earth observation", "knowledge graph"]
        }
        for area_name, area in research_areas.items():
            topic_index[area_name] = {
                "parent": "Research area",
                "keywords": list(set([area_name.lower(), area.get("key_question", ""), area.get("importance", "")] + manual_keywords.get(area_name, [])))
            }
            for topic in area["topics"]:
                name = topic["name"]
                topic_index[name] = {
                    "parent": area_name,
                    "keywords": list(set([name.lower(), topic.get("key_question", ""), topic.get("why", ""), topic.get("status", ""), topic.get("regions", "")] + manual_keywords.get(name, [])))
                }
        return topic_index

    def classify_universe_question(question, topic_index):
        """Keyword fallback classifier. Used only when the AI classifier is unavailable or invalid."""
        q = question.lower().replace("-", "-")
        best_topic = "Antarctic Ice Sheet"
        best_score = 0
        for topic, meta in topic_index.items():
            score = 0
            topic_lower = topic.lower()
            if topic_lower in q:
                score += 12
            for kw in meta.get("keywords", []):
                kw = str(kw).lower().strip()
                if not kw:
                    continue
                if kw in q:
                    score += max(2, min(8, len(kw) // 3))
                else:
                    for part in re.findall(r"[a-zA-Z]{3,}", kw):
                        if part in q:
                            score += 1
            if score > best_score:
                best_score = score
                best_topic = topic
        return best_topic, topic_index.get(best_topic, {}).get("parent", "Research area"), best_score, "keyword_fallback"

    def classify_universe_question_with_ai(question, topic_index, backend="Local Ollama"):
        """
        AI classifier: chooses exactly one node from the Research Universe.
        DeepSeek API is used when selected; otherwise local Ollama is used.
        If the selected backend fails or returns an invalid node, fallback to keyword matching.
        """
        if backend == "Evidence only":
            return classify_universe_question(question, topic_index)
        if backend == "DeepSeek API":
            ds_result = classify_universe_question_with_deepseek(question, topic_index)
            if ds_result:
                return ds_result
            return classify_universe_question(question, topic_index)
        if backend == "OpenAI API":
            openai_result = classify_universe_question_with_openai(question, topic_index)
            if openai_result:
                return openai_result
            return classify_universe_question(question, topic_index)
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
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_ctx": 4096, "num_gpu": -1}
            }
            r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=90)
            r.raise_for_status()
            raw = r.json().get("response", "").strip()

            # Be tolerant if the model wraps JSON in text or markdown.
            match = re.search(r"\{.*\}", raw, re.S)
            obj = json.loads(match.group(0) if match else raw)
            topic = str(obj.get("topic", "")).strip()
            confidence = float(obj.get("confidence", 0.0) or 0.0)

            # Exact match first; then case-insensitive match.
            if topic not in valid_topics:
                lowered = {t.lower(): t for t in valid_topics}
                topic = lowered.get(topic.lower(), "")
            if topic in valid_topics:
                return topic, topic_index.get(topic, {}).get("parent", "Research area"), confidence, "ai"
        except Exception:
            pass

        return classify_universe_question(question, topic_index)

    universe_topic_index = build_universe_topic_index(research_areas)

    # Build the payload used by the JavaScript universe component.
    # It must be defined before research_universe_html is rendered.
    universe_payload = {
        "center": {
            "name": "Antarctic Ice Sheet",
            "type": "Core system",
            "color": "#DDEEFF",
            "key_question": "How does the Antarctic Ice Sheet respond to climate forcing?",
            "importance": "The central system linking atmosphere, ocean, ice dynamics, solid Earth, observations, paleoclimate evidence, and future sea-level risk.",
            "status": "Research hub",
            "regions": "Antarctica and global coastlines"
        },
        "areas": research_areas
    }

    initial_focus_topic = st.session_state.get("universe_focus_topic", "")
    initial_focus_source = st.session_state.get("universe_focus_source", "manual")
    initial_focus_token = st.session_state.get("universe_focus_token", 0)

    research_universe_html = """
    <div id="research-universe-root">
      <style>
        #research-universe-root {
          height: 700px; width: 100%; overflow: hidden; position: relative; border-radius: 30px; isolation:isolate;
          background:
            radial-gradient(circle at 24% 24%, rgba(78,163,241,0.20), rgba(78,163,241,0.08) 24%, transparent 48%),
            radial-gradient(circle at 74% 68%, rgba(149,117,205,0.20), rgba(149,117,205,0.07) 26%, transparent 50%),
            radial-gradient(circle at 48% 45%, rgba(221,238,255,0.08), rgba(221,238,255,0.035) 24%, transparent 48%),
            #050d1b;
          background-size: 100% 100%;
          font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          color: #eef6ff; box-shadow: inset 0 0 90px rgba(78,163,241,0.13), 0 26px 80px rgba(0,0,0,.34);
        }
        #research-universe-root::before,
        #research-universe-root::after { content:""; position:absolute; inset:-18%; pointer-events:none; z-index:1; }
        #research-universe-root::before {
          background:
            radial-gradient(circle at 30% 24%, rgba(190,240,255,.08), transparent 34%),
            radial-gradient(circle at 70% 64%, rgba(126,220,255,.05), transparent 38%);
          mix-blend-mode:screen; opacity:.36;
        }
        #research-universe-root::after {
          background: radial-gradient(ellipse at 50% 50%, transparent 35%, rgba(2,6,23,.38) 82%);
          z-index:1;
        }
        @keyframes ruCardIn {
          from { opacity:0; transform:translateY(12px) scale(.985); }
          to { opacity:1; transform:translateY(0) scale(1); }
        }
        @keyframes ruLinkFlow { to { stroke-dashoffset:-40; } }
        @keyframes ruNodeBreath {
          0%,100% { filter:drop-shadow(0 0 14px rgba(130,210,255,.60)); }
          50% { filter:drop-shadow(0 0 24px rgba(210,245,255,.85)); }
        }
        #research-universe-root .title { position:absolute; top:22px; left:26px; z-index:7; width:46%; max-width:390px; min-width:290px; padding:15px 17px; border-radius:20px; overflow:hidden; background:linear-gradient(180deg, rgba(14,27,49,.62), rgba(4,12,25,.40)); border:1px solid rgba(210,238,255,.20); backdrop-filter:blur(18px) saturate(1.3); box-shadow:inset 0 1px 0 rgba(255,255,255,.13), 0 16px 44px rgba(0,0,0,.18); animation:ruCardIn .38s cubic-bezier(.2,.8,.2,1) both; }
        #research-universe-root .title::before { content:""; position:absolute; inset:-80% -35%; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.10) 38%, rgba(126,220,255,.18) 48%, transparent 66%); transform:translateX(-30%) rotate(10deg); opacity:.70; pointer-events:none; }
        #research-universe-root .title h2 { margin:0; font-size:22px; color:#f8fbff; letter-spacing:.2px; }
        #research-universe-root .title p { margin:7px 0 0 0; color:rgba(231,245,255,.72); line-height:1.38; font-size:13px; }
        #research-universe-svg { position:absolute; inset:0; width:100%; height:100%; z-index:2; }
        #research-universe-root .star { position:absolute; width:2px; height:2px; border-radius:50%; background:rgba(255,255,255,.75); box-shadow:0 0 9px rgba(255,255,255,.55); animation:twinkle 3.5s infinite ease-in-out alternate; }
        @keyframes twinkle { from { opacity:.25; transform:scale(.8); } to { opacity:.95; transform:scale(1.25); } }
        #research-universe-root .card { position:absolute; right:22px; top:28px; width:35%; max-width:275px; min-width:235px; overflow:hidden; z-index:6; border:1px solid rgba(210,238,255,.30); border-radius:24px; padding:19px; background:radial-gradient(circle at 12% 0%, rgba(255,255,255,.10), transparent 34%), linear-gradient(180deg,rgba(12,25,46,.88),rgba(5,13,27,.68)); backdrop-filter:blur(22px) saturate(1.38); box-shadow:0 24px 70px rgba(0,0,0,.38), inset 0 1px 0 rgba(255,255,255,.14), inset 0 -1px 0 rgba(126,220,255,.08); opacity:1; transform:translateY(0); transition:opacity .24s ease, transform .24s ease, border-color .24s ease, box-shadow .24s ease; animation:ruCardIn .42s cubic-bezier(.2,.8,.2,1) both; }
        #research-universe-root .card::before { content:""; position:absolute; inset:0; background:radial-gradient(circle at 18% 0%, rgba(255,255,255,.10), transparent 44%); opacity:.45; pointer-events:none; }
        #research-universe-root .card::-webkit-scrollbar { display:none; }
        #research-universe-root .card.is-fading { opacity:0; transform:translateY(10px) scale(.985); }
        #research-universe-root .badge { display:inline-block; padding:6px 10px; border-radius:999px; background:rgba(78,163,241,.14); border:1px solid rgba(142,207,255,.25); color:#bfe6ff; font-size:12px; letter-spacing:.25px; margin-bottom:14px; }
        #research-universe-root .card h3 { margin:0 0 10px 0; font-size:20px; color:#fff; }
        #research-universe-root .card .label { margin-top:14px; color:#8ccfff; font-size:11px; text-transform:uppercase; letter-spacing:1px; }
        #research-universe-root .card p { margin:5px 0 0 0; color:rgba(239,248,255,.84); line-height:1.45; font-size:13px; }
        #research-universe-root .hint { position:absolute; left:32px; bottom:24px; max-width:calc(100% - 64px); color:rgba(231,245,255,.64); font-size:13px; z-index:5; padding:8px 11px; border-radius:999px; background:rgba(2,6,23,.30); border:1px solid rgba(210,238,255,.10); backdrop-filter:blur(10px); }
        @media (max-width: 640px) {
          #research-universe-root .title { display:none; }
          #research-universe-root .card { left:26px; right:auto; top:24px; width:300px; max-width:calc(100% - 52px); min-width:0; }
        }
        .ru-link { stroke:rgba(118,200,255,.30); stroke-linecap:round; transition:all .55s ease; }
        .ru-link.active { stroke-dasharray:9 10; animation:ruLinkFlow 1.55s linear infinite; filter:drop-shadow(0 0 9px rgba(126,220,255,.55)); }
        .ru-node { cursor:pointer; transition:opacity .55s ease; }
        .ru-node circle.main { filter:drop-shadow(0 0 14px rgba(130,210,255,.65)); transition:all .55s ease; animation:ruNodeBreath 4.2s ease-in-out infinite; }
        .ru-node.focused circle.main { filter:drop-shadow(0 0 34px rgba(255,255,255,.96)); }
        .ru-node text { pointer-events:none; fill:rgba(246,251,255,.94); font-weight:650; text-anchor:middle; paint-order:stroke; stroke:rgba(2,6,23,.90); stroke-width:4px; stroke-linejoin:round; }
        .ru-node.ai-target-pulse circle.main { animation: aiTargetPulse .78s ease-in-out 2; }
        .ru-node.ai-target-pulse text { animation: aiTextPulse .78s ease-in-out 2; }
        @keyframes aiTargetPulse {
          0% { stroke-width:2px; filter:drop-shadow(0 0 14px rgba(130,210,255,.65)); }
          50% { stroke-width:7px; filter:drop-shadow(0 0 38px rgba(255,255,255,1)); }
          100% { stroke-width:2px; filter:drop-shadow(0 0 14px rgba(130,210,255,.65)); }
        }
        @keyframes aiTextPulse {
          0% { fill:rgba(246,251,255,.94); }
          50% { fill:#ffffff; }
          100% { fill:rgba(246,251,255,.94); }
        }
      </style>
      <div class="title"><h2>Antarctic Research Universe</h2><p>Ask a question; AI locates the matching node. You can also click any sphere manually.</p></div>
      <div class="card" id="knowledge-card"></div>
      <div class="hint">Click a sphere · Ask below · matched module auto-focuses here</div>
      <svg id="research-universe-svg" viewBox="0 0 1180 760" preserveAspectRatio="xMidYMid meet"></svg>
    </div>

    <script>
    (function () {
      const data = __DATA__;
      const root = document.getElementById("research-universe-root");
      const svg = document.getElementById("research-universe-svg");
      const card = document.getElementById("knowledge-card");
      const NS = "http://www.w3.org/2000/svg";
      const cx = 430, cy = 405;
      let focusedId = null;
      const initialFocus = __INITIAL_FOCUS__;
      const initialFocusSource = __INITIAL_FOCUS_SOURCE__;
      const initialFocusToken = __INITIAL_FOCUS_TOKEN__;
      const storageKey = "antarctic_research_universe_state_v3";

      for (let i = 0; i < 95; i++) {
        const s = document.createElement("div");
        s.className = "star";
        s.style.left = Math.random() * 100 + "%";
        s.style.top = Math.random() * 100 + "%";
        s.style.animationDelay = Math.random() * 4 + "s";
        root.appendChild(s);
      }

      function el(name, attrs = {}) {
        const e = document.createElementNS(NS, name);
        Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
        return e;
      }
      function polar(angleDeg, r) {
        const a = (angleDeg - 90) * Math.PI / 180;
        return { x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r };
      }
      function safe(t) { return String(t ?? "").replace(/[&<>]/g, m => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[m])); }

      const nodes = [];
      const links = [];
      nodes.push({ id:data.center.name, parent:null, group:"Core", level:0, r:56, color:data.center.color,
        question:data.center.key_question, why:data.center.importance, status:data.center.status, regions:data.center.regions,
        home:{x:cx, y:cy} });

      Object.entries(data.areas).forEach(([areaName, area]) => {
        const p = polar(area.angle, 205);
        nodes.push({ id:areaName, parent:data.center.name, group:areaName, level:1, r:38, color:area.color,
          question:area.key_question, why:area.importance, status:"Research area", regions:area.topics.map(t => t.name).join(" - "), home:p });
        links.push({source:data.center.name, target:areaName, type:"area"});
        area.topics.forEach((topic, i) => {
          const localAngle = area.angle + (i - (area.topics.length - 1) / 2) * 19;
          const tp = polar(localAngle, 330 + (i % 2) * 28);
          nodes.push({ id:topic.name, parent:areaName, group:areaName, level:2, r:22, color:area.color,
            question:topic.key_question, why:topic.why, status:topic.status, regions:topic.regions, home:tp });
          links.push({source:areaName, target:topic.name, type:"topic"});
        });
      });

      const nodeById = new Map(nodes.map(n => [n.id, n]));
      function related(id) {
        const n = nodeById.get(id);
        const set = new Set([id]);
        links.forEach(l => { if (l.source === id) set.add(l.target); if (l.target === id) set.add(l.source); });
        if (n && n.parent) set.add(n.parent);
        if (n && n.level === 1) nodes.filter(x => x.parent === n.id).forEach(x => set.add(x.id));
        if (n && n.level === 2) nodes.filter(x => x.parent === n.parent).forEach(x => set.add(x.id));
        return set;
      }

      const defs = el("defs");
      defs.innerHTML = `<filter id="ruGlow"><feGaussianBlur stdDeviation="4.5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>`;
      svg.appendChild(defs);
      const linkLayer = el("g"), nodeLayer = el("g");
      svg.appendChild(linkLayer); svg.appendChild(nodeLayer);

      const linkEls = links.map(l => {
        const a = nodeById.get(l.source), b = nodeById.get(l.target);
        const line = el("line", { class:"ru-link", x1:a.home.x, y1:a.home.y, x2:b.home.x, y2:b.home.y, "stroke-width": l.type === "area" ? 2.2 : 1.25 });
        line.dataset.source = l.source; line.dataset.target = l.target;
        linkLayer.appendChild(line);
        return line;
      });

      function addWrappedText(g, text, fs) {
        const words = text.split(/\\s+/);
        const lines = text.length > 15 && words.length > 1 ? [words.slice(0, Math.ceil(words.length/2)).join(" "), words.slice(Math.ceil(words.length/2)).join(" ")] : [text];
        const t = el("text", { "font-size": fs });
        lines.forEach((line, i) => {
          const sp = el("tspan", { x:0, dy: i === 0 && lines.length > 1 ? "-0.15em" : (i === 0 ? "0.35em" : "1.15em") });
          sp.textContent = line;
          t.appendChild(sp);
        });
        g.appendChild(t);
      }

      const nodeEls = nodes.map(n => {
        const g = el("g", { class:"ru-node", transform:`translate(${n.home.x},${n.home.y})` });
        g.dataset.id = n.id;
        const c1 = el("circle", { class:"main", r:n.r, fill:n.color, "fill-opacity": n.level === 2 ? .70 : .88, stroke:"rgba(255,255,255,.76)", "stroke-width": n.level === 0 ? 2.6 : 1.5, filter:"url(#ruGlow)" });
        const c2 = el("circle", { r:n.r*.58, fill:"rgba(255,255,255,.22)" });
        g.appendChild(c1); g.appendChild(c2);
        addWrappedText(g, n.id, n.level === 0 ? 14 : n.level === 1 ? 12 : 10);
        g.addEventListener("click", ev => { ev.stopPropagation(); focusedId === n.id ? resetUniverse() : focusNode(n); });
        nodeLayer.appendChild(g);
        return g;
      });

      nodes.forEach(n => {
        n.x = n.home.x;
        n.y = n.home.y;
        n.startX = n.x;
        n.startY = n.y;
        n.targetX = n.x;
        n.targetY = n.y;
        n.scale = 1;
        n.targetScale = 1;
      });

      function persistUniverseState() {
        try {
          const state = {
            focusedId: focusedId,
            nodes: nodes.map(n => ({ id:n.id, x:n.x, y:n.y, scale:n.scale, targetX:n.targetX, targetY:n.targetY, targetScale:n.targetScale })),
            styles: nodeEls.map(g => {
              const main = g.querySelector("circle.main");
              return {
                id:g.dataset.id,
                opacity:g.style.opacity || "1",
                strokeWidth:main.getAttribute("stroke-width"),
                fillOpacity:main.getAttribute("fill-opacity")
              };
            }),
            links: linkEls.map(line => ({
              source:line.dataset.source,
              target:line.dataset.target,
              stroke:line.getAttribute("stroke"),
              strokeWidth:line.getAttribute("stroke-width")
            }))
          };
          window.localStorage.setItem(storageKey, JSON.stringify(state));
        } catch (e) {}
      }

      function restoreUniverseState() {
        try {
          const raw = window.localStorage.getItem(storageKey);
          if (!raw) return false;
          const state = JSON.parse(raw);
          if (!state || !Array.isArray(state.nodes)) return false;
          focusedId = state.focusedId || null;
          state.nodes.forEach(saved => {
            const n = nodeById.get(saved.id);
            if (!n) return;
            n.x = Number.isFinite(saved.x) ? saved.x : n.home.x;
            n.y = Number.isFinite(saved.y) ? saved.y : n.home.y;
            n.scale = Number.isFinite(saved.scale) ? saved.scale : 1;
            n.targetX = Number.isFinite(saved.targetX) ? saved.targetX : n.x;
            n.targetY = Number.isFinite(saved.targetY) ? saved.targetY : n.y;
            n.targetScale = Number.isFinite(saved.targetScale) ? saved.targetScale : n.scale;
          });
          if (Array.isArray(state.styles)) {
            state.styles.forEach(saved => {
              const g = nodeEls.find(el => el.dataset.id === saved.id);
              if (!g) return;
              const main = g.querySelector("circle.main");
              g.style.opacity = saved.opacity || "1";
              if (saved.strokeWidth) main.setAttribute("stroke-width", saved.strokeWidth);
              if (saved.fillOpacity) main.setAttribute("fill-opacity", saved.fillOpacity);
            });
          }
          if (Array.isArray(state.links)) {
            state.links.forEach(saved => {
              const line = linkEls.find(el => el.dataset.source === saved.source && el.dataset.target === saved.target);
              if (!line) return;
              if (saved.stroke) line.setAttribute("stroke", saved.stroke);
              if (saved.strokeWidth) line.setAttribute("stroke-width", saved.strokeWidth);
            });
          }
          if (focusedId && nodeById.has(focusedId)) {
            const rel = related(focusedId);
            nodeEls.forEach(g => g.classList.toggle("focused", g.dataset.id === focusedId));
            linkEls.forEach(line => {
              const on = rel.has(line.dataset.source) && rel.has(line.dataset.target);
              line.classList.toggle("active", on);
            });
          }
          draw();
          if (focusedId && nodeById.has(focusedId)) updateCard(nodeById.get(focusedId), false);
          else updateCard(nodeById.get(data.center.name), false);
          return true;
        } catch (e) {
          return false;
        }
      }

      function setNodeTarget(n, x, y, scale = 1) {
        n.targetX = x;
        n.targetY = y;
        n.targetScale = scale;
      }
      function draw() {
        nodeEls.forEach(g => {
          const n = nodeById.get(g.dataset.id);
          g.setAttribute("transform", `translate(${n.x},${n.y}) scale(${n.scale})`);
        });
        linkEls.forEach(line => {
          const a = nodeById.get(line.dataset.source), b = nodeById.get(line.dataset.target);
          line.setAttribute("x1", a.x); line.setAttribute("y1", a.y); line.setAttribute("x2", b.x); line.setAttribute("y2", b.y);
        });
      }
      let activeAnimation = null;
      function animateToTargets(duration = 850) {
        if (activeAnimation) cancelAnimationFrame(activeAnimation);
        nodes.forEach(n => {
          n.startX = n.x;
          n.startY = n.y;
          n.startScale = n.scale;
        });
        const startTime = performance.now();
        function step(now) {
          const t = Math.min((now - startTime) / duration, 1);
          const ease = 1 - Math.pow(1 - t, 3);
          nodes.forEach(n => {
            n.x = n.startX + (n.targetX - n.startX) * ease;
            n.y = n.startY + (n.targetY - n.startY) * ease;
            n.scale = n.startScale + (n.targetScale - n.startScale) * ease;
          });
          draw();
          if (t < 1) {
            activeAnimation = requestAnimationFrame(step);
          } else {
            persistUniverseState();
          }
        }
        activeAnimation = requestAnimationFrame(step);
      }
      function updateCard(d, animated = true) {
        const html = `<div class="badge">${d.level === 0 ? "Core system" : d.level === 1 ? "Research area" : safe(d.group)}</div>
          <h3>${safe(d.id)}</h3><div class="label">Key question</div><p>${safe(d.question)}</p>
          <div class="label">Why it matters</div><p>${safe(d.why)}</p><div class="label">Research status</div><p>${safe(d.status)}</p>
          <div class="label">Key regions / linked topics</div><p>${safe(d.regions)}</p>`;
        if (!animated) {
          card.innerHTML = html;
          return;
        }
        card.classList.add("is-fading");
        window.setTimeout(() => {
          card.innerHTML = html;
          card.classList.remove("is-fading");
        }, 180);
      }
      function focusNode(d) {
        focusedId = d.id;
        const rel = related(d.id);
        updateCard(d, true);
        const pos = new Map();
        pos.set(d.id, {x:cx, y:cy});
        const orbit = nodes.filter(n => n.parent === d.id);
        const siblings = d.parent ? nodes.filter(n => n.parent === d.parent && n.id !== d.id) : [];
        const shown = orbit.length ? orbit : (siblings.length ? siblings : nodes.filter(n => n.level === 1 && n.id !== d.id));
        shown.forEach((n, i) => {
          const a = 2 * Math.PI * i / shown.length - Math.PI / 2;
          const r = d.level === 2 ? 170 : 210;
          pos.set(n.id, {x:cx + Math.cos(a)*r, y:cy + Math.sin(a)*r});
        });
        if (d.parent) pos.set(d.parent, {x:cx - 245, y:cy - 190});
        nodes.filter(n => !pos.has(n.id)).forEach((n, i, arr) => {
          const a = 2 * Math.PI * i / Math.max(1, arr.length);
          pos.set(n.id, {x:cx + Math.cos(a)*345, y:cy + Math.sin(a)*285});
        });
        nodes.forEach(n => {
          const p = pos.get(n.id);
          setNodeTarget(n, p.x, p.y, n.id === d.id ? 1.22 : 1);
        });
        animateToTargets(850);
        nodeEls.forEach(g => {
          const n = nodeById.get(g.dataset.id), main = g.querySelector("circle.main");
          g.classList.toggle("focused", n.id === d.id);
          g.style.opacity = (rel.has(n.id) || n.group === d.group) ? 1 : .24;
          main.setAttribute("stroke-width", n.id === d.id ? 4.4 : rel.has(n.id) ? 2.8 : 1);
          main.setAttribute("fill-opacity", n.id === d.id ? 1 : rel.has(n.id) ? .92 : .30);
        });
        linkEls.forEach(line => {
          const on = rel.has(line.dataset.source) && rel.has(line.dataset.target);
          line.classList.toggle("active", on);
          line.setAttribute("stroke", on ? "rgba(163,226,255,.92)" : "rgba(118,200,255,.12)");
          line.setAttribute("stroke-width", on ? 3.2 : 1);
        });
      }
      function resetUniverse(animated = true) {
        focusedId = null;
        updateCard(nodeById.get(data.center.name), animated);
        nodes.forEach(n => setNodeTarget(n, n.home.x, n.home.y, 1));
        if (animated) animateToTargets(850);
        else { nodes.forEach(n => { n.x = n.targetX; n.y = n.targetY; n.scale = n.targetScale; }); draw(); }
        nodeEls.forEach(g => {
          const n = nodeById.get(g.dataset.id), main = g.querySelector("circle.main");
          g.classList.remove("focused");
          g.style.opacity = 1;
          main.setAttribute("stroke-width", n.level === 0 ? 2.6 : 1.5);
          main.setAttribute("fill-opacity", n.level === 2 ? .70 : .88);
        });
        linkEls.forEach(line => {
          const type = links.find(l => l.source === line.dataset.source && l.target === line.dataset.target).type;
          line.classList.remove("active");
          line.setAttribute("stroke", "rgba(118,200,255,.30)");
          line.setAttribute("stroke-width", type === "area" ? 2.2 : 1.25);
        });
      }
      function pulseThenFocus(id) {
        const n = nodeById.get(id);
        if (!n) return;
        const g = nodeEls.find(el => el.dataset.id === id);
        if (!g) {
          focusNode(n);
          return;
        }
        g.classList.add("ai-target-pulse");
        window.setTimeout(() => {
          g.classList.remove("ai-target-pulse");
          focusNode(n);
        }, 1250);
      }

      svg.addEventListener("click", () => resetUniverse(true));

      // On Streamlit reruns, restore the last in-browser graph state first.
      // This avoids jumping back to the core layout before an AI-triggered focus.
      const restored = restoreUniverseState();
      if (!restored) resetUniverse(false);

      if (initialFocus && nodeById.has(initialFocus)) {
        window.setTimeout(() => {
          // initialFocusToken is intentionally read so the iframe content changes on every AI ask,
          // even when the matched node is the same as the previous question.
          if (initialFocusSource === "ai") {
            pulseThenFocus(initialFocus);
          } else {
            focusNode(nodeById.get(initialFocus));
          }
        }, 350);
      }
    })();
    </script>
    """.replace("__DATA__", json.dumps(universe_payload, ensure_ascii=False)).replace("__INITIAL_FOCUS__", json.dumps(initial_focus_topic, ensure_ascii=False)).replace("__INITIAL_FOCUS_SOURCE__", json.dumps(initial_focus_source, ensure_ascii=False)).replace("__INITIAL_FOCUS_TOKEN__", json.dumps(initial_focus_token, ensure_ascii=False))


    # Page title sits above the workspace.
    # The explanatory caption is placed inside the left column so the Copilot can start slightly higher,
    # close to the caption line rather than down at the map top.
    st.markdown("<div class='atlas-module-title'><h1>&#127756; Research Universe Explorer</h1></div>", unsafe_allow_html=True)

    # Two-column explorer layout:
    # Left: Research Universe caption + map. Right: lightweight Copilot input and classification status only.
    # Retrieved passages and generated answer are rendered below the two-column workspace.
    universe_col, copilot_col = st.columns([0.76, 0.24], gap="large")

    ai_backend = st.session_state.get("ai_backend", "Evidence only")
    ok, model_names, err = check_ollama()

    with universe_col:
        st.caption("Explore the review paper as a knowledge universe. Ask on the right; the map stays visible, locates the matching node, and updates the concise card inside the map.")
        components.html(research_universe_html, height=720, scrolling=False)

    with copilot_col:
        # Start the Copilot at the same vertical level as the caption above the map.
        st.subheader("Research Copilot")

        backend_options = ["Evidence only", "Local Ollama", "DeepSeek API", "OpenAI API"]
        current_backend = st.session_state.get("ai_backend", "Evidence only")
        ai_backend = st.selectbox(
            "AI Backend",
            backend_options,
            index=backend_options.index(current_backend) if current_backend in backend_options else 0,
            key="ai_backend",
            help="Evidence only always works locally. AI backends add generated answers when configured."
        )

        # If the user switches backend, remove old classification/result text.
        # This prevents a previous DeepSeek status card from remaining after switching back to Ollama.
        previous_backend = st.session_state.get("ai_backend_last_rendered")
        if previous_backend is not None and previous_backend != ai_backend:
            for stale_key in [
                "universe_question",
                "universe_focus_topic",
                "universe_focus_parent",
                "universe_match_score",
                "universe_classifier_source",
                "universe_focus_source",
                "universe_focus_token",
                "universe_pending_question",
                "universe_enter_submitted",
            ]:
                st.session_state.pop(stale_key, None)
            st.session_state["universe_question_input"] = ""
            st.session_state["ai_backend_last_rendered"] = ai_backend
            st.rerun()
        st.session_state["ai_backend_last_rendered"] = ai_backend

        if ai_backend == "Evidence only":
            st.info("Evidence-only mode is active. Questions will focus the map and retrieve relevant passages without calling an AI API.")
        elif ai_backend == "Local Ollama":
            if ok:
                st.success(f"Local Ollama is connected. Current local model: {OLLAMA_MODEL}")
            else:
                st.warning(f"Local Ollama is not ready for {OLLAMA_MODEL}. You can still retrieve paper passages, but local AI answers need this model available in Ollama.")
                if err:
                    with st.expander("Connection error"):
                        st.code(err)
                if model_names:
                    st.write("Detected Ollama models:", model_names)
                    st.caption(f"Switch Ollama to {OLLAMA_MODEL}, or run `ollama pull {OLLAMA_MODEL}` if it is not installed.")
                else:
                    st.caption(f"Start Ollama and make sure the local model dropdown is set to {OLLAMA_MODEL}.")
        elif ai_backend == "DeepSeek API":
            selected_deepseek_model = st.selectbox(
                "DeepSeek Model",
                ["deepseek-chat", "deepseek-reasoner"],
                index=0 if st.session_state.get("deepseek_model_select", "deepseek-chat") == "deepseek-chat" else 1,
                key="deepseek_model_select",
                help="deepseek-chat is faster and cheaper; deepseek-reasoner is better for harder reasoning tasks."
            )

            # Keep the API key in a stable session-state field so it survives form submits and reruns.
            if "deepseek_api_key_saved" not in st.session_state:
                st.session_state["deepseek_api_key_saved"] = ""
            if "deepseek_verified" not in st.session_state:
                st.session_state["deepseek_verified"] = False
            if "deepseek_status_message" not in st.session_state:
                st.session_state["deepseek_status_message"] = ""

            configured_key = get_deepseek_api_key()
            if configured_key and st.session_state.get("deepseek_verified", False):
                st.success(f"DeepSeek API is connected, current model: {selected_deepseek_model}")
            elif configured_key:
                st.info("DeepSeek API key is saved. Click Test DeepSeek Connection once to verify it.")
            else:
                st.warning("DeepSeek API key is not configured.")

            with st.expander("DeepSeek API settings", expanded=not bool(configured_key)):
                st.caption("For local testing, enter the key here; it will stay saved during this Streamlit session.")
                key_input = st.text_input(
                    "DeepSeek API Key",
                    type="password",
                    value=st.session_state.get("deepseek_api_key_saved", ""),
                    placeholder="sk-...",
                    key="deepseek_api_key_input"
                )
                if st.button("Save & Test DeepSeek", type="secondary", use_container_width=True):
                    st.session_state["deepseek_api_key_saved"] = key_input.strip()
                    ok_ds, msg_ds = test_deepseek_connection(st.session_state["deepseek_api_key_saved"], selected_deepseek_model)
                    st.session_state["deepseek_verified"] = ok_ds
                    st.session_state["deepseek_status_message"] = msg_ds
                    st.rerun()
                if st.session_state.get("deepseek_status_message"):
                    if st.session_state.get("deepseek_verified", False):
                        st.success(st.session_state["deepseek_status_message"])
                    else:
                        st.error(st.session_state["deepseek_status_message"])

        elif ai_backend == "OpenAI API":
            openai_models = OPENAI_MODEL_OPTIONS
            current_openai_model = st.session_state.get("openai_model_select", OPENAI_MODEL)
            selected_openai_model = st.selectbox(
                "OpenAI Model",
                openai_models,
                index=openai_models.index(current_openai_model) if current_openai_model in openai_models else 0,
                key="openai_model_select",
                help="Choose the official OpenAI model used for classification and paper-grounded answers."
            )

            if "openai_api_key_saved" not in st.session_state:
                st.session_state["openai_api_key_saved"] = ""
            if "openai_verified" not in st.session_state:
                st.session_state["openai_verified"] = False
            if "openai_status_message" not in st.session_state:
                st.session_state["openai_status_message"] = ""

            configured_openai_key = get_openai_api_key()
            if configured_openai_key and st.session_state.get("openai_verified", False):
                st.success(f"OpenAI API is connected, current model: {selected_openai_model}")
            elif configured_openai_key:
                st.info("OpenAI API key is saved. Click Test OpenAI Connection once to verify it.")
            else:
                st.warning("OpenAI API key is not configured.")

            with st.expander("OpenAI API settings", expanded=not bool(configured_openai_key)):
                st.caption("For local testing, enter the key here; it will stay saved during this Streamlit session.")
                openai_key_input = st.text_input(
                    "OpenAI API Key",
                    type="password",
                    value=st.session_state.get("openai_api_key_saved", ""),
                    placeholder="sk-...",
                    key="openai_api_key_input"
                )
                if st.button("Save & Test OpenAI", type="secondary", use_container_width=True):
                    st.session_state["openai_api_key_saved"] = openai_key_input.strip()
                    ok_openai, msg_openai = test_openai_connection(st.session_state["openai_api_key_saved"], selected_openai_model)
                    st.session_state["openai_verified"] = ok_openai
                    st.session_state["openai_status_message"] = msg_openai
                    st.rerun()
                if st.session_state.get("openai_status_message"):
                    if st.session_state.get("openai_verified", False):
                        st.success(st.session_state["openai_status_message"])
                    else:
                        st.error(st.session_state["openai_status_message"])

        def submit_universe_question():
            q = st.session_state.get("universe_question_input", "").strip()
            if q:
                st.session_state["universe_pending_question"] = q

        if "universe_question_input" not in st.session_state:
            st.session_state["universe_question_input"] = st.session_state.get("universe_question", "")

        st.markdown("Ask a question about the Antarctic Ice Sheet review paper:")
        st.text_input(
            "Ask a question about the Antarctic Ice Sheet review paper",
            key="universe_question_input",
            placeholder="Example: Why is grounding line retreat important for future sea-level rise?",
            label_visibility="collapsed",
            on_change=submit_universe_question
        )
        ask_button_label = "Search evidence" if ai_backend == "Evidence only" else "Ask AI and focus map"
        if st.button(ask_button_label, type="primary", use_container_width=True):
            submit_universe_question()

        pending_question = st.session_state.pop("universe_pending_question", "").strip()
        feedback_box = st.empty()

        if pending_question:
            if st.session_state.get("ai_backend", "Evidence only") == "Evidence only":
                feedback_box.info("Searching the paper and focusing the matching knowledge module...")
            else:
                feedback_box.info("AI is locating the matching knowledge module and retrieving paper passages...")
            matched_topic, matched_parent, score, classifier_source = classify_universe_question_with_ai(pending_question, universe_topic_index, backend=st.session_state.get("ai_backend", "Evidence only"))
            st.session_state["universe_question"] = pending_question
            st.session_state["universe_focus_topic"] = matched_topic
            st.session_state["universe_focus_parent"] = matched_parent
            st.session_state["universe_match_score"] = score
            st.session_state["universe_classifier_source"] = classifier_source
            st.session_state["universe_focus_source"] = "ai"
            st.session_state["universe_focus_token"] = st.session_state.get("universe_focus_token", 0) + 1
            st.rerun()

        active_question = st.session_state.get("universe_question", "").strip()
        if active_question:
            matched_topic = st.session_state.get("universe_focus_topic", "Antarctic Ice Sheet")
            matched_parent = st.session_state.get("universe_focus_parent", "Core system")
            display_module = matched_topic if matched_parent in ["Core system", "Research area"] else f"{matched_parent} / {matched_topic}"
            classifier_source = st.session_state.get("universe_classifier_source", "keyword_fallback")
            if classifier_source in ["ai", "deepseek", "openai"]:
                backend_name = "DeepSeek" if classifier_source == "deepseek" else ("OpenAI" if classifier_source == "openai" else "AI")
                st.info(f"{backend_name} matched this question to **{display_module}**. The map is focused above; evidence and generated content appear below.")
            else:
                st.info(f"This question matches **{display_module}**. Evidence-only mode used keyword matching; paper passages appear below.")

    # Full-width evidence and answer area below the map + Copilot workspace.
    active_question = st.session_state.get("universe_question", "").strip()
    if active_question:
        matched_topic = st.session_state.get("universe_focus_topic", "Antarctic Ice Sheet")
        matched_parent = st.session_state.get("universe_focus_parent", "Core system")
        display_module = matched_topic if matched_parent in ["Core system", "Research area"] else f"{matched_parent} / {matched_topic}"
        classifier_source = st.session_state.get("universe_classifier_source", "keyword_fallback")

        topic_keywords = [matched_topic]
        if matched_parent not in ["Core system", "Research area"]:
            topic_keywords.append(matched_parent)
        keywords = list(dict.fromkeys(extract_keywords(active_question) + extract_keywords(" ".join(topic_keywords))))
        results = search_pages(pages, keywords, 5)

        st.divider()
        st.subheader("Evidence and AI Answer")
        if classifier_source in ["ai", "deepseek", "openai"]:
            backend_name = "DeepSeek" if classifier_source == "deepseek" else ("OpenAI" if classifier_source == "openai" else "AI")
            st.info(f"{backend_name} matched this question to **{display_module}**. The map is focused above.")
        else:
            st.info(f"This question matches **{display_module}**. Evidence-only mode used keyword matching.")

        if not results:
            st.warning("No relevant passages found.")
        else:
            with st.expander("Retrieved passages from the paper", expanded=False):
                for r in results:
                    st.markdown(f"**Page {r['page']} | Score: {r['score']}**")
                    st.write(r["text"][:1600] + "...")

            current_backend = st.session_state.get("ai_backend", "Evidence only")
            backend_ready = (current_backend == "DeepSeek API" and bool(get_deepseek_api_key())) or (current_backend == "OpenAI API" and bool(get_openai_api_key())) or (current_backend == "Local Ollama" and ok)
            if backend_ready:
                st.subheader("AI Answer")
                progress_bar = st.progress(0.0)
                text_box = st.empty()
                if classifier_source in ["ai", "deepseek", "openai"]:
                    backend_name = "DeepSeek" if classifier_source == "deepseek" else ("OpenAI" if classifier_source == "openai" else "AI")
                    answer_prefix = f"{backend_name} matched this question to **{display_module}**. "
                else:
                    answer_prefix = f"This question matches **{display_module}**. "
                try:
                    stream_ai_answer(st.session_state.get("ai_backend", "Local Ollama"), active_question, results, text_box, progress_bar, answer_prefix=answer_prefix)
                    st.success("Generation completed")
                except Exception as e:
                    st.error(f"{st.session_state.get('ai_backend', 'Local Ollama')} call failed")
                    st.code(str(e))
            else:
                st.info("AI answer generation is off or unavailable, so only retrieved paper passages are shown.")

elif module == "Research Directions":
    st.markdown("""
    <style>
      .block-container { padding-top: 1.05rem !important; }

      /* Compact Research Compass header: keeps the first screen focused on the actual tool. */
      .directions-title-row {
        margin: 1.72rem 0 .55rem 0;
        padding: 10px 14px 11px 14px;
        border-radius: 20px;
        border: 1px solid rgba(170,215,255,.18);
        background:
          radial-gradient(circle at 18% 18%, rgba(78,163,241,.18), transparent 30%),
          radial-gradient(circle at 76% 58%, rgba(149,117,205,.14), transparent 32%),
          linear-gradient(135deg, rgba(3,7,18,.68), rgba(7,17,31,.44));
        box-shadow: inset 0 0 28px rgba(78,163,241,.045);
        display: flex;
        align-items: baseline;
        gap: 18px;
        flex-wrap: wrap;
      }
      .directions-title-row h1 {
        margin: 0;
        font-size: 2.18rem;
        line-height: 1.12;
        letter-spacing: 0;
        color: #f8fbff;
        white-space: nowrap;
      }
      .directions-title-row p {
        margin: 0;
        color: rgba(221,240,252,.74);
        font-size: .88rem;
        line-height: 1.28;
        max-width: 1120px;
      }
      .direction-card {
        padding: 14px 15px;
        border-radius: 18px;
        border: 1px solid rgba(170,215,255,.18);
        background: linear-gradient(180deg, rgba(8,18,34,.74), rgba(7,15,29,.48));
        box-shadow: inset 0 0 24px rgba(78,163,241,.05);
        min-height: 132px;
      }
      .direction-card .k {
        font-size: 11px;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #8ccfff;
        font-weight: 850;
        margin-bottom: 7px;
      }
      .direction-card h3 {
        margin: 0 0 8px 0;
        color: #f8fbff;
        font-size: 1.05rem;
        line-height: 1.25;
      }
      .direction-card p {
        margin: 0;
        color: rgba(235,248,255,.78);
        line-height: 1.43;
        font-size: .86rem;
      }
      .direction-chip-row { display:flex; flex-wrap:wrap; gap:7px; margin-top:10px; }
      .direction-chip {
        padding: 5px 9px;
        border-radius: 999px;
        border: 1px solid rgba(142,207,255,.22);
        background: rgba(78,163,241,.10);
        color: #c8edff;
        font-size: 12px;
        font-weight: 700;
      }
      .direction-metric-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin-bottom: 16px;
      }
      .direction-metric {
        position: relative;
        overflow: hidden;
        min-height: 96px;
        padding: 13px 14px;
        border-radius: 18px;
        border: 1px solid rgba(190,226,255,.18);
        background:
          radial-gradient(circle at 18% 0%, rgba(255,255,255,.10), transparent 34%),
          linear-gradient(180deg, rgba(17,35,62,.72), rgba(7,15,29,.50));
        box-shadow: inset 0 1px 0 rgba(255,255,255,.10), 0 16px 42px rgba(0,0,0,.18);
        backdrop-filter: blur(18px) saturate(1.28);
      }
      .direction-metric::before {
        content: "";
        position: absolute;
        inset: -80% -35%;
        background: linear-gradient(120deg, transparent 0%, rgba(255,255,255,.10) 38%, rgba(126,220,255,.16) 48%, transparent 66%);
        transform: translateX(-34%) rotate(10deg);
        opacity: .36;
        pointer-events: none;
      }
      .direction-metric .k {
        position: relative;
        color: rgba(235,248,255,.82);
        font-size: 12px;
        font-weight: 760;
      }
      .direction-metric .v {
        position: relative;
        margin-top: 8px;
        color: #fff;
        font-size: 1.75rem;
        line-height: 1;
        font-weight: 850;
      }
      .direction-metric .sub {
        position: relative;
        margin-top: 5px;
        color: rgba(220,236,248,.62);
        font-size: 12px;
        font-weight: 700;
      }
      .direction-metric .v.time {
        font-size: 1.05rem;
        line-height: 1.25;
        white-space: normal;
      }
      .direction-mini-note {
        padding: 11px 13px;
        border-radius: 16px;
        border: 1px solid rgba(74,222,128,.22);
        background: rgba(34,197,94,.09);
        color: rgba(234,255,241,.88);
        font-size: .86rem;
        line-height: 1.43;
      }
      .direction-output-box {
        padding: 14px 15px;
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,.12);
        background: rgba(255,255,255,.045);
        color: rgba(239,248,255,.88);
        line-height: 1.48;
        font-size: .90rem;
      }
      div[data-testid="stMetric"] {
        background: rgba(255,255,255,.035);
        border: 1px solid rgba(170,215,255,.11);
        padding: 10px 12px;
        border-radius: 16px;
      }
      /* Make controls tighter so compass content appears in the first screen. */
      div[data-testid="stSelectbox"], div[data-testid="stRadio"], div[data-testid="stSlider"] {
        margin-top: 0 !important;
        margin-bottom: .15rem !important;
      }
    </style>
    <div class="directions-title-row">
      <h1>&#129517; Research Compass</h1>
      <p>Explore frontier questions from the review paper: choose a theme, inspect uncertainty, connect regions and methods, then generate a starter research idea.</p>
    </div>
    """, unsafe_allow_html=True)

    research_directions = {
        "Ocean heat pathways": {
            "emoji": "*",
            "system": "Ocean-ice shelf interaction",
            "uncertainty": 92,
            "impact": 94,
            "observability": 58,
            "time_scale": "days ->decades",
            "regions": ["Amundsen Sea", "Bellingshausen Sea", "Totten Glacier", "Filchner-Ronne"],
            "methods": ["Ocean moorings", "AUV", "CTD", "High-resolution ocean models"],
            "core_question": "How does warm Circumpolar Deep Water cross the continental shelf and reach ice-shelf cavities?",
            "why_now": "The paper repeatedly points to warm ocean access as a central control on basal melting, but the exact pathways depend on winds, eddies, tides, bathymetry, and freshwater feedbacks.",
            "gap": "Cross-shelf heat transport is still hard to observe directly and difficult to represent in models at the right spatial scale.",
            "student_angle": "Build a conceptual or data-driven map linking bathymetric troughs, wind forcing, and glacier thinning hotspots.",
            "starter_questions": [
                "Which Antarctic margins are most exposed to warm-water access under changing winds?",
                "Can satellite-observed thinning be connected to likely ocean heat pathways?",
                "How does meltwater-driven stratification change the persistence of warm water beneath ice shelves?"
            ]
        },
        "Grounding-line instability": {
            "emoji": "*",
            "system": "Ice dynamics",
            "uncertainty": 88,
            "impact": 96,
            "observability": 64,
            "time_scale": "years ->centuries",
            "regions": ["Thwaites", "Pine Island", "Wilkes Basin", "Aurora Basin"],
            "methods": ["InSAR", "Satellite altimetry", "Radar sounding", "Ice-sheet models"],
            "core_question": "When does grounding-line retreat become self-sustaining on retrograde bed topography?",
            "why_now": "MISI links bed geometry, ice-shelf buttressing, and ocean forcing; it is one of the highest-impact mechanisms for future sea-level projections.",
            "gap": "The timing and reversibility of retreat depend on subglacial topography, basal friction, ocean melt parameterization, and solid-Earth feedbacks.",
            "student_angle": "Use a case-study comparison between Thwaites, Pine Island, and an East Antarctic basin to explain how bed geometry changes risk.",
            "starter_questions": [
                "Which bed geometries make retreat most sensitive to small melt-rate changes?",
                "How do pinning points delay or reorganize grounding-line retreat?",
                "Can InSAR-derived velocity changes be used as early signs of buttressing loss?"
            ]
        },
        "Ice-shelf fracture and calving": {
            "emoji": "*",
            "system": "Atmosphere-ice shelf coupling",
            "uncertainty": 85,
            "impact": 90,
            "observability": 70,
            "time_scale": "days ->years",
            "regions": ["Antarctic Peninsula", "Larsen B", "Wilkins", "Roi Baudouin"],
            "methods": ["Optical imagery", "SAR", "Surface melt mapping", "Fracture models"],
            "core_question": "How do surface melt, hydrofracturing, and calving change ice-shelf buttressing?",
            "why_now": "Surface hydrology and hydrofracture are crucial for understanding rapid shelf collapse and high-end sea-level risk, but MICI remains debated.",
            "gap": "Models still struggle to predict when fractures connect, when shelves collapse, and how quickly inland glaciers respond.",
            "student_angle": "Create a visual diagnostic framework that classifies ice shelves by meltwater ponding, crevasse density, and buttressing importance.",
            "starter_questions": [
                "Which surface-hydrology patterns indicate increasing hydrofracture vulnerability?",
                "How much passive shelf area can be lost before grounded ice accelerates?",
                "Can Larsen B-like collapse logic be generalized to other Antarctic shelves?"
            ]
        },
        "Subglacial water and basal sliding": {
            "emoji": "*",
            "system": "Subglacial hydrology",
            "uncertainty": 91,
            "impact": 82,
            "observability": 42,
            "time_scale": "hours ->millennia",
            "regions": ["Siple Coast", "Thwaites", "Byrd Glacier", "Subglacial lakes"],
            "methods": ["Radar", "Altimetry lake detection", "Boreholes", "Hydrology models"],
            "core_question": "How does water beneath the ice sheet control basal friction and ice velocity?",
            "why_now": "Basal water can lubricate the bed, drain through lakes and channels, and feed freshwater into ice-shelf cavities.",
            "gap": "The subglacial system is difficult to observe directly, so models often rely on simplified sliding laws and uncertain hydrological parameters.",
            "student_angle": "Compare distributed versus channelized drainage and explain how each could stabilize or destabilize ice flow.",
            "starter_questions": [
                "How do active subglacial lake drainage events change downstream velocity?",
                "What remote-sensing signatures indicate a switch from distributed to channelized flow?",
                "How should basal hydrology be represented in beginner-friendly ice-flow simulations?"
            ]
        },
        "Solid-Earth feedbacks": {
            "emoji": "*",
            "system": "Solid Earth-ice interaction",
            "uncertainty": 87,
            "impact": 84,
            "observability": 50,
            "time_scale": "decades ->millennia",
            "regions": ["West Antarctica", "Amundsen Sea", "Antarctic Peninsula", "East Antarctica"],
            "methods": ["GPS/GNSS", "GRACE correction", "Seismology", "GIA models"],
            "core_question": "Can bedrock uplift and sea-level fingerprints slow or reshape ice-sheet retreat?",
            "why_now": "GIA affects both observed mass-balance estimates and physical retreat feedbacks near grounding lines.",
            "gap": "Antarctic mantle viscosity varies in 3D, but many models still simplify Earth structure or lack enough geodetic constraints.",
            "student_angle": "Explain why the solid Earth is not just a correction term but an active feedback in ice-sheet stability.",
            "starter_questions": [
                "Where is rapid bedrock uplift most likely to slow grounding-line retreat?",
                "How sensitive are GRACE-derived mass trends to different GIA assumptions?",
                "Can regional GPS/GNSS constraints improve ice-sheet projection confidence?"
            ]
        },
        "Paleo constraints for future projections": {
            "emoji": "*",
            "system": "Past-future bridge",
            "uncertainty": 80,
            "impact": 88,
            "observability": 56,
            "time_scale": "centuries ->millions of years",
            "regions": ["Pliocene", "Last Interglacial", "Marine margins", "Ice-core sites"],
            "methods": ["Marine sediment cores", "Ice cores", "Sea-level records", "Model-data comparison"],
            "core_question": "How can past warm periods constrain future Antarctic sea-level contribution?",
            "why_now": "The satellite era is too short to reveal the full AIS response, so paleo records are essential for testing long-term sensitivity.",
            "gap": "Paleo sea-level and ice-extent reconstructions have large uncertainties, making it hard to validate specific model physics.",
            "student_angle": "Build a Past-Present-Future evidence chain showing what each archive can and cannot prove.",
            "starter_questions": [
                "Which past warm intervals are most useful analogs for future Antarctic change?",
                "How can paleo records test whether high-end collapse mechanisms are realistic?",
                "What uncertainty remains when using sea-level records to constrain AIS retreat?"
            ]
        },
        "AI-assisted Antarctic research": {
            "emoji": "*",
            "system": "AI + Earth observation",
            "uncertainty": 74,
            "impact": 78,
            "observability": 86,
            "time_scale": "now ->next decade",
            "regions": ["Remote sensing", "Literature synthesis", "Education", "Model workflows"],
            "methods": ["Knowledge graphs", "RAG", "Computer vision", "Interactive visualization"],
            "core_question": "How can AI help organize observations, literature, and model uncertainty without replacing scientific reasoning?",
            "why_now": "Your Atlas itself is a prototype: it turns a dense review paper into explorable knowledge maps, simulations, and paper-grounded Q&A.",
            "gap": "AI tools must remain source-grounded, uncertainty-aware, and connected to real observation and modeling workflows.",
            "student_angle": "Turn this project into a portfolio piece: an AI research assistant for Antarctic ice-sheet literature and remote-sensing reasoning.",
            "starter_questions": [
                "Can a knowledge graph help students navigate AIS mechanisms more effectively than a linear PDF?",
                "How can RAG systems cite paper passages while generating slide-ready scientific explanations?",
                "Can AI detect conceptual links between satellite observations and physical ice-sheet processes?"
            ]
        }
    }

    direction_names = list(research_directions.keys())
    if "directions_selected" not in st.session_state or st.session_state["directions_selected"] not in direction_names:
        st.session_state["directions_selected"] = direction_names[0]

    top_col, option_col = st.columns([0.72, 0.28], gap="large")
    with option_col:
        selected_direction = st.selectbox(
            "Choose a frontier direction",
            direction_names,
            key="directions_selected"
        )
        view_mode = st.radio(
            "View mode",
            ["Compass", "Timeline", "Region map", "Proposal builder"],
            horizontal=False,
            key="directions_view_mode"
        )
        emphasis = st.slider("Ambition level", 1, 5, 3, help="Higher ambition makes the generated research idea broader and more frontier-oriented.")

    selected_info = research_directions[selected_direction]

    with top_col:
        safe_time_scale = html.escape(selected_info["time_scale"]).replace("-&gt;", "&rarr; ")
        st.markdown(f"""
        <div class="direction-metric-grid">
          <div class="direction-metric"><div class="k">Impact</div><div class="v">{selected_info['impact']}</div><div class="sub">/ 100</div></div>
          <div class="direction-metric"><div class="k">Uncertainty</div><div class="v">{selected_info['uncertainty']}</div><div class="sub">/ 100</div></div>
          <div class="direction-metric"><div class="k">Observability</div><div class="v">{selected_info['observability']}</div><div class="sub">/ 100</div></div>
          <div class="direction-metric"><div class="k">Time scale</div><div class="v time">{safe_time_scale}</div></div>
        </div>
        """, unsafe_allow_html=True)

        card_a, card_b, card_c = st.columns([0.34, 0.33, 0.33], gap="small")
        with card_a:
            st.markdown(f"""
            <div class="direction-card">
              <div class="k">Selected frontier</div>
              <h3>{selected_info['emoji']} {selected_direction}</h3>
              <p><b>Core question:</b><br>{selected_info['core_question']}</p>
            </div>
            """, unsafe_allow_html=True)
        with card_b:
            st.markdown(f"""
            <div class="direction-card">
              <div class="k">Why it matters now</div>
              <h3>{selected_info['system']}</h3>
              <p>{selected_info['why_now']}</p>
            </div>
            """, unsafe_allow_html=True)
        with card_c:
            chip_html = "".join([f"<span class='direction-chip'>{m}</span>" for m in selected_info["methods"]])
            st.markdown(f"""
            <div class="direction-card">
              <div class="k">Useful methods</div>
              <h3>Observation + modeling toolkit</h3>
              <div class="direction-chip-row">{chip_html}</div>
            </div>
            """, unsafe_allow_html=True)

    # Plotly compass bubble map
    compass_df = pd.DataFrame([
        {
            "Direction": name,
            "Impact": meta["impact"],
            "Uncertainty": meta["uncertainty"],
            "Observability": meta["observability"],
            "System": meta["system"],
            "emoji": "*",
            "Selected": name == selected_direction,
            "Size": 20 + meta["impact"] * 0.55,
            "Label": f"{meta['emoji']} {name}"
        }
        for name, meta in research_directions.items()
    ])

    if view_mode == "Compass":
        fig = go.Figure()
        fig.add_shape(type="rect", x0=50, x1=100, y0=50, y1=100, fillcolor="rgba(255,180,90,0.08)", line=dict(width=0), layer="below")
        fig.add_shape(type="rect", x0=0, x1=50, y0=50, y1=100, fillcolor="rgba(100,180,255,0.06)", line=dict(width=0), layer="below")
        fig.add_shape(type="rect", x0=50, x1=100, y0=0, y1=50, fillcolor="rgba(120,255,180,0.055)", line=dict(width=0), layer="below")
        fig.add_trace(go.Scatter(
            x=compass_df["Uncertainty"],
            y=compass_df["Impact"],
            mode="markers+text",
            text=compass_df["Label"],
            textposition="top center",
            marker=dict(
                size=compass_df["Size"],
                color=compass_df["Observability"],
                colorscale="Blues",
                showscale=True,
                colorbar=dict(title="Observability"),
                line=dict(width=np.where(compass_df["Selected"], 4, 1), color=np.where(compass_df["Selected"], "white", "rgba(255,255,255,.45)")),
                opacity=np.where(compass_df["Selected"], 1.0, 0.72)
            ),
            customdata=np.stack([compass_df["System"], compass_df["Observability"]], axis=-1),
            hovertemplate="<b>%{text}</b><br>System: %{customdata[0]}<br>Uncertainty: %{x}/100<br>Impact: %{y}/100<br>Observability: %{customdata[1]}/100<extra></extra>"
        ))
        fig.add_annotation(x=78, y=96, text="High impact + high uncertainty = frontier zone", showarrow=False, font=dict(size=14))
        fig.update_layout(
            height=520,
            margin=dict(l=10, r=10, t=25, b=10),
            xaxis=dict(title="Scientific uncertainty", range=[35, 100], gridcolor="rgba(150,180,200,.16)"),
            yaxis=dict(title="Sea-level / Earth-system impact", range=[65, 100], gridcolor="rgba(150,180,200,.16)"),
            plot_bgcolor="rgba(3,7,18,0.15)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(240,248,255,.88)")
        )
        st.plotly_chart(fig, use_container_width=True, key="directions_compass_plot")
        st.markdown(f"""
        <div class="direction-mini-note">
          <b>How to read it:</b> directions in the upper-right are scientifically important but still uncertain. The selected item is highlighted; color indicates how directly observable the process is with current tools.
        </div>
        """, unsafe_allow_html=True)

    elif view_mode == "Timeline":
        timeline = pd.DataFrame([
            {"Stage": "Past evidence", "Position": 0, "Description": "Use paleo records to test whether the mechanism happened before.", "Direction": selected_direction},
            {"Stage": "Present observation", "Position": 1, "Description": "Use satellites, field data, and ocean/solid-Earth observations to identify active signals.", "Direction": selected_direction},
            {"Stage": "Process model", "Position": 2, "Description": "Represent the mechanism in physical or statistical models.", "Direction": selected_direction},
            {"Stage": "Coupled projection", "Position": 3, "Description": "Connect the mechanism to sea-level projections and uncertainty.", "Direction": selected_direction},
            {"Stage": "Research product", "Position": 4, "Description": "Turn the result into a map, figure, interactive tool, or proposal.", "Direction": selected_direction},
        ])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timeline["Position"], y=[1]*len(timeline), mode="lines+markers+text",
            text=timeline["Stage"], textposition="top center",
            marker=dict(size=[28, 32, 32, 32, 30], line=dict(width=2, color="white")),
            line=dict(width=5),
            hovertext=timeline["Description"], hovertemplate="<b>%{text}</b><br>%{hovertext}<extra></extra>"
        ))
        fig.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=45, b=20),
            xaxis=dict(visible=False, range=[-.35, 4.35]),
            yaxis=dict(visible=False, range=[0.6, 1.35]),
            plot_bgcolor="rgba(3,7,18,0.15)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(240,248,255,.88)")
        )
        st.plotly_chart(fig, use_container_width=True, key="directions_timeline_plot")
        st.markdown(f"""
        <div class="direction-output-box">
          <b>{selected_info['emoji']} {selected_direction} as a research pathway</b><br><br>
          1. Start from the paper's review of known mechanisms.<br>
          2. Identify the current observation gap: {selected_info['gap']}<br>
          3. Use methods such as {', '.join(selected_info['methods'][:3])}.<br>
          4. Convert the result into a figure, map, model comparison, or AI-assisted explainer.
        </div>
        """, unsafe_allow_html=True)

    elif view_mode == "Region map":
        region_coords = {
            "Amundsen Sea": (-74.5, -110), "Bellingshausen Sea": (-72, -85), "Totten Glacier": (-67, 116),
            "Filchner-Ronne": (-78, -55), "Thwaites": (-75.5, -106), "Pine Island": (-75, -100),
            "Wilkes Basin": (-70, 140), "Aurora Basin": (-72, 120), "Antarctic Peninsula": (-65, -62),
            "Larsen B": (-65.5, -61), "Wilkins": (-70, -73), "Roi Baudouin": (-70, 24),
            "Siple Coast": (-82, -150), "Byrd Glacier": (-80, 160), "Subglacial lakes": (-77, 105),
            "West Antarctica": (-78, -115), "East Antarctica": (-78, 80), "Marine margins": (-70, 30),
            "Ice-core sites": (-76, 20), "Remote sensing": (-75, 0), "Literature synthesis": (-74, 40),
            "Education": (-73, 80), "Model workflows": (-73, 120), "GRACE correction": (-76, -30)
        }
        rows = []
        for r in selected_info["regions"]:
            lat, lon = region_coords.get(r, (-75, 0))
            rows.append({"Region": r, "lat": lat, "lon": lon, "Direction": selected_direction})
        region_df = pd.DataFrame(rows)
        fig = go.Figure(go.Scattergeo(
            lat=region_df["lat"], lon=region_df["lon"], text=region_df["Region"],
            mode="markers+text", textposition="top center",
            marker=dict(size=18, color="deepskyblue", line=dict(width=2, color="white")),
            hovertemplate="<b>%{text}</b><br>Linked to: " + selected_direction + "<extra></extra>"
        ))
        fig.update_geos(
            projection_type="azimuthal equal area",
            projection_rotation=dict(lat=-90),
            lataxis_range=[-90, -55],
            showland=True, landcolor="rgb(235,245,250)",
            showocean=True, oceancolor="rgb(8,35,60)",
            showcountries=False, showcoastlines=True, coastlinecolor="rgba(80,120,140,.7)",
            bgcolor="rgba(0,0,0,0)"
        )
        fig.update_layout(
            height=520,
            margin=dict(l=0, r=0, t=18, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(240,248,255,.88)")
        )
        st.plotly_chart(fig, use_container_width=True, key="directions_region_map")
        st.caption("This is a conceptual region locator for research planning, not a precise GIS layer.")

    elif view_mode == "Proposal builder":
        q_options = selected_info["starter_questions"]
        chosen_q = st.selectbox("Choose a starter question", q_options, key="directions_starter_question")
        method_focus = st.multiselect("Methods to include", selected_info["methods"], default=selected_info["methods"][:2], key="directions_methods")
        region_focus = st.multiselect("Regions / evidence contexts", selected_info["regions"], default=selected_info["regions"][:2], key="directions_regions")
        ambition_text = {
            1: "a small class-project style literature synthesis",
            2: "a focused exploratory analysis",
            3: "a feasible undergraduate research proposal",
            4: "an ambitious portfolio project with visualization or modeling",
            5: "a high-end PhD-style frontier proposal"
        }[emphasis]
        proposal = f"""Title: {selected_info['emoji']} {selected_direction}: {chosen_q}

Research style: {ambition_text}

Motivation:
{selected_info['why_now']}

Knowledge gap:
{selected_info['gap']}

Possible approach:
Use {', '.join(method_focus) if method_focus else 'selected observations and models'} focused on {', '.join(region_focus) if region_focus else 'a suitable Antarctic case region'}. The goal is to connect mechanism, observation, and uncertainty rather than only summarize the paper.

Expected output:
1. A concept map of the mechanism.
2. A small evidence table linking observations to physical interpretation.
3. A visual figure or interactive module that explains the research direction.
4. A short uncertainty paragraph explaining what remains unknown.

Why this fits your Atlas:
{selected_info['student_angle']}"""
        st.text_area("Generated research proposal seed", proposal, height=430)
        st.download_button(
            "Download proposal seed as .txt",
            proposal,
            file_name=f"research_direction_{selected_direction.lower().replace(' ', '_').replace('-', '_')}.txt",
            mime="text/plain",
            use_container_width=True
        )

    st.divider()
    st.subheader("Research seed cards")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        st.markdown(f"""
        <div class="direction-output-box">
          <b>Key gap</b><br>{selected_info['gap']}<br><br>
          <b>Beginner-researcher angle</b><br>{selected_info['student_angle']}
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("**Starter questions**")
        for sq in selected_info["starter_questions"]:
            st.write(f"- {sq}")


elif module == "Antarctic System Explorer":
    st.markdown("""
    <style>
      /* Antarctic System Explorer: online-safe responsive controls. */
      .block-container {
        padding-top: 2.35rem !important;
      }
      h1, h2, h3 {
        margin-top: .38rem !important;
        margin-bottom: .38rem !important;
      }

      /* Keep controls compact without forcing columns into a single crowded strip. */
      div[data-testid="stVerticalBlock"] { gap: .20rem !important; }
      div[data-testid="stHorizontalBlock"] { gap: .55rem !important; }
      div[data-testid="stSelectbox"] { margin-top: 0 !important; }
      div[data-testid="stToggle"] {
        margin-top: 0 !important;
        padding-top: 0 !important;
        min-height: 1.9rem !important;
      }
      div[data-testid="stSelectbox"] > label {
        padding-bottom: .18rem !important;
      }
      div[data-testid="stSelectbox"] label,
      div[data-testid="stToggle"] label {
        margin-bottom: .34rem !important;
        font-size: .82rem !important;
        font-weight: 760 !important;
      }

      .system-title-row {
        display: flex;
        align-items: baseline;
        gap: 18px;
        margin: .95rem 0 .58rem 0;
        flex-wrap: wrap;
      }
      .system-title-row .system-title {
        margin: 0;
        color: #f8fbff;
        font-size: clamp(2.05rem, 4vw, 2.72rem);
        line-height: 1.18;
        font-weight: 800;
        letter-spacing: 0;
      }
      .system-title-row .system-inline-hint {
        color: rgba(188, 221, 239, .72);
        font-size: .84rem;
        line-height: 1.25;
        font-weight: 500;
        max-width: 980px;
      }
      .system-control-strip {
        margin-top: .10rem;
        padding: 0;
        border-radius: 0;
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
      }
      .system-control-title {
        margin: .42rem 0 .34rem 0 !important;
        padding-bottom: .02rem !important;
        font-size: .84rem;
        font-weight: 850;
        letter-spacing: .01em;
        color: rgba(158, 216, 245, .82);
      }
      .system-layer-row {
        margin-top: .12rem !important;
        margin-left: 0 !important;
      }

      /* Observation layer buttons: compact translucent pills, equal width, deployment-safe. */
      div.stButton > button {
        min-height: 44px !important;
        height: 44px !important;
        border-radius: 999px !important;
        padding: .48rem .78rem !important;
        font-size: .84rem !important;
        line-height: 1.05 !important;
        font-weight: 780 !important;
        white-space: nowrap !important;
        background: rgba(56, 189, 248, 0.34) !important;
        border: 1px solid rgba(125, 211, 252, 0.58) !important;
        color: rgba(232, 250, 255, 0.98) !important;
        text-shadow: 0 0 6px rgba(255,255,255,0.15);
        box-shadow:
          0 0 4px rgba(56, 189, 248, 0.26),
          0 0 14px rgba(56, 189, 248, 0.18),
          inset 0 0 2px rgba(224,252,255,0.16);
        backdrop-filter: blur(8px);
        transition: all 0.16s ease !important;
      }
      div.stButton > button[kind="primary"] {
        background: rgba(56, 189, 248, 0.52) !important;
        border-color: rgba(186, 230, 253, 0.90) !important;
        box-shadow:
          0 0 8px rgba(56, 189, 248, 0.44),
          0 0 24px rgba(56, 189, 248, 0.30),
          inset 0 0 4px rgba(224,252,255,0.22) !important;
      }
      div.stButton > button:hover {
        background: rgba(14, 165, 233, 0.56) !important;
        border-color: rgba(186, 230, 253, 0.92) !important;
        transform: translateY(-1px);
      }

      /* Let the visualization start close to the controls without overlap. */
      iframe[title="streamlit_component.streamlit.components.v1.html"] {
        margin-top: .05rem !important;
      }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="system-title-row">
      <div class="system-title">&#128752; Antarctic System Explorer</div>
      <div class="system-inline-hint">
        Explore how different observation tools see the same Antarctic case study. Choose a glacier or ice-shelf case, then switch the sensor layer to see what that tool would reveal.
      </div>
    </div>
    """, unsafe_allow_html=True)

    cases = {
        "Thwaites Glacier": {
            "region": "West Antarctica / Amundsen Sea Sector",
            "type": "Fast outlet glacier",
            "main_theme": "Ocean-driven thinning, grounding-line retreat, and MISI-like vulnerability",
            "location_label": "Amundsen Sea Sector",
            "coords": "~75°S, 106°W",
            "base_note": "Thwaites is often discussed as one of the most vulnerable WAIS glaciers because warm ocean water can thin its ice shelf and reduce buttressing.",
            "visual_seed": "thwaites",
            "tools": {
                "Satellite Altimetry": {
                    "icon": "*",
                    "measures": "Surface elevation change",
                    "observed": "Surface lowering and dynamic thinning near the glacier trunk and grounding zone.",
                    "result": "The satellite-era record indicates strong thinning in the Amundsen Sea sector.",
                    "interpretation": "Lower surface elevation is consistent with ice-shelf thinning and faster discharge of grounded ice.",
                    "visual": "Laser/radar tracks scan across the glacier while a blue-to-red thinning layer appears over the trunk.",
                    "process": "Elevation loss ->thinner ice shelf ->weaker buttressing ->faster flow"
                },
                "InSAR Velocity": {
                    "icon": "*",
                    "measures": "Ice velocity and deformation",
                    "observed": "Fast flow and acceleration toward the floating ice shelf.",
                    "result": "Velocity patterns reveal where ice discharge is concentrated and where flow responds to buttressing loss.",
                    "interpretation": "Faster flow suggests reduced resistance near the grounding line and shelf front.",
                    "visual": "Orange velocity vectors appear over the glacier trunk and lengthen downstream.",
                    "process": "Phase difference ->displacement ->velocity field ->ice discharge"
                },
                "GRACE / GRACE-FO": {
                    "icon": "*",
                    "measures": "Regional mass change from gravity",
                    "observed": "Large-scale negative mass balance in West Antarctica.",
                    "result": "GRACE-like observations connect glacier change to regional mass loss.",
                    "interpretation": "Mass loss contributes to global mean sea-level rise, but requires GIA correction.",
                    "visual": "A broad red gravity-anomaly style field covers the regional basin.",
                    "process": "Gravity change ->mass balance ->sea-level contribution"
                },
                "GPS / GNSS": {
                    "icon": "*",
                    "measures": "Point motion and bedrock response",
                    "observed": "Sparse station-style points track crustal motion and local displacement.",
                    "result": "GNSS helps separate ice-mass change from solid-Earth motion.",
                    "interpretation": "This is important for constraining GIA and interpreting gravity-based mass estimates.",
                    "visual": "Station markers pulse, with small vectors showing motion/uplift.",
                    "process": "Station position ->crustal motion ->GIA correction"
                },
                "Ice-penetrating Radar": {
                    "icon": "*",
                    "measures": "Ice thickness, bed topography, internal layers",
                    "observed": "Bed geometry and possible retrograde slopes beneath the glacier system.",
                    "result": "Radar-style profiles reveal the hidden boundary conditions controlling retreat.",
                    "interpretation": "Bed topography determines whether retreat can become self-sustaining.",
                    "visual": "Radar flight lines and a glowing subglacial cross-section appear beneath the ice.",
                    "process": "Radar echo ->bed map ->instability assessment"
                },
                "Ice / Marine Sediment Cores": {
                    "icon": "*",
                    "measures": "Past climate and retreat history",
                    "observed": "Marine records help reconstruct previous grounding-line positions and retreat episodes.",
                    "result": "Paleo evidence extends interpretation beyond the short satellite era.",
                    "interpretation": "Past retreat provides context for how the system may respond to future forcing.",
                    "visual": "Core sites appear offshore, connected to a time-depth archive strip.",
                    "process": "Core record ->past retreat ->future sensitivity constraint"
                }
            }
        },
        "Pine Island Glacier": {
            "region": "West Antarctica / Amundsen Sea Sector",
            "type": "Fast outlet glacier",
            "main_theme": "CDW intrusion, ice-shelf thinning, grounding-line retreat",
            "location_label": "Pine Island Bay",
            "coords": "~75°S, 100°W",
            "base_note": "Pine Island Glacier is a classic example of rapid retreat linked to warm Circumpolar Deep Water reaching the ice-shelf cavity.",
            "visual_seed": "pine",
            "tools": {
                "Satellite Altimetry": {
                    "icon": "*",
                    "measures": "Surface elevation change",
                    "observed": "Strong thinning along the glacier and ice shelf.",
                    "result": "Altimetry-style evidence shows where surface lowering is concentrated.",
                    "interpretation": "Surface lowering reflects dynamic thinning and enhanced basal melting.",
                    "visual": "Repeated satellite tracks reveal a thinning corridor near the grounding zone.",
                    "process": "Repeated elevation profiles ->thinning map ->dynamic response"
                },
                "InSAR Velocity": {
                    "icon": "*",
                    "measures": "Ice velocity and grounding-zone motion",
                    "observed": "Fast outlet flow toward Pine Island Bay.",
                    "result": "Velocity vectors show the main discharge pathway.",
                    "interpretation": "Acceleration is consistent with reduced ice-shelf buttressing.",
                    "visual": "Dense downstream arrows highlight the fast-flowing trunk.",
                    "process": "SAR phase ->velocity ->ice discharge"
                },
                "GRACE / GRACE-FO": {
                    "icon": "*",
                    "measures": "Regional mass balance",
                    "observed": "Part of the broader Amundsen Sea mass-loss signal.",
                    "result": "Gravity change captures integrated regional loss rather than local glacier detail.",
                    "interpretation": "Useful for linking local dynamic change to total mass loss.",
                    "visual": "A basin-scale mass-loss halo overlays the map.",
                    "process": "Gravity anomaly ->regional mass trend ->sea-level signal"
                },
                "GPS / GNSS": {
                    "icon": "*",
                    "measures": "Bedrock and surface motion at stations",
                    "observed": "Point observations can help constrain solid-Earth response.",
                    "result": "GNSS is precise but spatially sparse.",
                    "interpretation": "Important for separating ice signals from bedrock uplift.",
                    "visual": "Station points blink at the margin with uplift arrows.",
                    "process": "Position time series ->uplift rate ->correction"
                },
                "Ice-penetrating Radar": {
                    "icon": "*",
                    "measures": "Bed and cavity geometry",
                    "observed": "Troughs and bed features that route ocean heat toward the grounding line.",
                    "result": "Radar and bathymetry reveal pathways for warm water access.",
                    "interpretation": "Geometry helps explain why Pine Island is sensitive to ocean forcing.",
                    "visual": "Subglacial troughs glow beneath the ice image.",
                    "process": "Bed sounding ->trough geometry ->ocean access pathway"
                },
                "Ice / Marine Sediment Cores": {
                    "icon": "*",
                    "measures": "Past retreat and ocean conditions",
                    "observed": "Marine archives record earlier ice-margin behavior in Pine Island Trough.",
                    "result": "Sediment evidence helps test whether retreat was rapid or episodic.",
                    "interpretation": "Past retreat constrains model scenarios for future instability.",
                    "visual": "Offshore core dots and a layered sediment strip appear.",
                    "process": "Sediment layers ->retreat history ->model constraint"
                }
            }
        },
        "Totten Glacier": {
            "region": "East Antarctica / Sabrina Coast",
            "type": "East Antarctic outlet glacier",
            "main_theme": "Warm water access to a marine-based EAIS sector",
            "location_label": "Sabrina Coast",
            "coords": "~67°S, 116°E",
            "base_note": "Totten Glacier shows that parts of East Antarctica can also be sensitive to ocean heat and marine-based bed geometry.",
            "visual_seed": "totten",
            "tools": {
                "Satellite Altimetry": {
                    "icon": "*",
                    "measures": "Surface height change",
                    "observed": "Surface lowering in a vulnerable East Antarctic outlet system.",
                    "result": "Altimetry helps detect whether EAIS outlet glaciers are thinning or thickening.",
                    "interpretation": "Thinning suggests ocean forcing can affect parts of East Antarctica too.",
                    "visual": "Satellite tracks cross an East Antarctic outlet with localized thinning colors.",
                    "process": "Elevation change ->outlet thinning ->EAIS vulnerability"
                },
                "InSAR Velocity": {
                    "icon": "*",
                    "measures": "Ice velocity",
                    "observed": "Fast flow through the Totten outlet toward the coast.",
                    "result": "InSAR-style velocity mapping identifies dynamic outlet behavior.",
                    "interpretation": "Flow pattern links inland catchment ice to coastal forcing.",
                    "visual": "Flow arrows converge toward the outlet glacier trunk.",
                    "process": "Velocity field ->discharge pathway ->dynamic thinning"
                },
                "GRACE / GRACE-FO": {
                    "icon": "*",
                    "measures": "Large-scale mass balance",
                    "observed": "EAIS mass change is harder to isolate because signals are broad and uncertain.",
                    "result": "GRACE provides continent-scale mass context but local attribution is limited.",
                    "interpretation": "Needs careful regional interpretation and GIA correction.",
                    "visual": "A broad, softer mass-balance field overlays the East Antarctic sector.",
                    "process": "Gravity trend ->regional mass estimate ->uncertainty"
                },
                "GPS / GNSS": {
                    "icon": "*",
                    "measures": "Crustal motion and vertical uplift",
                    "observed": "Sparse geodetic constraints for East Antarctic solid-Earth response.",
                    "result": "GNSS helps improve corrections to mass-balance estimates.",
                    "interpretation": "Especially important where mass-change signals are subtle.",
                    "visual": "Few station markers emphasize sparse but precise measurements.",
                    "process": "GNSS station ->uplift correction ->better mass estimate"
                },
                "Ice-penetrating Radar": {
                    "icon": "*",
                    "measures": "Ice thickness, bed, subglacial basin structure",
                    "observed": "Marine-based geometry and bed pathways beneath the outlet system.",
                    "result": "Radar is central for identifying hidden EAIS vulnerabilities.",
                    "interpretation": "Bed shape controls whether ocean-driven retreat can propagate inland.",
                    "visual": "A deep basin cross-section appears below the satellite-style surface.",
                    "process": "Radar profile ->marine basin ->retreat sensitivity"
                },
                "Ice / Marine Sediment Cores": {
                    "icon": "*",
                    "measures": "Past EAIS and ocean conditions",
                    "observed": "Marine sediment records can indicate past margin retreat and ocean warmth.",
                    "result": "Paleo data helps evaluate long-term East Antarctic sensitivity.",
                    "interpretation": "Useful because satellite records are too short for millennial-scale behavior.",
                    "visual": "Core archive marks appear along the continental shelf.",
                    "process": "Paleo archive ->warm-period behavior ->future analog"
                }
            }
        },
        "Larsen B Ice Shelf": {
            "region": "Antarctic Peninsula",
            "type": "Collapsed ice shelf",
            "main_theme": "Surface meltwater, hydrofracturing, and buttressing loss",
            "location_label": "Antarctic Peninsula",
            "coords": "~65°S, 61°W",
            "base_note": "Larsen B is a famous example of ice-shelf collapse followed by acceleration of tributary glaciers after buttressing was lost.",
            "visual_seed": "larsen",
            "tools": {
                "Satellite Altimetry": {
                    "icon": "*",
                    "measures": "Surface elevation before/after collapse",
                    "observed": "Elevation and surface morphology changed dramatically after shelf breakup.",
                    "result": "Altimetry-like monitoring helps quantify post-collapse glacier thinning.",
                    "interpretation": "After shelf loss, tributary glaciers can accelerate and thin.",
                    "visual": "Before/after scan lines reveal lowered tributary glacier surfaces.",
                    "process": "Ice-shelf loss ->tributary thinning ->reduced stability"
                },
                "InSAR Velocity": {
                    "icon": "*",
                    "measures": "Tributary glacier acceleration",
                    "observed": "Glaciers feeding the former shelf accelerated after collapse.",
                    "result": "Velocity mapping directly shows the dynamic impact of buttressing loss.",
                    "interpretation": "This is a clear example of why floating shelves matter for grounded ice.",
                    "visual": "Arrows behind the former shelf become longer and brighter.",
                    "process": "Shelf collapse ->lower back stress ->faster tributary flow"
                },
                "GRACE / GRACE-FO": {
                    "icon": "*",
                    "measures": "Regional mass change",
                    "observed": "Regional signal is smaller and harder to isolate than WAIS basin-scale loss.",
                    "result": "GRACE gives context but is not the primary local diagnostic here.",
                    "interpretation": "Better used with altimetry and velocity for this case.",
                    "visual": "A faint regional mass-change layer appears over the Peninsula.",
                    "process": "Regional gravity ->mass context ->multi-sensor interpretation"
                },
                "GPS / GNSS": {
                    "icon": "*",
                    "measures": "Local motion and crustal response",
                    "observed": "Point measurements can support local deformation and uplift context.",
                    "result": "GNSS is useful but sparse relative to satellite imagery.",
                    "interpretation": "Best interpreted together with optical/SAR records.",
                    "visual": "A few station vectors appear along the Peninsula.",
                    "process": "Station motion ->local deformation ->context"
                },
                "Ice-penetrating Radar": {
                    "icon": "*",
                    "measures": "Shelf and tributary geometry",
                    "observed": "Internal structure and thickness help explain shelf weakness and tributary response.",
                    "result": "Radar can support understanding of mechanical vulnerability.",
                    "interpretation": "Geometry and crevasse structure affect collapse potential.",
                    "visual": "Crack-like internal layers and radar profiles appear across the shelf.",
                    "process": "Internal structure ->fracture vulnerability ->collapse risk"
                },
                "Ice / Marine Sediment Cores": {
                    "icon": "*",
                    "measures": "Longer-term shelf and climate history",
                    "observed": "Records can help determine whether collapse was unusual in recent millennia.",
                    "result": "Paleo context tells whether modern breakup exceeds natural variability.",
                    "interpretation": "Important for connecting recent atmospheric warming to shelf stability.",
                    "visual": "Core archive appears near the shelf front and former embayment.",
                    "process": "Archive record ->shelf history ->modern anomaly"
                }
            }
        },
        "Wilkes Subglacial Basin": {
            "region": "East Antarctica",
            "type": "Marine-based subglacial basin",
            "main_theme": "Bed topography, marine-based ice, long-term sensitivity",
            "location_label": "Wilkes Land",
            "coords": "~70°S, 140°E",
            "base_note": "Wilkes Subglacial Basin is important because marine-based East Antarctic ice could be vulnerable if warming and bed geometry allow retreat to propagate inland.",
            "visual_seed": "wilkes",
            "tools": {
                "Satellite Altimetry": {
                    "icon": "*",
                    "measures": "Broad surface elevation trends",
                    "observed": "Surface elevation provides a first view of present-day change over a large basin.",
                    "result": "Altimetry helps detect whether the basin is stable, thinning, or thickening.",
                    "interpretation": "Present changes must be interpreted against snowfall and firn processes.",
                    "visual": "Wide satellite tracks sweep across the basin surface.",
                    "process": "Elevation trend ->basin-scale change ->mass-balance clue"
                },
                "InSAR Velocity": {
                    "icon": "*",
                    "measures": "Outlet velocity patterns",
                    "observed": "Velocity fields show where ice can drain from the basin toward the coast.",
                    "result": "InSAR identifies fast-flow corridors and outlet controls.",
                    "interpretation": "Flow pathways connect interior basin geometry to coastal vulnerability.",
                    "visual": "Flow arrows trace drainage from the basin toward the margin.",
                    "process": "Velocity map ->drainage structure ->discharge risk"
                },
                "GRACE / GRACE-FO": {
                    "icon": "*",
                    "measures": "Large-scale mass change",
                    "observed": "Broad gravity signals help monitor basin-scale mass balance.",
                    "result": "Spatial resolution is coarse, so interpretation is regional.",
                    "interpretation": "GIA correction is essential in East Antarctica.",
                    "visual": "A broad mass-balance wash appears across Wilkes Land.",
                    "process": "Gravity field ->basin mass trend ->GIA-sensitive estimate"
                },
                "GPS / GNSS": {
                    "icon": "*",
                    "measures": "Crustal uplift and solid-Earth correction",
                    "observed": "Sparse but valuable constraints on vertical bedrock motion.",
                    "result": "GNSS improves the correction needed for gravity-derived ice mass.",
                    "interpretation": "Important for reducing uncertainty in East Antarctic mass balance.",
                    "visual": "Uplift vectors appear as fixed station points over the basin margin.",
                    "process": "Uplift rate ->GIA model ->corrected ice mass"
                },
                "Ice-penetrating Radar": {
                    "icon": "*",
                    "measures": "Hidden basin geometry and bed slope",
                    "observed": "Deep subglacial basin and retrograde-bed style geometry.",
                    "result": "Radar is the most visually important tool for this case because the key feature is hidden beneath ice.",
                    "interpretation": "Bed topography controls long-term marine ice-sheet sensitivity.",
                    "visual": "A large glowing subglacial basin appears beneath the ice surface.",
                    "process": "Bed echo ->basin geometry ->marine instability potential"
                },
                "Ice / Marine Sediment Cores": {
                    "icon": "*",
                    "measures": "Past warm-period ice extent",
                    "observed": "Paleo records test whether marine-based EAIS sectors retreated in past warm climates.",
                    "result": "Core evidence helps constrain long-term sensitivity that satellites cannot capture.",
                    "interpretation": "Useful for Pliocene and interglacial analogs.",
                    "visual": "Archive markers connect the basin to past warm-period evidence.",
                    "process": "Past margin record ->warm-climate response ->future constraint"
                }
            }
        }
    }

    tool_order = ["Satellite Altimetry", "InSAR Velocity", "GRACE / GRACE-FO", "GPS / GNSS", "Ice-penetrating Radar", "Ice / Marine Sediment Cores"]

    layer_label_map = {
        "Satellite Altimetry": "Altimetry",
        "InSAR Velocity": "InSAR",
        "GRACE / GRACE-FO": "GRACE",
        "GPS / GNSS": "GNSS",
        "Ice-penetrating Radar": "Radar",
        "Ice / Marine Sediment Cores": "Cores"
    }

    if "system_tool_select" not in st.session_state or st.session_state["system_tool_select"] not in tool_order:
        st.session_state["system_tool_select"] = tool_order[0]
    if "system_visual_layers" not in st.session_state or not isinstance(st.session_state["system_visual_layers"], list):
        st.session_state["system_visual_layers"] = [st.session_state["system_tool_select"]]

    st.markdown("<div class='system-control-strip'>", unsafe_allow_html=True)
    st.caption("Conceptual visualization: the base scene and sensor layers illustrate observation logic, not downloaded raw remote-sensing data.")

    # Deployment-safe layout: keep Case Study and Multi-layer mode on the first row,
    # then give Observation layers a full row. This prevents Streamlit Cloud / browser
    # width differences from squeezing the toggle to the far right or overlapping pills.
    case_col, mode_col = st.columns([0.58, 0.42], gap="large")
    with case_col:
        selected_case = st.selectbox("Case Study", list(cases.keys()), key="system_case_select")
    with mode_col:
        layer_mode = st.toggle(
            "Multi-layer mode",
            value=False,
            key="system_multilayer_mode",
            help="Off: buttons choose the primary observation layer. On: buttons become multi-select visible layers."
        )

    st.markdown("<div class='system-control-title'>Observation layers</div>", unsafe_allow_html=True)
    st.markdown("<div class='system-layer-row'>", unsafe_allow_html=True)
    layer_cols = st.columns([1, 1, 1, 1, 1, 1], gap="small")
    for i, layer_name in enumerate(tool_order):
        with layer_cols[i]:
            if layer_mode:
                active = layer_name in st.session_state["system_visual_layers"]
                if st.button(
                    layer_label_map[layer_name],
                    key=f"system_layer_btn_multi_{i}",
                    type="primary" if active else "secondary",
                    use_container_width=True
                ):
                    current_layers = list(st.session_state.get("system_visual_layers", []))
                    if layer_name in current_layers:
                        current_layers = [x for x in current_layers if x != layer_name]
                    else:
                        current_layers.append(layer_name)
                    if not current_layers:
                        current_layers = [st.session_state["system_tool_select"]]
                    st.session_state["system_visual_layers"] = current_layers
                    st.rerun()
            else:
                active = layer_name == st.session_state["system_tool_select"]
                if st.button(
                    layer_label_map[layer_name],
                    key=f"system_layer_btn_single_{i}",
                    type="primary" if active else "secondary",
                    use_container_width=True
                ):
                    st.session_state["system_tool_select"] = layer_name
                    st.session_state["system_visual_layers"] = [layer_name]
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    selected_tool = st.session_state["system_tool_select"]
    if layer_mode:
        visual_layers = [layer for layer in st.session_state.get("system_visual_layers", []) if layer in tool_order]
        if not visual_layers:
            visual_layers = [selected_tool]
        if selected_tool not in visual_layers:
            selected_tool = visual_layers[0]
            st.session_state["system_tool_select"] = selected_tool
    else:
        visual_layers = [selected_tool]
        st.session_state["system_visual_layers"] = visual_layers

    case = cases[selected_case]
    tool = case["tools"][selected_tool]

    explorer_payload = {
        "case_name": selected_case,
        "case": case,
        "tool_name": selected_tool,
        "tool": tool,
        "tool_order": tool_order
    }

    explorer_html = """
    <div id="sensor-explorer-root">
      <style>
        #sensor-explorer-root {
          width: 100%; height: 655px; overflow: hidden; position: relative; border-radius: 32px; isolation:isolate;
          color: #edf8ff; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background:
            radial-gradient(circle at 20% 18%, rgba(78,163,241,.24), transparent 30%),
            radial-gradient(circle at 86% 20%, rgba(149,117,205,.18), transparent 26%),
            linear-gradient(135deg, #030712 0%, #07111f 48%, #020617 100%);
          background-size: 135% 135%, 150% 150%, 100% 100%;
          box-shadow: inset 0 0 100px rgba(78,163,241,.14), 0 26px 82px rgba(0,0,0,.34);
          animation: sensorNebulaDrift 24s ease-in-out infinite;
        }
        #sensor-explorer-root * { box-sizing: border-box; }
        #sensor-explorer-root::before,
        #sensor-explorer-root::after { content:""; position:absolute; inset:-18%; pointer-events:none; z-index:1; }
        #sensor-explorer-root::before {
          background:linear-gradient(115deg, transparent 8%, rgba(255,255,255,.055) 38%, rgba(126,220,255,.10) 49%, transparent 63%);
          mix-blend-mode:screen; opacity:.70; animation:sensorGlassDrift 13s ease-in-out infinite;
        }
        #sensor-explorer-root::after {
          background:radial-gradient(ellipse at 52% 52%, transparent 35%, rgba(2,6,23,.36) 84%);
          z-index:1;
        }
        @keyframes sensorNebulaDrift { 0%,100% { background-position:0% 0%, 100% 18%, 0 0; } 50% { background-position:8% 7%, 91% 26%, 0 0; } }
        @keyframes sensorGlassDrift { 0%,100% { transform:translateX(-7%) rotate(-3deg); opacity:.52; } 50% { transform:translateX(7%) rotate(3deg); opacity:.86; } }
        @keyframes sensorPanelIn { from { opacity:0; transform:translateY(12px) scale(.985); } to { opacity:1; transform:translateY(0) scale(1); } }
        .sensor-title {
          position:absolute; top:10px; left:22px; z-index:9;
          max-width: calc(100% - 44px); width: auto;
          display:flex; align-items:center; gap:16px;
          padding:9px 13px; border-radius:18px; overflow:hidden; background:radial-gradient(circle at 14% 0%, rgba(255,255,255,.10), transparent 34%), linear-gradient(180deg, rgba(14,27,49,.60), rgba(4,12,25,.40));
          border:1px solid rgba(210,238,255,.20); backdrop-filter: blur(18px) saturate(1.28);
          box-shadow:inset 0 1px 0 rgba(255,255,255,.12), 0 16px 44px rgba(0,0,0,.18);
          animation:sensorPanelIn .36s cubic-bezier(.2,.8,.2,1) both;
          white-space: nowrap;
        }
        .sensor-title h2 {
          margin:0;
          font-size:20px;
          letter-spacing:.2px;
          flex:0 0 auto;
          white-space:nowrap;
        }
        .sensor-title p {
          margin:0;
          color:rgba(230,245,255,.72);
          font-size:12px;
          line-height:1.1;
          white-space:nowrap;
          overflow:hidden;
          text-overflow:ellipsis;
        }
        .sat-frame {
          position:absolute; left:22px; top:62px; width:66%; height:570px; border-radius:26px; overflow:hidden;
          z-index:4; border:1px solid rgba(210,238,255,.22); background:#06111e;
          box-shadow: 0 24px 74px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.10), inset 0 0 62px rgba(110,210,255,.10);
          animation:sensorPanelIn .42s cubic-bezier(.2,.8,.2,1) both;
        }
        .sat-frame::before { content:""; position:absolute; inset:-60% -30%; z-index:2; pointer-events:none; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.08) 38%, rgba(126,220,255,.12) 48%, transparent 66%); opacity:.50; transform:translateX(-26%) rotate(10deg); }
        .sat-image {
          position:absolute; inset:0;
          background:
            radial-gradient(ellipse at 22% 36%, rgba(245,252,255,.92) 0%, rgba(205,232,244,.82) 20%, rgba(94,138,162,.20) 38%, transparent 55%),
            radial-gradient(ellipse at 58% 52%, rgba(255,255,255,.84) 0%, rgba(205,230,238,.55) 18%, rgba(45,88,118,.12) 45%, transparent 62%),
            radial-gradient(ellipse at 76% 64%, rgba(145,220,238,.24), transparent 34%),
            linear-gradient(135deg, #0b2940 0%, #163b52 35%, #081624 100%);
          filter: saturate(1.04) contrast(1.06);
        }
        .sat-image::before {
          content:""; position:absolute; inset:-20%; opacity:.26;
          background-image:
            repeating-linear-gradient(18deg, rgba(255,255,255,.20) 0 1px, transparent 1px 18px),
            repeating-linear-gradient(105deg, rgba(255,255,255,.10) 0 1px, transparent 1px 26px);
          transform: rotate(-2deg);
        }
        .sat-image::after {
          content:""; position:absolute; inset:0; opacity:.30; mix-blend-mode: screen;
          background: radial-gradient(circle at 50% 50%, transparent 0 38%, rgba(0,0,0,.55) 86%);
        }
        .case-thwaites .sat-image { background:
          radial-gradient(ellipse at 25% 40%, rgba(250,252,255,.95), rgba(209,232,242,.82) 22%, rgba(64,98,130,.14) 45%, transparent 64%),
          radial-gradient(ellipse at 72% 70%, rgba(0,110,155,.45), rgba(3,22,45,.88) 58%),
          linear-gradient(135deg, #092034, #13324b 46%, #03111f); }
        .case-pine .sat-image { background:
          radial-gradient(ellipse at 32% 42%, rgba(248,252,255,.96), rgba(215,236,246,.80) 24%, rgba(58,90,122,.20) 48%, transparent 64%),
          radial-gradient(ellipse at 78% 55%, rgba(52,160,194,.42), rgba(3,20,39,.88) 60%),
          linear-gradient(145deg, #082132, #153d55 48%, #061522); }
        .case-totten .sat-image { background:
          radial-gradient(ellipse at 68% 38%, rgba(250,252,255,.96), rgba(220,239,247,.78) 26%, rgba(65,100,128,.16) 50%, transparent 66%),
          radial-gradient(ellipse at 18% 70%, rgba(35,145,190,.42), rgba(4,23,44,.88) 60%),
          linear-gradient(135deg, #0d273b, #174058 48%, #061421); }
        .case-larsen .sat-image { background:
          radial-gradient(ellipse at 50% 48%, rgba(247,252,255,.94), rgba(200,228,238,.80) 18%, rgba(88,128,148,.24) 38%, transparent 54%),
          linear-gradient(100deg, #0b3148 0%, #194962 48%, #061421 100%); }
        .case-wilkes .sat-image { background:
          radial-gradient(ellipse at 52% 42%, rgba(250,252,255,.97), rgba(224,240,248,.82) 32%, rgba(73,105,128,.22) 58%, transparent 72%),
          radial-gradient(ellipse at 80% 74%, rgba(42,150,185,.34), transparent 45%),
          linear-gradient(135deg, #09233a, #13364d 52%, #04111d); }
        .glacier-outline {
          position:absolute; left:9%; top:12%; width:62%; height:76%; border-radius:60% 44% 46% 62%;
          border:2px solid rgba(255,255,255,.34); background:rgba(255,255,255,.045);
          box-shadow: inset 0 0 40px rgba(255,255,255,.10), 0 0 25px rgba(160,230,255,.10);
          transform: rotate(-10deg);
        }
        .case-larsen .glacier-outline { left:25%; width:36%; border-radius:28% 70% 55% 42%; transform:rotate(4deg); }
        .case-wilkes .glacier-outline { left:21%; top:15%; width:58%; height:72%; border-radius:50%; transform:rotate(0deg); }
        .ocean-label, .ice-label, .case-label {
          position:absolute; z-index:3; padding:7px 10px; border-radius:999px; font-size:12px;
          background:rgba(2,6,23,.50); border:1px solid rgba(210,238,255,.20); backdrop-filter: blur(12px) saturate(1.24);
          box-shadow:inset 0 1px 0 rgba(255,255,255,.08), 0 10px 24px rgba(0,0,0,.14);
        }
        .ice-label { left:48px; bottom:36px; }
        .ocean-label { right:40px; bottom:38px; color:#bdefff; }
        .case-label { left:48px; top:36px; color:#ffffff; }
        .overlay { position:absolute; inset:0; z-index:4; pointer-events:none; animation: layerFade .42s ease both; }
        .overlay > * { animation: layerFade .52s ease both; }
        @keyframes layerFade { from { opacity:0; transform:translateY(8px) scale(.985); } to { opacity:1; transform:translateY(0) scale(1); } }
        .orbit {
          position:absolute; left:8%; top:7%; width:38px; height:38px; border-radius:50%;
          background:linear-gradient(135deg, #e8fbff, #6fd4ff); box-shadow:0 0 24px rgba(120,220,255,.95);
          animation: satelliteOrbit 7s linear infinite;
        }
        .orbit::after { content:""; position:absolute; left:28px; top:17px; width:150px; height:2px; background:linear-gradient(90deg, rgba(165,235,255,.9), transparent); transform:rotate(10deg); }
        @keyframes satelliteOrbit { 0%{transform:translate(0,0)} 45%{transform:translate(610px,90px)} 100%{transform:translate(0,0)} }
        .altimetry .scan-line {
          position:absolute; top:-30%; width:3px; height:160%; background:linear-gradient(180deg, transparent, rgba(160,235,255,.95), transparent);
          box-shadow:0 0 16px rgba(128,220,255,.9); animation: scanDown 2.4s ease-in-out infinite;
        }
        .altimetry .scan-line:nth-child(1){left:25%; animation-delay:0s}.altimetry .scan-line:nth-child(2){left:42%; animation-delay:.35s}.altimetry .scan-line:nth-child(3){left:59%; animation-delay:.7s}
        @keyframes scanDown { 0%,100%{opacity:.25; transform:translateY(-18px)} 50%{opacity:1; transform:translateY(22px)} }
        .thinning-blob { position:absolute; left:37%; top:34%; width:220px; height:190px; border-radius:50%; background:radial-gradient(circle, rgba(255,100,55,.70), rgba(255,178,60,.38) 45%, transparent 72%); mix-blend-mode:screen; animation:pulse 2.2s ease-in-out infinite; }
        @keyframes pulse { 0%,100%{opacity:.45; transform:scale(.96)} 50%{opacity:.92; transform:scale(1.06)} }
        .insar .vel-arrow { position:absolute; height:4px; background:linear-gradient(90deg, rgba(255,170,55,.15), rgba(255,155,40,1)); border-radius:999px; box-shadow:0 0 12px rgba(255,145,40,.9); animation:flow 1.5s ease-in-out infinite; }
        .insar .vel-arrow::after { content:""; position:absolute; right:-7px; top:-5px; border-left:12px solid rgba(255,155,40,1); border-top:7px solid transparent; border-bottom:7px solid transparent; }
        .insar .a1{left:24%;top:38%;width:120px}.insar .a2{left:31%;top:48%;width:160px;animation-delay:.15s}.insar .a3{left:39%;top:58%;width:190px;animation-delay:.3s}.insar .a4{left:29%;top:64%;width:138px;animation-delay:.45s}
        @keyframes flow { 0%,100%{transform:translateX(-6px);opacity:.55} 50%{transform:translateX(12px);opacity:1} }
        .grace .mass-blob { position:absolute; left:20%; top:24%; width:430px; height:360px; border-radius:50%; background:radial-gradient(circle, rgba(255,68,68,.68), rgba(255,132,60,.42) 42%, rgba(0,120,255,.10) 68%, transparent 78%); filter:blur(2px); mix-blend-mode:screen; animation:pulse 2.8s ease-in-out infinite; }
        .gnss .station { position:absolute; width:16px; height:16px; border-radius:50%; background:#9dffb6; border:2px solid white; box-shadow:0 0 16px rgba(120,255,170,.9); animation:pulse 1.8s infinite; }
        .gnss .station::after { content:"→"; position:absolute; left:14px; top:-18px; color:#9dffb6; font-weight:900; font-size:22px; text-shadow:0 0 12px rgba(120,255,170,.95); }
        .gnss .s1{left:31%;top:42%}.gnss .s2{left:48%;top:57%;animation-delay:.3s}.gnss .s3{left:62%;top:36%;animation-delay:.6s}.gnss .s4{left:24%;top:66%;animation-delay:.9s}
        .radar .radar-line { position:absolute; height:3px; background:rgba(255,255,255,.80); box-shadow:0 0 16px rgba(255,255,255,.88); transform:rotate(-12deg); }
        .radar .r1{left:22%;top:34%;width:340px}.radar .r2{left:26%;top:50%;width:300px}.radar .r3{left:30%;top:65%;width:260px}
        .radar .basin { position:absolute; left:24%; bottom:58px; width:430px; height:92px; border-radius:0 0 60% 60%; border-bottom:4px solid rgba(255,214,82,.95); background:linear-gradient(180deg, transparent, rgba(255,214,82,.20)); box-shadow:0 18px 30px rgba(255,214,82,.25); }
        .cores .core-dot { position:absolute; width:18px; height:18px; border-radius:50%; background:#f6c85f; border:2px solid white; box-shadow:0 0 16px rgba(246,200,95,.9); }
        .cores .c1{left:68%;top:62%}.cores .c2{left:75%;top:50%}.cores .c3{left:61%;top:72%}
        .cores .archive { position:absolute; right:54px; top:88px; width:86px; height:250px; border-radius:14px; background:repeating-linear-gradient(180deg, rgba(255,255,255,.86) 0 18px, rgba(155,210,230,.82) 18px 35px, rgba(80,120,145,.70) 35px 52px); border:1px solid rgba(255,255,255,.55); box-shadow:0 0 20px rgba(255,255,255,.25); }
        .legend-pill { position:absolute; left:32px; bottom:76px; z-index:6; padding:9px 13px; border-radius:999px; background:rgba(2,6,23,.62); border:1px solid rgba(210,238,255,.18); color:#cfeeff; font-size:12px; }
        .side-card {
          position:absolute; right:22px; top:62px; width:30%; height:570px; border-radius:26px; padding:18px;
          z-index:6; background:radial-gradient(circle at 12% 0%, rgba(255,255,255,.12), transparent 34%), linear-gradient(180deg, rgba(12,25,46,.90), rgba(5,13,27,.70)); border:1px solid rgba(210,238,255,.30);
          box-shadow:0 24px 74px rgba(0,0,0,.40), inset 0 1px 0 rgba(255,255,255,.14), inset 0 -1px 0 rgba(126,220,255,.08); backdrop-filter:blur(24px) saturate(1.38); overflow:auto; scrollbar-width:none;
          animation:sensorPanelIn .46s cubic-bezier(.2,.8,.2,1) both;
        }
        .side-card::-webkit-scrollbar{display:none}.badge{display:inline-flex; gap:7px; align-items:center; padding:7px 11px; border-radius:999px; color:#bfe6ff; background:rgba(78,163,241,.14); border:1px solid rgba(142,207,255,.25); font-size:12px; font-weight:700}.side-card h3{margin:15px 0 8px 0; font-size:24px}.meta{color:rgba(235,248,255,.70); font-size:13px; line-height:1.45}.label{margin-top:15px; color:#8ccfff; font-size:11px; text-transform:uppercase; letter-spacing:1px}.side-card p{margin:6px 0 0 0; color:rgba(239,248,255,.86); line-height:1.45; font-size:13px}.insight-card{margin-top:11px; padding:12px 13px; border-radius:17px; background:rgba(255,255,255,.058); border:1px solid rgba(210,238,255,.13); box-shadow: inset 0 1px 0 rgba(255,255,255,.06), inset 0 0 22px rgba(78,163,241,.045); transition:transform .18s ease, border-color .18s ease}.insight-card:hover{transform:translateY(-1px); border-color:rgba(126,220,255,.28)}.insight-card .k{font-size:11px; text-transform:uppercase; letter-spacing:.9px; color:#8ccfff; font-weight:800}.insight-card .v{margin-top:5px; color:rgba(239,248,255,.89); font-size:13px; line-height:1.42}.tool-grid{display:grid; grid-template-columns:1fr 1fr; gap:9px; margin-top:15px}.tool-mini{padding:9px 10px; border-radius:14px; background:rgba(255,255,255,.052); border:1px solid rgba(255,255,255,.12); font-size:12px; color:rgba(239,248,255,.76); transition:transform .18s ease, border-color .18s ease}.tool-mini:hover{transform:translateY(-1px); border-color:rgba(126,220,255,.28)}.tool-mini.layer-on{border-color:rgba(74,222,128,.42); background:rgba(34,197,94,.10); color:#eafff0}.tool-mini.active{border-color:rgba(130,220,255,.85); background:rgba(78,163,241,.22); color:#fff; box-shadow:0 0 18px rgba(78,163,241,.18)}.synthesis{margin-top:16px; padding:13px; border-radius:16px; background:rgba(34,197,94,.08); border:1px solid rgba(74,222,128,.18); color:rgba(235,255,242,.86); font-size:13px; line-height:1.45}.process-chain{margin-top:10px; padding:12px; border-radius:14px; background:rgba(255,255,255,.052); border:1px solid rgba(255,255,255,.12); color:#d8f1ff; font-size:12px; line-height:1.45}.visible-layers{position:absolute; left:32px; top:92px; z-index:7; display:flex; gap:7px; flex-wrap:wrap; max-width:62%}.layer-chip{padding:6px 9px; border-radius:999px; background:rgba(2,6,23,.52); border:1px solid rgba(210,238,255,.18); color:#d9f4ff; font-size:11px; backdrop-filter:blur(10px)}
      </style>
      <div class="sensor-title"><h2>Multi-Sensor Evidence Explorer</h2><p>Case study as the base satellite scene; each observation tool adds a different evidence layer on top.</p></div>
      <div class="sat-frame case-__CASE_CLASS__">
        <div class="sat-image"></div><div class="glacier-outline"></div><div class="orbit"></div>
        <div class="case-label">Location: __CASE_NAME__ · __COORDS__</div><div class="ice-label">Ice / shelf surface</div><div class="ocean-label">Ocean cavity / shelf sea</div>
        <div class="visible-layers">__VISIBLE_LAYER_CHIPS__</div>
        <div class="overlay __OVERLAY_CLASS__">__OVERLAY_HTML__</div>
        <div class="legend-pill">Primary layer: __TOOL_ICON__ __TOOL_NAME__ - __MEASURES__</div>
      </div>
      <div class="side-card">
        <span class="badge">__TOOL_ICON__ Observation layer</span>
        <h3>__CASE_NAME__</h3>
        <div class="meta"><b>Region:</b> __REGION__<br><b>Type:</b> __TYPE__<br><b>Main theme:</b> __THEME__</div>
        <div class="insight-card"><div class="k">Observation</div><div class="v">__OBSERVED__</div></div>
        <div class="insight-card"><div class="k">Measurement</div><div class="v">__MEASURES__</div></div>
        <div class="insight-card"><div class="k">Visual layer</div><div class="v">__VISUAL__</div></div>
        <div class="insight-card"><div class="k">Interpretation</div><div class="v">__INTERPRETATION__</div></div>
        <div class="process-chain">__PROCESS__</div>
        <div class="tool-grid">__TOOL_GRID__</div>
        <div class="synthesis"><b>Evidence logic:</b><br>Different sensors do not duplicate each other. They measure elevation, velocity, gravity/mass, point motion, hidden bed geometry, and past archives. Together they turn one glacier from an image into a scientific system.</div>
      </div>
    </div>
    """

    def _safe_html(value):
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _overlay_for(tool_name):
        if tool_name == "Satellite Altimetry":
            return "altimetry", '<div class="scan-line"></div><div class="scan-line"></div><div class="scan-line"></div><div class="thinning-blob"></div>'
        if tool_name == "InSAR Velocity":
            return "insar", '<div class="vel-arrow a1"></div><div class="vel-arrow a2"></div><div class="vel-arrow a3"></div><div class="vel-arrow a4"></div>'
        if tool_name == "GRACE / GRACE-FO":
            return "grace", '<div class="mass-blob"></div>'
        if tool_name == "GPS / GNSS":
            return "gnss", '<div class="station s1"></div><div class="station s2"></div><div class="station s3"></div><div class="station s4"></div>'
        if tool_name == "Ice-penetrating Radar":
            return "radar", '<div class="radar-line r1"></div><div class="radar-line r2"></div><div class="radar-line r3"></div><div class="basin"></div>'
        return "cores", '<div class="core-dot c1"></div><div class="core-dot c2"></div><div class="core-dot c3"></div><div class="archive"></div>'

    overlay_items = [_overlay_for(layer) for layer in visual_layers]
    overlay_class = " ".join([cls for cls, _ in overlay_items])
    overlay_html = "".join([html for _, html in overlay_items])
    case_class = {
        "thwaites": "thwaites",
        "pine": "pine",
        "totten": "totten",
        "larsen": "larsen",
        "wilkes": "wilkes"
    }.get(case.get("visual_seed", "thwaites"), "thwaites")
    tool_grid = "".join([
        f'<div class="tool-mini {"active" if name == selected_tool else ("layer-on" if name in visual_layers else "")}">{case["tools"][name]["icon"]} {name}</div>'
        for name in tool_order
    ])
    visible_layer_chips = "".join([
        f'<span class="layer-chip">{case["tools"][name]["icon"]} {name}</span>'
        for name in visual_layers
    ])

    replacements = {
        "__CASE_CLASS__": case_class,
        "__CASE_NAME__": _safe_html(selected_case),
        "__COORDS__": _safe_html(case["coords"]),
        "__OVERLAY_CLASS__": overlay_class,
        "__OVERLAY_HTML__": overlay_html,
        "__TOOL_ICON__": _safe_html(tool["icon"]),
        "__TOOL_NAME__": _safe_html(selected_tool),
        "__MEASURES__": _safe_html(tool["measures"]),
        "__REGION__": _safe_html(case["region"]),
        "__TYPE__": _safe_html(case["type"]),
        "__THEME__": _safe_html(case["main_theme"]),
        "__VISUAL__": _safe_html(tool["visual"]),
        "__OBSERVED__": _safe_html(tool["observed"]),
        "__INTERPRETATION__": _safe_html(tool["interpretation"]),
        "__PROCESS__": _safe_html(tool["process"]).replace(" ->", " &nbsp;&rarr;&nbsp; "),
        "__TOOL_GRID__": tool_grid,
        "__VISIBLE_LAYER_CHIPS__": visible_layer_chips
    }
    for k, v in replacements.items():
        explorer_html = explorer_html.replace(k, v)

    components.html(explorer_html, height=675, scrolling=False)

    st.caption("The text summarizes observation logic from the review-paper case studies.")

    r1, r2, r3 = st.columns(3)
    r1.metric("Case", selected_case)
    r2.metric("Primary layer", selected_tool)
    r3.metric("Visible layers", str(len(visual_layers)))

    with st.expander("Build the multi-sensor synthesis", expanded=False):
        selected_layers = st.multiselect(
            "Combine observation layers",
            tool_order,
            default=[selected_tool, "InSAR Velocity", "Satellite Altimetry"] if selected_tool not in ["InSAR Velocity", "Satellite Altimetry"] else [selected_tool, "GRACE / GRACE-FO"],
            key="system_layer_multiselect"
        )
        if selected_layers:
            cards_html = "".join([
                f"""
                <div class="evidence-layer-card">
                  <div class="evidence-layer-title">{case['tools'][layer]['icon']} {layer}</div>
                  <div class="evidence-layer-label">Measures</div>
                  <div class="evidence-layer-text">{case['tools'][layer]['measures']}</div>
                  <div class="evidence-layer-label">Observed</div>
                  <div class="evidence-layer-text">{case['tools'][layer]['observed']}</div>
                </div>
                """
                for layer in selected_layers
            ])
            evidence_builder_html = textwrap.dedent(f"""
            <div class="evidence-builder-wrap">
              <style>
                html, body {{
                  margin: 0;
                  padding: 0;
                  background: transparent;
                  overflow: hidden;
                  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                  color: rgba(245,250,255,.94);
                }}
                .evidence-builder-wrap {{
                  width: 100%;
                  display: block;
                  clear: both;
                  box-sizing: border-box;
                  padding: 0 0 2px 0;
                }}
                .system-note-card {{
                  padding: 0 0 10px 0;
                  background: transparent;
                  border: none;
                  color: rgba(245,250,255,.92);
                  line-height: 1.45;
                  font-size: 14px;
                }}
                .system-note-card b {{
                  font-size: 15px;
                  color: rgba(248,251,255,.98);
                }}
                .evidence-grid-fixed {{
                  display: grid;
                  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                  gap: 12px;
                  margin-top: 4px;
                  margin-bottom: 14px;
                }}
                .evidence-layer-card {{
                  padding: 14px 15px;
                  border-radius: 18px;
                  border: 1px solid rgba(78,163,241,.22);
                  background: rgba(78,163,241,.065);
                  min-height: 154px;
                  box-sizing: border-box;
                }}
                .evidence-layer-title {{
                  font-weight: 800;
                  font-size: 15px;
                  margin-bottom: 12px;
                  color: rgba(248,251,255,.98);
                }}
                .evidence-layer-label {{
                  font-size: 12px;
                  opacity: .68;
                  font-weight: 700;
                  margin-top: 8px;
                }}
                .evidence-layer-text {{
                  font-size: 13px;
                  margin-top: 3px;
                  line-height: 1.4;
                }}
                .synthesis-fixed {{
                  clear: both;
                  margin-top: 14px;
                  padding: 14px 16px;
                  border-radius: 16px;
                  background: rgba(34,197,94,.16);
                  border: 1px solid rgba(74,222,128,.26);
                  color: #49e782;
                  font-size: 15px;
                  line-height: 1.45;
                  font-weight: 650;
                  box-sizing: border-box;
                }}
              </style>
              <div class="system-note-card">
                <b>Evidence Builder</b><br>
                Each selected sensor contributes a different kind of evidence. The goal is not to make the map busier, but to show how a scientific conclusion is assembled.
              </div>
              <div class="evidence-grid-fixed">
                {cards_html}
              </div>
              <div class="synthesis-fixed">
                Synthesis: For <b>{selected_case}</b>, these layers combine different evidence dimensions and support the theme: <b>{case['main_theme']}</b>.
              </div>
            </div>
            """)
            evidence_rows = max(1, int(np.ceil(len(selected_layers) / 2)))
            components.html(evidence_builder_html, height=126 + evidence_rows * 172, scrolling=False)
        else:
            st.info("Select one or more layers to build a scientific synthesis.")

    with st.expander("Physical-process context", expanded=False):
        processes = {
            "Ocean Forcing": "Warm Circumpolar Deep Water can reach the continental shelf and increase basal melting below ice shelves.",
            "Ice Shelf Buttressing": "Floating ice shelves slow inland ice flow by providing back stress; thinning or collapse reduces this support.",
            "Grounding Line Retreat": "The grounding line marks the transition from grounded ice to floating ice; retreat can increase ice discharge.",
            "MISI": "Marine Ice Sheet Instability can occur when retreat on a retrograde bed exposes thicker ice and causes further retreat.",
            "MICI": "Marine Ice Cliff Instability is a proposed rapid-collapse mechanism involving hydrofracturing and cliff failure.",
            "Basal Hydrology": "Subglacial water can reduce basal resistance and affect ice flow speed.",
            "Solid Earth Feedback": "Bedrock uplift and sea-level fingerprints can either amplify or slow ice-sheet retreat."
        }
        selected_process = st.selectbox("Select a process", list(processes.keys()), key="system_process_context")
        st.info(processes[selected_process])


elif module == "AI Visualizer":
    st.markdown('''
    <style>
      .block-container { padding-top: 1.42rem !important; }

      /* Compact one-line title row */
      .visualizer-intro {
        margin: .32rem 0 .35rem 0;
        display: flex;
        align-items: center;
        gap: 18px;
        flex-wrap: nowrap;
      }
      .visualizer-intro h1 {
        margin: 0;
        color: #f8fbff;
        font-size: 2.25rem;
        line-height: 1.18;
        font-weight: 850;
        letter-spacing: 0;
        white-space: nowrap;
      }
      .visualizer-intro p {
        margin: 0;
        color: rgba(188, 221, 239, .75);
        font-size: .88rem;
        line-height: 1.15;
        max-width: 980px;
      }

      /* Compress the control row: selectbox + radio */
      div[data-testid="stSelectbox"], div[data-testid="stRadio"] {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
      }
      div[data-testid="stSelectbox"] label,
      div[data-testid="stRadio"] label {
        font-size: .78rem !important;
        font-weight: 760 !important;
        margin-bottom: .05rem !important;
        padding-bottom: 0 !important;
      }
      div[data-testid="stSelectbox"] > div,
      div[data-testid="stRadio"] > div {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
      }
      div[data-baseweb="select"] > div {
        min-height: 34px !important;
        height: 34px !important;
      }
      div[data-baseweb="select"] div {
        line-height: 1.05 !important;
      }
      div[data-testid="stRadio"] [role="radiogroup"] {
        gap: .75rem !important;
        min-height: 34px !important;
        align-items: center !important;
      }
      div[data-testid="stRadio"] [role="radio"] {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
      }

      /* Keep the Scientific Story Engine close to controls without hiding it under Streamlit's top bar. */
      div[data-testid="stIFrame"] {
        margin-top: .35rem !important;
        scroll-margin-top: 96px !important;
      }

      /* Do not let the AI Visualizer radio compression affect the sidebar navigation. */
      [data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] {
        gap: .46rem !important;
        min-height: auto !important;
        align-items: stretch !important;
      }
      [data-testid="stSidebar"] div[data-testid="stRadio"] [role="radio"] {
        padding-top: .12rem !important;
        padding-bottom: .12rem !important;
        min-height: 1.7rem !important;
      }
      [data-testid="stSidebar"] div[data-testid="stRadio"] label,
      [data-testid="stSidebar"] div[data-testid="stRadio"] p {
        white-space: nowrap !important;
        line-height: 1.25 !important;
      }
    </style>
    <div class="visualizer-intro">
      <h1>&#127912; AI Visualizer</h1>
      <p>Transform the review paper into an interactive scientific story: mechanisms grow step by step, evidence nodes light up, and each pathway becomes slide-ready.</p>
    </div>
    ''', unsafe_allow_html=True)

    story_bank = {
        "Ice Sheet Stability": {
            "subtitle": "From ocean heat to ice-sheet retreat",
            "opening": "Antarctic stability is not controlled by one factor. It emerges from ocean forcing, ice-shelf buttressing, grounding-line geometry, and feedbacks across the Earth system.",
            "modes": {
                "Past": [
                    {"id": "Past Warm Periods", "type": "Paleo evidence", "x": 18, "y": 28, "note": "Pliocene and Last Interglacial evidence shows that the AIS can respond strongly to warmer climates.", "evidence": "Ice cores - marine sediments - sea-level constraints"},
                    {"id": "Marine-based Ice", "type": "Boundary condition", "x": 39, "y": 42, "note": "Ice grounded below sea level is especially sensitive to ocean and grounding-line feedbacks.", "evidence": "Subglacial basins - continental shelf records"},
                    {"id": "Retreat Episodes", "type": "Ice response", "x": 62, "y": 35, "note": "Past retreat helps test whether models can reproduce rapid ice-sheet change.", "evidence": "Grounding-zone wedges - iceberg plow marks"},
                    {"id": "Model Constraints", "type": "Research use", "x": 80, "y": 55, "note": "Paleo records constrain future projections by showing what the ice sheet has done before.", "evidence": "Paleo-data model comparison"}
                ],
                "Present": [
                    {"id": "Warm Ocean Access", "type": "Ocean", "x": 16, "y": 46, "note": "Warm Circumpolar Deep Water can reach vulnerable ice-shelf cavities.", "evidence": "Ocean observations - shelf-break bathymetry"},
                    {"id": "Basal Melting", "type": "Ice shelf", "x": 34, "y": 32, "note": "Ocean heat melts the underside of floating ice shelves.", "evidence": "Altimetry - ocean moorings - melt-rate estimates"},
                    {"id": "Reduced Buttressing", "type": "Ice dynamics", "x": 52, "y": 42, "note": "Thinner or damaged shelves provide less back stress to grounded ice.", "evidence": "Ice velocity - shelf-thickness change"},
                    {"id": "Grounding Line Retreat", "type": "Ice dynamics", "x": 69, "y": 31, "note": "The grounding line controls how much grounded ice can discharge into the ocean.", "evidence": "InSAR - altimetry - tidal flexure"},
                    {"id": "Faster Ice Flow", "type": "Observation", "x": 84, "y": 48, "note": "Velocity observations reveal acceleration of outlet glaciers in key sectors.", "evidence": "InSAR velocity fields"}
                ],
                "Future": [
                    {"id": "Continued Warming", "type": "Forcing", "x": 15, "y": 32, "note": "Future atmosphere and ocean forcing determine the pressure placed on the AIS.", "evidence": "Climate scenarios"},
                    {"id": "Instability Thresholds", "type": "Uncertainty", "x": 35, "y": 48, "note": "MISI and possible MICI-like behavior could amplify retreat once thresholds are crossed.", "evidence": "Ice-sheet models - process studies"},
                    {"id": "Coupled Feedbacks", "type": "Earth system", "x": 57, "y": 34, "note": "Ocean, ice, atmosphere, and solid Earth feedbacks interact across time scales.", "evidence": "Coupled ice-ocean-solid Earth models"},
                    {"id": "Sea-level Risk", "type": "Impact", "x": 78, "y": 50, "note": "Antarctica remains a major uncertainty in future sea-level projections.", "evidence": "Projection ensembles - uncertainty quantification"}
                ]
            }
        },
        "Ocean-driven Ice Loss": {
            "subtitle": "How ocean heat becomes ice discharge",
            "opening": "Warm water reaches the ice shelf cavity, melts ice from below, weakens buttressing, and allows grounded ice to accelerate.",
            "modes": {
                "Past": [
                    {"id": "Shelf Troughs", "type": "Landscape memory", "x": 18, "y": 50, "note": "Repeated glacial erosion carved troughs that can route warm water toward the margin.", "evidence": "Bathymetry - marine geomorphology"},
                    {"id": "Past Ocean States", "type": "Paleo ocean", "x": 39, "y": 35, "note": "Marine records reconstruct past ocean warmth and ice-margin retreat.", "evidence": "Marine sediment cores"},
                    {"id": "Retreat History", "type": "Paleo ice", "x": 63, "y": 43, "note": "Past retreat episodes provide analogs for modern ocean-forced change.", "evidence": "Continental shelf archives"},
                    {"id": "Sensitivity Test", "type": "Model constraint", "x": 81, "y": 31, "note": "Models are tested against past retreat and sea-level evidence.", "evidence": "Paleo-calibrated simulations"}
                ],
                "Present": [
                    {"id": "CDW Intrusion", "type": "Ocean", "x": 14, "y": 45, "note": "Circumpolar Deep Water brings heat onto the continental shelf.", "evidence": "Ocean profiles - shelf-break circulation"},
                    {"id": "Ice-shelf Cavity", "type": "Hidden interface", "x": 33, "y": 31, "note": "The most important melting often occurs beneath floating ice shelves, out of direct view.", "evidence": "Radar - ocean access drilling - models"},
                    {"id": "Basal Melt", "type": "Process", "x": 50, "y": 45, "note": "Heat and salt exchange at the ice-ocean boundary melts ice from below.", "evidence": "Melt-rate estimates - ocean modeling"},
                    {"id": "Shelf Thinning", "type": "Observation", "x": 67, "y": 31, "note": "Altimetry detects surface lowering that indicates thinning.", "evidence": "Satellite altimetry"},
                    {"id": "Ice Discharge", "type": "Impact", "x": 84, "y": 48, "note": "Once buttressing weakens, grounded ice can flow faster into the ocean.", "evidence": "InSAR velocity - mass balance"}
                ],
                "Future": [
                    {"id": "Stronger Heat Flux", "type": "Forcing", "x": 15, "y": 36, "note": "Changes in winds, eddies, tides, and circulation may alter heat delivery to shelves.", "evidence": "High-resolution ocean models"},
                    {"id": "Freshwater Feedback", "type": "Feedback", "x": 36, "y": 52, "note": "Meltwater can increase stratification and trap subsurface heat.", "evidence": "Freshwater-ocean coupling"},
                    {"id": "More Basal Melt", "type": "Amplification", "x": 58, "y": 34, "note": "A warmer, more stratified shelf ocean can sustain higher basal melt rates.", "evidence": "Ice-ocean model experiments"},
                    {"id": "Projection Spread", "type": "Uncertainty", "x": 80, "y": 48, "note": "Ocean forcing remains one of the central uncertainties in future AIS mass loss.", "evidence": "Model intercomparison"}
                ]
            }
        },
        "Hydrofracture & Ice Cliff Risk": {
            "subtitle": "Atmospheric melt, shelf collapse, and high-end risk",
            "opening": "Surface meltwater can pond on ice shelves, deepen crevasses through hydrofracture, and reduce shelf integrity.",
            "modes": {
                "Past": [
                    {"id": "Warm Intervals", "type": "Climate context", "x": 18, "y": 34, "note": "Past warm periods help test whether surface-melt processes can explain high sea levels.", "evidence": "Last Interglacial - Pliocene"},
                    {"id": "Ice-shelf Absence", "type": "Paleo state", "x": 42, "y": 50, "note": "Some records imply reduced ice-shelf cover during warmer conditions.", "evidence": "Marine sediment evidence"},
                    {"id": "Rapid Retreat Clues", "type": "Paleo evidence", "x": 65, "y": 36, "note": "Geomorphic evidence can suggest rapid retreat or calving behavior.", "evidence": "Iceberg-keel plow marks"},
                    {"id": "Model Debate", "type": "Uncertainty", "x": 82, "y": 53, "note": "MICI is influential but still debated and requires more validation.", "evidence": "Ice-sheet model comparisons"}
                ],
                "Present": [
                    {"id": "Surface Melt", "type": "Atmosphere", "x": 16, "y": 35, "note": "Surface melt is most prominent around the Antarctic Peninsula and shelf margins.", "evidence": "Satellite melt detection"},
                    {"id": "Melt Ponds", "type": "Hydrology", "x": 35, "y": 50, "note": "Ponded water adds weight and can fill crevasses.", "evidence": "Optical imagery - surface hydrology mapping"},
                    {"id": "Hydrofracturing", "type": "Fracture", "x": 54, "y": 34, "note": "Water pressure can drive cracks deeper into the shelf.", "evidence": "Larsen-style collapse interpretation"},
                    {"id": "Shelf Collapse", "type": "Instability", "x": 72, "y": 48, "note": "Shelf breakup reduces buttressing and can accelerate tributary glaciers.", "evidence": "Larsen B observations"},
                    {"id": "Flow Acceleration", "type": "Observation", "x": 86, "y": 32, "note": "Post-collapse velocity change shows the mechanical importance of ice shelves.", "evidence": "InSAR velocity"}
                ],
                "Future": [
                    {"id": "More Surface Melt", "type": "Forcing", "x": 16, "y": 45, "note": "Atmospheric warming may expand meltwater systems on ice shelves.", "evidence": "Climate projections"},
                    {"id": "Shelf Vulnerability", "type": "Risk", "x": 37, "y": 31, "note": "Vulnerability depends on firn capacity, fracture fields, shelf geometry, and stress state.", "evidence": "Surface hydrology + fracture models"},
                    {"id": "Possible MICI", "type": "Debated mechanism", "x": 60, "y": 49, "note": "Marine Ice Cliff Instability could raise high-end sea-level outcomes, but evidence remains limited.", "evidence": "Model parameterization - field analogs"},
                    {"id": "High-end Sea Level", "type": "Impact", "x": 82, "y": 34, "note": "This pathway matters most for low-probability, high-impact projection tails.", "evidence": "Scenario ensembles"}
                ]
            }
        },
        "Solid Earth Feedbacks": {
            "subtitle": "The bed below the ice is part of the story",
            "opening": "Bed topography, geothermal heat, basal water, and glacial isostatic adjustment shape how the ice sheet responds.",
            "modes": {
                "Past": [
                    {"id": "Tectonic Template", "type": "Deep control", "x": 16, "y": 42, "note": "Rifting, basins, and mountains created the bed geometry on which ice evolves.", "evidence": "Geophysics - bed maps"},
                    {"id": "Dynamic Topography", "type": "Long-term change", "x": 38, "y": 30, "note": "Mantle-driven uplift or subsidence can alter vulnerability over million-year scales.", "evidence": "Mantle circulation models"},
                    {"id": "Past Loading", "type": "GIA memory", "x": 61, "y": 47, "note": "The solid Earth continues to respond to past ice loading changes.", "evidence": "Relative sea level - GPS"},
                    {"id": "Paleo Boundary", "type": "Model input", "x": 81, "y": 35, "note": "Past topography and sea level affect reconstructions of AIS history.", "evidence": "Ice-sheet + GIA models"}
                ],
                "Present": [
                    {"id": "Bed Topography", "type": "Boundary", "x": 16, "y": 34, "note": "Retrograde beds and subglacial basins affect grounding-line stability.", "evidence": "Radar - BEDMAP-style products"},
                    {"id": "Geothermal Heat", "type": "Basal energy", "x": 36, "y": 51, "note": "Heat from below can produce basal meltwater and influence sliding.", "evidence": "Magnetic/seismic heat-flux estimates"},
                    {"id": "Subglacial Hydrology", "type": "Basal water", "x": 58, "y": 34, "note": "Water beneath the ice can lubricate the bed and connect interior ice to shelf cavities.", "evidence": "Radar - altimetry lake drainage"},
                    {"id": "GIA Correction", "type": "Observation need", "x": 80, "y": 49, "note": "Gravity-based mass estimates require correction for solid-Earth motion.", "evidence": "GRACE - GPS/GNSS"}
                ],
                "Future": [
                    {"id": "Bedrock Uplift", "type": "Feedback", "x": 17, "y": 46, "note": "Ice loss can trigger bedrock uplift and local sea-level fall near grounding lines.", "evidence": "GIA theory - GPS"},
                    {"id": "Relative Sea Level", "type": "Stabilizer", "x": 39, "y": 31, "note": "Local sea-level fall can slow retreat in some settings.", "evidence": "Coupled sea-level models"},
                    {"id": "3D Earth Structure", "type": "Uncertainty", "x": 61, "y": 49, "note": "Viscosity varies strongly across Antarctica, affecting feedback timing.", "evidence": "Seismology - geodesy"},
                    {"id": "Coupled Projection", "type": "Model frontier", "x": 82, "y": 35, "note": "Future projections need ice, ocean, atmosphere, and solid Earth coupling.", "evidence": "Coupled model development"}
                ]
            }
        }
    }

    story_col, lens_col = st.columns([0.58, 0.42], gap="small")
    with story_col:
        story_topic = st.selectbox("Choose story", list(story_bank.keys()), key="visualizer_story_topic")
    with lens_col:
        time_mode = st.radio("Lens", ["Past", "Present", "Future"], horizontal=True, key="visualizer_time_lens")

    current_story = story_bank[story_topic]
    story_payload = {
        "topic": story_topic,
        "subtitle": current_story["subtitle"],
        "opening": current_story["opening"],
        "mode": time_mode,
        "nodes": current_story["modes"][time_mode]
    }

    story_html = r'''
    <div id="ai-story-root">
      <style>
        #ai-story-root { width: 100%; height: 690px; position: relative; overflow: hidden; border-radius: 32px; isolation:isolate; color: #eef8ff; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: radial-gradient(circle at 18% 18%, rgba(78,163,241,.26), transparent 28%), radial-gradient(circle at 78% 72%, rgba(149,117,205,.22), transparent 30%), radial-gradient(circle at 50% 52%, rgba(185,242,255,.10), transparent 25%), linear-gradient(135deg, #030712 0%, #07111f 47%, #020617 100%); background-size:135% 135%, 150% 150%, 120% 120%, 100% 100%; box-shadow: inset 0 0 105px rgba(78,163,241,.14), 0 26px 82px rgba(0,0,0,.34); animation:aiNebulaDrift 24s ease-in-out infinite; }
        #ai-story-root * { box-sizing: border-box; }
        #ai-story-root::before,
        #ai-story-root::after { content:""; position:absolute; inset:-18%; pointer-events:none; z-index:1; }
        #ai-story-root::before { background:linear-gradient(115deg, transparent 8%, rgba(255,255,255,.055) 37%, rgba(126,220,255,.10) 48%, transparent 62%); mix-blend-mode:screen; opacity:.70; animation:aiGlassDrift 12s ease-in-out infinite; }
        #ai-story-root::after { background:radial-gradient(ellipse at 52% 52%, transparent 34%, rgba(2,6,23,.34) 84%); z-index:1; }
        .ai-v-star { position:absolute; width:2px; height:2px; border-radius:50%; background:rgba(255,255,255,.72); box-shadow:0 0 10px rgba(255,255,255,.65); animation:aiTwinkle 3.8s infinite ease-in-out alternate; }
        @keyframes aiTwinkle { from { opacity:.22; transform:scale(.7); } to { opacity:.95; transform:scale(1.35); } }
        @keyframes aiNebulaDrift { 0%,100% { background-position:0% 0%, 100% 92%, 50% 50%, 0 0; } 50% { background-position:8% 6%, 91% 80%, 44% 56%, 0 0; } }
        @keyframes aiGlassDrift { 0%,100% { transform:translateX(-8%) rotate(-3deg); opacity:.52; } 50% { transform:translateX(8%) rotate(3deg); opacity:.86; } }
        @keyframes aiPanelIn { from { opacity:0; transform:translateY(12px) scale(.985); } to { opacity:1; transform:translateY(0) scale(1); } }
        @keyframes aiStageFloat { 0%,100% { transform:translate3d(0,0,0); } 50% { transform:translate3d(0,-5px,0); } }
        .ai-story-title { position:absolute; left:24px; top:62px; width: 430px; z-index:10; overflow:hidden; padding:18px 20px; border-radius:24px; border:1px solid rgba(210,238,255,.22); background:radial-gradient(circle at 14% 0%, rgba(255,255,255,.12), transparent 34%), linear-gradient(180deg, rgba(14,27,49,.66), rgba(4,12,25,.42)); backdrop-filter: blur(22px) saturate(1.32); box-shadow:inset 0 1px 0 rgba(255,255,255,.13), 0 18px 48px rgba(0,0,0,.18); animation:aiPanelIn .38s cubic-bezier(.2,.8,.2,1) both; }
        .ai-story-title::before { content:""; position:absolute; inset:-80% -35%; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.11) 38%, rgba(126,220,255,.18) 48%, transparent 66%); transform:translateX(-28%) rotate(10deg); opacity:.62; pointer-events:none; }
        .ai-story-title .kicker { color:#8dd8ff; font-size:12px; letter-spacing:1.2px; text-transform:uppercase; font-weight:850; }
        .ai-story-title h2 { margin:7px 0 5px 0; font-size:28px; letter-spacing:0; color:#fff; }
        .ai-story-title p { margin:0; color:rgba(231,245,255,.75); font-size:13px; line-height:1.42; }
        .ai-story-stage { position:absolute; left:24px; top:225px; width: calc(100% - 372px); height: 438px; z-index:5; border-radius:28px; border:1px solid rgba(210,238,255,.20); overflow:hidden; background: radial-gradient(ellipse at 46% 50%, rgba(223,249,255,.12), transparent 55%), linear-gradient(180deg, rgba(8,19,36,.52), rgba(2,6,23,.26)); box-shadow:inset 0 1px 0 rgba(255,255,255,.10), 0 20px 56px rgba(0,0,0,.22); animation:aiPanelIn .44s cubic-bezier(.2,.8,.2,1) both; }
        .ai-story-stage::before { content:""; position:absolute; inset:-60% -30%; z-index:3; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.08) 38%, rgba(126,220,255,.12) 48%, transparent 66%); opacity:.54; transform:translateX(-24%) rotate(10deg); pointer-events:none; }
        .ai-stage-bg { position:absolute; inset:0; background: radial-gradient(ellipse at 30% 66%, rgba(248,252,255,.78), rgba(180,220,235,.34) 25%, transparent 52%), radial-gradient(ellipse at 75% 70%, rgba(55,160,190,.20), transparent 42%), linear-gradient(180deg, rgba(45,125,170,.06), rgba(0,0,0,.05)); opacity:.78; animation:aiStageFloat 7s ease-in-out infinite; }
        .ai-stage-bg::before { content:""; position:absolute; left:-8%; right:-8%; bottom:58px; height:128px; background:linear-gradient(180deg, rgba(255,255,255,.72), rgba(185,230,242,.44)); clip-path: polygon(0% 62%, 10% 47%, 21% 54%, 32% 30%, 45% 48%, 57% 28%, 70% 46%, 83% 25%, 100% 52%, 100% 100%, 0% 100%); filter: drop-shadow(0 0 20px rgba(170,240,255,.20)); }
        .ai-stage-bg::after { content:""; position:absolute; left:0; right:0; bottom:0; height:104px; background:linear-gradient(180deg, rgba(46,160,205,.35), rgba(4,30,55,.80)); }
        #ai-story-svg { position:absolute; inset:0; width:100%; height:100%; z-index:4; }
        .ai-controls { position:absolute; left:22px; top:18px; z-index:12; display:flex; gap:10px; align-items:center; }
        .ai-controls button { position:relative; overflow:hidden; border:1px solid rgba(180,230,255,.34); border-radius:999px; padding:9px 14px; background:linear-gradient(180deg, rgba(17,35,62,.72), rgba(2,6,23,.54)); color:#eaf8ff; font-weight:850; cursor:pointer; box-shadow:0 10px 24px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.12); backdrop-filter:blur(14px); transition:transform .16s ease, border-color .16s ease, background .16s ease; }
        .ai-controls button::before { content:""; position:absolute; inset:-70% -35%; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.14) 38%, rgba(126,220,255,.22) 48%, transparent 66%); transform:translateX(-130%) rotate(10deg); opacity:0; pointer-events:none; }
        .ai-controls button:hover { transform:translateY(-1px); background:rgba(56,189,248,.20); border-color:rgba(186,230,253,.72); }
        .ai-controls button:hover::before { animation:aiButtonSheen .75s cubic-bezier(.2,.8,.2,1); }
        @keyframes aiButtonSheen { from { transform:translateX(-130%) rotate(10deg); opacity:0; } 28% { opacity:1; } to { transform:translateX(130%) rotate(10deg); opacity:0; } }
        .ai-progress { width:160px; height:7px; border-radius:999px; background:rgba(255,255,255,.12); overflow:hidden; border:1px solid rgba(255,255,255,.12); }
        .ai-progress span { display:block; height:100%; width:0%; background:linear-gradient(90deg, #6edcff, #d8f7ff); border-radius:999px; transition:width .3s ease; }
        .ai-side-panel { position:absolute; right:24px; top:62px; width:320px; height:601px; z-index:10; overflow:hidden; padding:20px; border-radius:28px; border:1px solid rgba(210,238,255,.30); background:radial-gradient(circle at 12% 0%, rgba(255,255,255,.12), transparent 34%), linear-gradient(180deg, rgba(12,25,46,.90), rgba(5,13,27,.70)); backdrop-filter: blur(24px) saturate(1.38); box-shadow:0 24px 74px rgba(0,0,0,.40), inset 0 1px 0 rgba(255,255,255,.14), inset 0 -1px 0 rgba(126,220,255,.08); animation:aiPanelIn .46s cubic-bezier(.2,.8,.2,1) both; }
        .ai-side-panel::before { content:""; position:absolute; inset:-70% -35%; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.11) 38%, rgba(126,220,255,.18) 48%, transparent 66%); transform:translateX(-30%) rotate(10deg); opacity:.40; pointer-events:none; }
        .ai-panel-badge { display:inline-flex; padding:7px 11px; border-radius:999px; color:#bfe6ff; background:rgba(78,163,241,.14); border:1px solid rgba(142,207,255,.25); font-size:12px; font-weight:850; }
        .ai-side-panel h3 { margin:15px 0 9px 0; font-size:24px; line-height:1.15; color:#fff; }
        .ai-side-panel .muted { color:rgba(235,248,255,.72); font-size:13px; line-height:1.45; }
        .ai-label { margin-top:16px; color:#8ccfff; font-size:11px; text-transform:uppercase; letter-spacing:1px; font-weight:850; }
        .ai-value { margin-top:6px; color:rgba(239,248,255,.88); line-height:1.45; font-size:13px; }
        .ai-mini-grid { display:grid; grid-template-columns:1fr 1fr; gap:9px; margin-top:16px; }
        .ai-mini-card { padding:10px; min-height:70px; border-radius:15px; border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.055); box-shadow:inset 0 1px 0 rgba(255,255,255,.06); }
        .ai-mini-card b { color:#fff; font-size:13px; }
        .ai-mini-card div { margin-top:5px; color:rgba(230,245,255,.70); font-size:12px; line-height:1.3; }
        .ai-slide-box { margin-top:16px; padding:13px; border-radius:17px; background:rgba(34,197,94,.09); border:1px solid rgba(74,222,128,.22); color:rgba(235,255,242,.88); font-size:13px; line-height:1.45; }
        .ai-node { cursor:pointer; opacity:0; transition:opacity .45s ease; }
        .ai-node .halo, .ai-node .core { transform-box:fill-box; transform-origin:center; }
        .ai-node .halo { fill:rgba(150,225,255,.12); stroke:rgba(160,230,255,.35); stroke-width:1.2; animation:aiBreath 2.8s ease-in-out infinite; }
        .ai-node .core { stroke:rgba(255,255,255,.82); stroke-width:1.6; filter:drop-shadow(0 0 18px rgba(126,220,255,.58)); }
        .ai-node text { pointer-events:none; text-anchor:middle; font-weight:850; fill:#f8fdff; paint-order:stroke; stroke:rgba(2,6,23,.92); stroke-width:4px; stroke-linejoin:round; }
        .ai-node.visible { opacity:1; }
        .ai-node.visible .core { animation:aiCorePop .38s cubic-bezier(.2,.8,.2,1) both; }
        .ai-node.active .halo { fill:rgba(255,255,255,.18); stroke:rgba(255,255,255,.82); stroke-width:2.4; }
        .ai-node.active .core { filter:drop-shadow(0 0 32px rgba(255,255,255,.95)); }
        .ai-link { opacity:0; stroke:rgba(160,225,255,.65); stroke-width:2.6; stroke-linecap:round; stroke-dasharray:8 9; filter:drop-shadow(0 0 8px rgba(120,220,255,.35)); transition:opacity .45s ease; }
        .ai-link.visible { opacity:.95; animation:dashMove 1.4s linear infinite; }
        @keyframes dashMove { to { stroke-dashoffset:-34; } }
        @keyframes aiBreath { 0%,100% { transform:scale(1); opacity:.70; } 50% { transform:scale(1.18); opacity:1; } }
        @keyframes aiCorePop { from { transform:scale(.72); opacity:.55; } to { transform:scale(1); opacity:1; } }
        .ai-caption { position:absolute; left:50%; transform:translateX(-50%); bottom:88px; z-index:8; width:min(640px, 72%); padding:12px 15px; border-radius:18px; border:1px solid rgba(255,255,255,.16); background:rgba(2,6,23,.52); box-shadow:0 14px 34px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.08); color:rgba(239,248,255,.84); font-size:13px; line-height:1.45; text-align:center; backdrop-filter:blur(14px) saturate(1.25); }
      </style>
      <div class="ai-story-title"><div class="kicker">Scientific Story Engine - __MODE__ lens</div><h2>__TOPIC__</h2><p><b>__SUBTITLE__</b><br>__OPENING__</p></div>
      <div class="ai-story-stage"><div class="ai-stage-bg"></div><svg id="ai-story-svg" viewBox="0 0 900 470" preserveAspectRatio="xMidYMid meet"></svg><div class="ai-caption" id="ai-caption">Click Begin Story to reveal the mechanism step by step, or click any glowing node to inspect its evidence card.</div><div class="ai-controls"><button id="ai-play">Begin Story</button><button id="ai-reset">Reset</button><div class="ai-progress"><span id="ai-progress-bar"></span></div></div></div>
      <div class="ai-side-panel" id="ai-side-panel"></div>
    </div>
    <script>
    (function(){
      const payload = __PAYLOAD__; const root = document.getElementById('ai-story-root'); const svg = document.getElementById('ai-story-svg'); const panel = document.getElementById('ai-side-panel'); const caption = document.getElementById('ai-caption'); const bar = document.getElementById('ai-progress-bar'); const NS = 'http://www.w3.org/2000/svg'; let step = -1; let timer = null;
      const typeColors = {'Ocean':'#4EA3F1','Ice shelf':'#B8F2FF','Ice Dynamics':'#7BDFF2','Ice dynamics':'#7BDFF2','Observation':'#9575CD','Atmosphere':'#A7C7E7','Hydrology':'#58D5FF','Fracture':'#FF8A65','Instability':'#FFB067','Debated mechanism':'#FFB067','Impact':'#CDB4DB','Forcing':'#F6C85F','Uncertainty':'#FFD166','Earth system':'#9CCC65','Boundary':'#C19A6B','Solid Earth':'#C19A6B','Basal water':'#79E0EE','Basal energy':'#F6C85F','Observation need':'#9575CD','Feedback':'#9CCC65','Stabilizer':'#9CCC65','Model frontier':'#CDB4DB','Paleo evidence':'#F6C85F','Paleo ice':'#F6C85F','Paleo ocean':'#4EA3F1','Research use':'#CDB4DB','Model constraint':'#CDB4DB','Landscape memory':'#C19A6B','Boundary condition':'#C19A6B','Ice response':'#7BDFF2','Deep control':'#C19A6B','Long-term change':'#9CCC65','GIA memory':'#9CCC65','Model input':'#CDB4DB','Amplification':'#FFB067','Risk':'#FFB067','Climate context':'#A7C7E7','Paleo state':'#F6C85F'};
      for (let i=0; i<90; i++) { const s = document.createElement('div'); s.className='ai-v-star'; s.style.left = Math.random()*100 + '%'; s.style.top = Math.random()*100 + '%'; s.style.animationDelay = Math.random()*4 + 's'; root.appendChild(s); }
      function el(name, attrs={}) { const e=document.createElementNS(NS,name); Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v)); return e; }
      function esc(t){ return String(t ?? '').replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[m])); }
      function wrapText(g, text, x, y, width, fs) { const words = String(text).split(/\s+/); let line='', lines=[]; words.forEach(w => { const test = line ? line + ' ' + w : w; if (test.length > width && line) { lines.push(line); line=w; } else line=test; }); if (line) lines.push(line); const t = el('text', {x:x, y:y, 'font-size':fs}); lines.slice(0,2).forEach((ln,i)=>{ const sp=el('tspan', {x:x, dy:i? '1.15em':'0'}); sp.textContent=ln; t.appendChild(sp); }); g.appendChild(t); }
      function nodeXY(n){ return {x:n.x*9, y:n.y*4.7}; }
      const defs = el('defs'); defs.innerHTML = `<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="rgba(190,240,255,.85)" /></marker>`; svg.appendChild(defs);
      const linkLayer = el('g'); const nodeLayer = el('g'); svg.appendChild(linkLayer); svg.appendChild(nodeLayer); const links = [];
      for(let i=0; i<payload.nodes.length-1; i++) { const a=nodeXY(payload.nodes[i]), b=nodeXY(payload.nodes[i+1]); const path = el('path', {class:'ai-link', d:`M ${a.x} ${a.y} C ${(a.x+b.x)/2} ${a.y-70}, ${(a.x+b.x)/2} ${b.y+70}, ${b.x} ${b.y}`, markerEnd:'url(#arrow)'}); path.dataset.index=i; linkLayer.appendChild(path); links.push(path); }
      const nodeEls = payload.nodes.map((n,i)=>{ const p=nodeXY(n), color=typeColors[n.type] || '#9EDBFF'; const g=el('g', {class:'ai-node', transform:`translate(${p.x},${p.y})`}); g.dataset.index=i; g.appendChild(el('circle', {class:'halo', r:50})); g.appendChild(el('circle', {class:'core', r:28, fill:color, 'fill-opacity':.88})); wrapText(g, n.id, 0, 5, 18, 13); g.addEventListener('click', ()=>revealTo(i)); nodeLayer.appendChild(g); return g; });
      function panelHtml(n, idx){ const chain = payload.nodes.map(x=>x.id).join(' \u2192 '); return `<span class="ai-panel-badge">${esc(payload.mode)} - ${esc(n.type)}</span><h3>${esc(n.id)}</h3><div class="muted">Node ${idx+1} of ${payload.nodes.length} in <b>${esc(payload.topic)}</b>.</div><div class="ai-label">Scientific meaning</div><div class="ai-value">${esc(n.note)}</div><div class="ai-label">Evidence layer</div><div class="ai-value">${esc(n.evidence)}</div><div class="ai-mini-grid"><div class="ai-mini-card"><b>Use in slides</b><div>Turn this node into one visual beat in a talk.</div></div><div class="ai-mini-card"><b>Reading logic</b><div>Connect mechanism, observation, and uncertainty.</div></div></div><div class="ai-slide-box"><b>Slide-ready chain</b><br>${esc(chain)}</div>`; }
      function revealTo(idx){ const safeIdx = Math.max(0, Math.min(idx, payload.nodes.length - 1)); step = safeIdx; nodeEls.forEach((g,i)=>{ g.classList.toggle('visible', i<=safeIdx); g.classList.toggle('active', i===safeIdx); }); links.forEach((l,i)=>l.classList.toggle('visible', i<safeIdx)); const n=payload.nodes[safeIdx]; panel.innerHTML = panelHtml(n, safeIdx); caption.innerHTML = `<b>${esc(n.id)}</b>  - ${esc(n.note)}`; bar.style.width = `${((safeIdx+1)/payload.nodes.length)*100}%`; }
      function reset(){ step=-1; if(timer) clearInterval(timer); timer=null; document.getElementById('ai-play').textContent='Begin Story'; nodeEls.forEach(g=>{g.classList.remove('visible','active');}); links.forEach(l=>l.classList.remove('visible')); bar.style.width='0%'; caption.innerHTML='Click Begin Story to reveal the mechanism step by step, or click any glowing node to inspect its evidence card.'; panel.innerHTML = `<span class="ai-panel-badge">Scientific Story Engine</span><h3>${esc(payload.topic)}</h3><div class="muted">${esc(payload.opening)}</div><div class="ai-label">Current lens</div><div class="ai-value">${esc(payload.mode)} - ${payload.nodes.length} story beats</div><div class="ai-slide-box"><b>How to use this module</b><br>Press Begin Story, then use each glowing node as one step of a scientific explanation. The right card gives the short interpretation and evidence layer.</div>`; }
      document.getElementById('ai-play').onclick = function(){ if(timer) clearInterval(timer); this.textContent='Playing'; revealTo(0); timer=setInterval(()=>{ if(step >= payload.nodes.length-1){ clearInterval(timer); timer=null; revealTo(payload.nodes.length-1); document.getElementById('ai-play').textContent='Replay Story'; return; } revealTo(step+1); }, 1150); };
      document.getElementById('ai-reset').onclick = reset; reset();
    })();
    </script>
    '''
    story_html = story_html.replace("__PAYLOAD__", json.dumps(story_payload, ensure_ascii=False))
    story_html = story_html.replace("__TOPIC__", str(story_payload["topic"]))
    story_html = story_html.replace("__SUBTITLE__", str(story_payload["subtitle"]))
    story_html = story_html.replace("__OPENING__", str(story_payload["opening"]))
    story_html = story_html.replace("__MODE__", str(story_payload["mode"]))

    components.html(story_html, height=700, scrolling=False)

    st.caption("This is a curated scientific-story visualization based on the review-paper mechanisms. It is designed for explanation and presentation, not as a raw-data simulation.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Story", story_topic)
    c2.metric("Lens", time_mode)
    c3.metric("Story beats", len(story_payload["nodes"]))
    c4.metric("Output mode", "Interactive")

    st.divider()
    st.subheader("Slide-ready export text")
    chain_text = " → ".join([n["id"] for n in story_payload["nodes"]])
    slide_note = f"""Slide title: {story_topic}  - {time_mode}

Main message: {current_story['opening']}

Visual chain: {chain_text}

Speaker note: Use the animation as a step-by-step explanation. Each node represents one scientific beat; the right card links the beat to evidence such as satellite observations, ocean data, paleo records, or coupled models."""
    st.code(slide_note)

    with st.expander("Storyboard table", expanded=False):
        storyboard_df = pd.DataFrame([
            {"Stage": i + 1, "Node": n["id"], "System / Type": n["type"], "Meaning": n["note"], "Evidence": n["evidence"]}
            for i, n in enumerate(story_payload["nodes"])
        ])
        st.dataframe(storyboard_df, use_container_width=True, hide_index=True)


elif module == "Mini Research Lab":
    st.markdown("<div class='atlas-module-title'><h1>&#129514; Mini Research Lab</h1></div>", unsafe_allow_html=True)
    lab_choice = st.radio(
        "Choose an experiment",
        ["Glacier Flow Simulator", "Ice Shelf Buttressing Lab", "Hydrofracture & Ice Shelf Collapse Lab"],
        horizontal=True
    )

    if lab_choice == "Glacier Flow Simulator":
        st.header("Interactive Antarctic Ice Sheet Simulator")

        with st.expander("Legend and visual guide", expanded=False):
            st.markdown("""
            - **White-blue surface:** Grounded ice sheet. Darker blue means thicker ice.
            - **Light blue floating surface:** Floating ice shelf extending over the ocean.
            - **Brown surface:** Bedrock beneath the ice.
            - **Transparent blue plane:** Ocean surface.
            - **Red line:** Grounding line, where grounded ice begins to float.
            - **Orange line arrows:** Ice flow direction.
            - **Cyan moving particles:** Ice parcels moving downstream.
            - **Orange/red subsurface patch:** Warm Circumpolar Deep Water intrusion.
            """)


        preset = st.selectbox(
            "Preset glacier mode",
            ["Custom", "Thwaites-like", "Pine Island-like", "Totten-like"]
        )
        st.caption(
            "Choose a conceptual glacier setting. The preset changes the default ocean forcing, ice shelf thickness, "
            "basal friction, and bed slope to resemble different Antarctic glacier styles."
        )

        if preset == "Thwaites-like":
            default_ocean_temp = 2.0
            default_snowfall = 1.0
            default_shelf = 160.0
            default_friction = 0.25
            default_slope = 3.2
        elif preset == "Pine Island-like":
            default_ocean_temp = 1.7
            default_snowfall = 1.1
            default_shelf = 180.0
            default_friction = 0.30
            default_slope = 2.8
        elif preset == "Totten-like":
            default_ocean_temp = 1.2
            default_snowfall = 1.5
            default_shelf = 240.0
            default_friction = 0.45
            default_slope = 2.0
        else:
            default_ocean_temp = 0.0
            default_snowfall = 1.0
            default_shelf = 200.0
            default_friction = 0.5
            default_slope = 1.0

        col1, col2, col3 = st.columns(3)

        with col1:
            year = st.slider("Simulation Year", 2025, 2100, 2025, 5)
            st.caption("Controls long-term climate forcing. Later years increase ocean warming and ice shelf thinning.")

            air_temp = st.slider("Air Temperature (°C)", -50.0, 0.0, -20.0, 1.0)
            st.caption("Represents atmospheric warming. Higher air temperature increases surface-related ice loss.")

            ocean_temp = st.slider("Ocean Temperature / CDW Forcing (°C)", -2.0, 5.0, default_ocean_temp, 0.1)
            st.caption("Represents warm ocean water forcing beneath ice shelves. Higher values enhance basal melting and retreat.")

        with col2:
            snowfall = st.slider("Snowfall / Accumulation (m/yr)", 0.0, 5.0, default_snowfall, 0.1)
            st.caption("Represents annual snow accumulation. More snowfall thickens the ice and partly offsets melting.")

            ice_shelf_thickness = st.slider("Ice Shelf Thickness (m)", 50.0, 500.0, default_shelf, 10.0)
            st.caption("Represents the strength of the floating ice shelf. Thicker shelves provide stronger buttressing.")

            basal_friction = st.slider("Basal Friction (0=low, 1=high)", 0.0, 1.0, default_friction, 0.05)
            st.caption("Controls resistance at the ice-bed interface. Lower friction allows faster ice flow.")

        with col3:
            bed_slope = st.slider("Bed Slope / Retrograde Bed Strength (°)", 0.0, 5.0, default_slope, 0.1)
            st.caption("Represents how strongly the bed deepens inland. Higher values make MISI-like retreat easier.")

            misi_on = st.checkbox("Enable MISI feedback", value=True)
            st.caption("Turns on Marine Ice Sheet Instability feedback. When active, retreat can accelerate on retrograde beds.")

            shelf_collapse = st.checkbox("Ice Shelf Collapse", value=False)
            st.caption("Simulates loss of ice shelf buttressing. When active, grounded ice flows faster toward the ocean.")

            cdw_intrusion = st.checkbox("CDW Warm Water Intrusion", value=True)
            st.caption("Adds warm Circumpolar Deep Water beneath the ice shelf, increasing basal melt and grounding-line retreat.")

        time_factor = (year - 2025) / (2100 - 2025)

        effective_ocean = ocean_temp + (1.2 * time_factor if cdw_intrusion else 0.2 * time_factor)
        effective_shelf = ice_shelf_thickness * (1 - 0.45 * time_factor if shelf_collapse else 1 - 0.12 * time_factor)
        effective_shelf = max(effective_shelf, 20.0)

        retreat = (
            8
            + effective_ocean * 7.0
            + bed_slope * 5.0
            - effective_shelf * 0.045
            - basal_friction * 9.0
        )

        if misi_on and bed_slope > 1.5 and effective_ocean > 0.5:
            misi_factor = 1 + 0.55 * bed_slope + 0.25 * effective_ocean
            retreat *= misi_factor

        if shelf_collapse:
            retreat *= 1.45

        if cdw_intrusion:
            retreat *= 1.18

        retreat = float(np.clip(retreat, 0, 68))
        glacier_length = 92 - retreat
        grounding_line_x = glacier_length

        nx, ny = 115, 62
        x = np.linspace(0, 105, nx)
        y = np.linspace(-32, 32, ny)
        X, Y = np.meshgrid(x, y)

        base_thickness = (
            620
            + snowfall * 110
            - effective_ocean * 55
            + effective_shelf * 0.35
            - bed_slope * 38
            - time_factor * 80
        )

        base_thickness = max(base_thickness, 120)

        center_shape = np.exp(-(Y / 20) ** 2)
        downstream_thinning = np.clip(1 - X / 112, 0, 1) ** 1.45
        surface_texture = 1 + 0.04 * np.sin(X / 7) * np.cos(Y / 6)

        thickness = base_thickness * center_shape * downstream_thinning * surface_texture
        thickness = np.clip(thickness, 12, None)

        bed = -150 - bed_slope * X * 9 + 65 * np.exp(-(Y / 25) ** 2)

        grounded_mask = X <= grounding_line_x
        shelf_mask = (X > grounding_line_x) & (X <= grounding_line_x + 18) & (not shelf_collapse)

        grounded_ice = np.where(grounded_mask, thickness, np.nan)

        shelf_thickness = effective_shelf * 0.55 * np.exp(-((X - grounding_line_x) / 22)) * np.exp(-(Y / 27) ** 2)
        shelf_surface = 70 + shelf_thickness
        floating_shelf = np.where(shelf_mask, shelf_surface, np.nan)

        bed_visible = np.where(X <= grounding_line_x + 22, bed, np.nan)

        ocean_level = np.zeros_like(X)
        ocean = np.where(X >= grounding_line_x - 3, ocean_level, np.nan)

        velocity_strength = max(
            0.08,
            0.35
            + effective_ocean * 0.30
            + (1 - basal_friction) * 1.45
            + bed_slope * 0.18
            + time_factor * 0.45
        )

        if misi_on and retreat > 20:
            velocity_strength *= 1.45

        if shelf_collapse:
            velocity_strength *= 1.35

        local_speed = velocity_strength * (0.25 + X / 95) * (thickness / np.nanmax(thickness))

        fig = go.Figure()

        fig.add_trace(go.Surface(
            z=bed_visible,
            x=X,
            y=Y,
            colorscale=[[0.0, "rgb(80,55,35)"], [0.5, "rgb(150,110,70)"], [1.0, "rgb(215,190,135)"]],
            opacity=0.36,
            showscale=False,
            name="Bedrock"
        ))

        fig.add_trace(go.Surface(
            z=ocean,
            x=X,
            y=Y,
            colorscale=[[0.0, "rgb(135,210,245)"], [1.0, "rgb(135,210,245)"]],
            opacity=0.32,
            showscale=False,
            name="Ocean"
        ))

        glacier_colorscale = [
            [0.00, "rgb(252,254,255)"],
            [0.20, "rgb(220,245,255)"],
            [0.45, "rgb(135,215,250)"],
            [0.70, "rgb(45,145,220)"],
            [1.00, "rgb(0,55,160)"]
        ]

        fig.add_trace(go.Surface(
            z=grounded_ice,
            x=X,
            y=Y,
            surfacecolor=thickness,
            colorscale=glacier_colorscale,
            opacity=0.97,
            colorbar=dict(title="Ice thickness (m)"),
            name="Grounded Ice",
            hovertemplate="Grounded ice<br>x=%{x:.1f} km<br>y=%{y:.1f} km<br>thickness=%{z:.1f} m<extra></extra>"
        ))

        fig.add_trace(go.Surface(
            z=floating_shelf,
            x=X,
            y=Y,
            colorscale=[[0.0, "rgb(205,245,255)"], [1.0, "rgb(150,230,255)"]],
            opacity=0.72,
            showscale=False,
            name="Floating Ice Shelf",
            hovertemplate="Floating ice shelf<br>x=%{x:.1f} km<br>y=%{y:.1f} km<extra></extra>"
        ))

        gl_y = np.linspace(-30, 30, 80)
        gl_x = np.full_like(gl_y, grounding_line_x)
        gl_z = np.full_like(gl_y, 90)

        fig.add_trace(go.Scatter3d(
            x=gl_x,
            y=gl_y,
            z=gl_z,
            mode="lines",
            line=dict(color="rgb(230,30,30)", width=8),
            name="Grounding Line"
        ))

        if cdw_intrusion:
            plume_y = np.linspace(-18, 18, 30)
            plume_x = np.linspace(grounding_line_x - 8, grounding_line_x + 22, 30)
            PX, PY = np.meshgrid(plume_x, plume_y)
            PZ = -25 + 5 * np.sin(PX / 6)
            fig.add_trace(go.Surface(
                z=PZ,
                x=PX,
                y=PY,
                colorscale=[[0.0, "rgb(255,210,80)"], [1.0, "rgb(255,70,20)"]],
                opacity=0.38,
                showscale=False,
                name="CDW Intrusion"
            ))

        arrow_x, arrow_y, arrow_z = [], [], []
        for i in range(8, nx - 15, 14):
            for j in range(7, ny - 7, 13):
                if not np.isfinite(grounded_ice[j, i]):
                    continue

                speed = local_speed[j, i]
                dx = 3.6 * (0.9 + 0.22 * speed)
                dy = -Y[j, i] / 44 * 1.2

                x0 = X[j, i]
                y0 = Y[j, i]
                z0 = grounded_ice[j, i] + 10
                x1 = x0 + dx
                y1 = y0 + dy
                z1 = z0 + 1

                arrow_x += [x0, x1, None]
                arrow_y += [y0, y1, None]
                arrow_z += [z0, z1, None]

                arrow_x += [x1, x1 - 0.9, None, x1, x1 - 0.9, None]
                arrow_y += [y1, y1 + 0.45, None, y1, y1 - 0.45, None]
                arrow_z += [z1, z1, None, z1, z1, None]

        fig.add_trace(go.Scatter3d(
            x=arrow_x,
            y=arrow_y,
            z=arrow_z,
            mode="lines",
            line=dict(color="rgb(255,155,45)", width=4),
            name="Ice Flow Direction"
        ))

        n_streams = 8
        n_particles_each = 18
        stream_ys = np.linspace(-17, 17, n_streams)

        # Particle animation fix:
        # The previous version used modulo wrapping:
        #     px = (x0 + speed * t) % grounding_line_x
        # When a particle crossed the grounding line, Plotly sometimes interpolated it
        # from the downstream end back to the upstream start, which looked like reverse flow
        # under high-speed / short-glacier parameter combinations.
        # This version uses one-way particles: they enter from upstream, move downstream,
        # and disappear after crossing the grounding line. No point is ever moved backward.
        flow_length = max(grounding_line_x, 8)
        particle_x0, particle_y0 = [], []
        for sy in stream_ys:
            for k in range(n_particles_each):
                particle_x0.append(-0.75 * flow_length + (k / (n_particles_each - 1)) * 1.65 * flow_length)
                particle_y0.append(sy)

        particle_x0 = np.array(particle_x0)
        particle_y0 = np.array(particle_y0)

        frame_count = 72
        downstream_step = (1.55 * flow_length / frame_count) * (0.65 + 0.18 * velocity_strength)

        def particle_frame(t):
            px_raw = particle_x0 + t * downstream_step
            visible = (px_raw >= 0) & (px_raw <= flow_length)

            px = np.where(visible, px_raw, np.nan)
            py = np.where(visible, particle_y0 + 1.2 * np.sin(px_raw / 9 + particle_y0 / 5), np.nan)

            p_center = np.exp(-(py / 20) ** 2)
            p_down = np.clip(1 - px / 112, 0, 1) ** 1.45
            p_texture = 1 + 0.04 * np.sin(px / 7) * np.cos(py / 6)

            pz = base_thickness * p_center * p_down * p_texture + 14
            pz = np.where(visible, pz, np.nan)
            return px, py, pz

        px, py, pz = particle_frame(0)

        fig.add_trace(go.Scatter3d(
            x=px,
            y=py,
            z=pz,
            mode="markers",
            marker=dict(size=3.0, color="rgb(0,235,210)", opacity=0.9),
            name="Moving Ice Particles"
        ))

        particle_trace_index = len(fig.data) - 1

        frames = []
        for t in range(frame_count):
            px, py, pz = particle_frame(t)
            frames.append(go.Frame(
                data=[go.Scatter3d(
                    x=px,
                    y=py,
                    z=pz,
                    mode="markers",
                    marker=dict(size=3.0, color="rgb(0,235,210)", opacity=0.9)
                )],
                traces=[particle_trace_index],
                name=str(t)
            ))

        fig.frames = frames

        fig.update_layout(
            height=760,
            margin=dict(l=0, r=0, t=35, b=0),
            scene=dict(
                xaxis_title="Distance downstream (km)",
                yaxis_title="Glacier width (km)",
                zaxis_title="Elevation / Thickness (m)",
                bgcolor="white",
                camera=dict(eye=dict(x=1.65, y=-1.9, z=1.15))
            ),
            updatemenus=[dict(
                type="buttons",
                direction="left",
                showactive=False,
                x=0.02,
                y=0.95,
                buttons=[
                    dict(
                        label="Play ice flow",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 85, "redraw": True},
                            "fromcurrent": True,
                            "mode": "immediate",
                            "transition": {"duration": 0},
                            "loop": False
                        }]
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "transition": {"duration": 0}
                        }]
                    )
                ]
            )]
        )

        # Render the animated Plotly figure inside an isolated HTML iframe.
        # This keeps the animation button while avoiding Streamlit's frontend DOM
        # removeChild conflict that can happen with st.plotly_chart + 3D frames.
        plot_html = fig.to_html(
            include_plotlyjs="inline",
            full_html=False,
            config={"responsive": True, "displayModeBar": True}
        )
        components.html(plot_html, height=790, scrolling=False)

        ice_loss = (
            (abs(air_temp) * 0.04 + max(effective_ocean, 0) * 2.6)
            * (1.25 - basal_friction * 0.65)
            / (snowfall + 0.5)
        )
        sea_level = retreat * 0.013
        velocity = velocity_strength * 1.8

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ice Loss", f"{ice_loss:.2f}")
        c2.metric("Grounding Line Retreat", f"{retreat:.1f} km")
        c3.metric("Ice Flow Velocity", f"{velocity:.2f} km/yr")
        c4.metric("Sea Level Contribution", f"{sea_level:.2f} m")


    elif lab_choice == "Ice Shelf Buttressing Lab":
        st.header("Ice Shelf Buttressing Lab")

        with st.expander("Legend and mechanism guide", expanded=False):
            st.markdown("""
            - **Dark blue block:** Grounded ice sheet flowing toward the ocean.
            - **Light blue block:** Floating ice shelf.
            - **Orange arrows:** Relative ice-flow speed.
            - **Brown bump:** Pinning point / local topographic resistance.
            - **Red dashed line:** Grounding line.
            - **Gray removed zone:** Calved or collapsed ice-shelf area.
            - **Blue back-stress arrows:** Buttressing force pushing back against grounded ice.
            """)


        st.caption(
            "This conceptual lab focuses on one mechanism: a floating ice shelf can provide back stress "
            "that slows down inland grounded ice. When the shelf thins, calves, or loses pinning points, "
            "buttressing weakens and grounded ice accelerates."
        )

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            shelf_thickness = st.slider("Ice Shelf Thickness (m)", 50.0, 700.0, 260.0, 10.0, key="buttress_shelf_thickness")
            st.caption("Thicker ice shelves provide stronger mechanical support to inland grounded ice.")

            ocean_temp_b = st.slider("Ocean Temperature Forcing (°C)", -2.0, 5.0, 1.0, 0.1, key="buttress_ocean_temp")
            st.caption("Warmer ocean water increases basal melting and weakens the ice shelf from below.")

        with col_b:
            pinning_strength = st.slider("Pinning Point Strength (%)", 0.0, 100.0, 55.0, 5.0, key="buttress_pinning")
            st.caption("Pinning points are bedrock highs or obstacles that help the ice shelf resist flow.")

            calving_extent = st.slider("Calving / Shelf Loss (%)", 0.0, 100.0, 20.0, 5.0, key="buttress_calving")
            st.caption("Larger calving extent removes floating shelf area and reduces buttressing.")

        with col_c:
            lateral_confinement = st.slider("Lateral Confinement (%)", 0.0, 100.0, 60.0, 5.0, key="buttress_lateral")
            st.caption("Narrow embayments and side walls can strengthen buttressing by resisting shelf spreading.")

            bed_slope_b = st.slider("Retrograde Bed Slope (°)", 0.0, 5.0, 1.5, 0.1, key="buttress_bed_slope")
            st.caption("A stronger retrograde bed makes grounding-line retreat more unstable.")

        thickness_factor = shelf_thickness / 700.0
        pinning_factor = pinning_strength / 100.0
        lateral_factor = lateral_confinement / 100.0
        calving_factor = calving_extent / 100.0
        ocean_factor = max(ocean_temp_b, 0.0) / 5.0

        buttressing_index = (
            100
            * (0.45 * thickness_factor + 0.30 * pinning_factor + 0.25 * lateral_factor)
            * (1 - 0.75 * calving_factor)
            * (1 - 0.45 * ocean_factor)
        )
        buttressing_index = float(np.clip(buttressing_index, 0, 100))

        velocity = 180 + (100 - buttressing_index) * 8.5 + ocean_factor * 260 + bed_slope_b * 55
        retreat_b = float(np.clip((100 - buttressing_index) * 0.18 + ocean_factor * 8 + bed_slope_b * 2.0, 0, 45))
        sea_level_b = retreat_b * 0.011

        grounding_line_x = 42
        shelf_full_length = 42
        remaining_shelf_length = shelf_full_length * (1 - calving_factor)
        shelf_end = grounding_line_x + remaining_shelf_length
        removed_start = shelf_end
        removed_end = grounding_line_x + shelf_full_length

        fig = go.Figure()

        fig.add_shape(
            type="rect",
            x0=grounding_line_x,
            x1=92,
            y0=-1.6,
            y1=1.6,
            line=dict(width=0),
            fillcolor="rgba(120,210,245,0.35)",
            layer="below"
        )

        bed_x = np.linspace(0, 92, 180)
        bed_y = -1.35 - 0.006 * bed_slope_b * bed_x + 0.16 * np.exp(-((bed_x - 56) / 6) ** 2)
        fig.add_trace(go.Scatter(
            x=bed_x,
            y=bed_y,
            mode="lines",
            line=dict(color="rgb(130,85,45)", width=5),
            name="Bedrock"
        ))

        ice_top = 0.82
        ice_bottom = -0.35
        fig.add_shape(
            type="rect",
            x0=0,
            x1=grounding_line_x,
            y0=ice_bottom,
            y1=ice_top,
            line=dict(color="rgb(0,55,160)", width=2),
            fillcolor="rgba(20,110,210,0.86)",
            layer="above"
        )

        shelf_thick_vis = 0.28 + 0.55 * thickness_factor
        fig.add_shape(
            type="rect",
            x0=grounding_line_x,
            x1=shelf_end,
            y0=-shelf_thick_vis / 2,
            y1=shelf_thick_vis / 2,
            line=dict(color="rgb(70,170,220)", width=2),
            fillcolor="rgba(170,235,255,0.80)",
            layer="above"
        )

        if calving_extent > 0:
            fig.add_shape(
                type="rect",
                x0=removed_start,
                x1=removed_end,
                y0=-0.42,
                y1=0.42,
                line=dict(color="rgba(120,120,120,0.7)", width=1, dash="dash"),
                fillcolor="rgba(150,150,150,0.18)",
                layer="above"
            )
            fig.add_annotation(
                x=(removed_start + removed_end) / 2,
                y=0.65,
                text="calved / lost shelf area",
                showarrow=False,
                font=dict(size=12, color="gray")
            )

        pin_x = grounding_line_x + remaining_shelf_length * 0.58 if remaining_shelf_length > 5 else grounding_line_x + 3
        pin_size = 0.16 + 0.45 * pinning_factor
        if remaining_shelf_length > 4 and pinning_strength > 0:
            fig.add_shape(
                type="circle",
                x0=pin_x - 2.4 * pin_size,
                x1=pin_x + 2.4 * pin_size,
                y0=-0.75 - pin_size,
                y1=-0.75 + pin_size,
                line=dict(color="rgb(120,70,35)", width=2),
                fillcolor="rgba(155,95,45,0.85)",
                layer="above"
            )
            fig.add_annotation(
                x=pin_x,
                y=-1.05,
                text="pinning point",
                showarrow=False,
                font=dict(size=12, color="rgb(100,65,35)")
            )

        fig.add_trace(go.Scatter(
            x=[grounding_line_x, grounding_line_x],
            y=[-1.25, 1.2],
            mode="lines",
            line=dict(color="red", width=4, dash="dash"),
            name="Grounding Line"
        ))

        arrow_count = 6
        speed_scale = np.clip((velocity - 180) / 950, 0.15, 1.0)
        for k in range(arrow_count):
            y_arrow = -0.05 + (k - (arrow_count - 1) / 2) * 0.17
            x0 = 8 + k * 4.5
            x1 = x0 + 6 + 9 * speed_scale
            fig.add_annotation(
                x=x1,
                y=y_arrow,
                ax=x0,
                ay=y_arrow,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1.4,
                arrowwidth=2.8 + 2.8 * speed_scale,
                arrowcolor="rgb(255,140,40)"
            )

        backstress = buttressing_index / 100
        for k in range(4):
            yb = -0.35 + k * 0.23
            fig.add_annotation(
                x=grounding_line_x - 7 * backstress,
                y=yb,
                ax=grounding_line_x + 9 * backstress,
                ay=yb,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1.1,
                arrowwidth=1.5 + 3 * backstress,
                arrowcolor="rgba(40,90,190,0.8)"
            )

        fig.add_annotation(x=18, y=1.05, text="<b>Grounded ice</b>", showarrow=False, font=dict(size=14, color="white"))
        fig.add_annotation(x=grounding_line_x + max(remaining_shelf_length, 5) / 2, y=0.55, text="<b>Floating ice shelf</b>", showarrow=False, font=dict(size=13, color="rgb(20,85,130)"))
        fig.add_annotation(x=75, y=-1.05, text="<b>Ocean</b>", showarrow=False, font=dict(size=14, color="rgb(30,120,170)"))

        fig.update_layout(
            title="Conceptual Ice Shelf Buttressing Experiment",
            height=520,
            margin=dict(l=20, r=20, t=60, b=20),
            xaxis=dict(title="Distance downstream (km)", range=[0, 92], showgrid=False),
            yaxis=dict(visible=False, range=[-1.65, 1.35]),
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True, key="plot_buttressing_lab")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Buttressing Index", f"{buttressing_index:.0f} / 100")
        c2.metric("Ice Flow Velocity", f"{velocity:.0f} m/yr")
        c3.metric("Grounding Line Retreat", f"{retreat_b:.1f} km")
        c4.metric("Sea Level Contribution", f"{sea_level_b:.2f} m")

        st.markdown("""
        **How to read this lab:**  
        When the ice shelf is thick, laterally confined, and pinned to bedrock highs, it pushes back against the grounded ice.
        This reduces ice velocity and stabilizes the grounding line. When the shelf thins or calves away, the back stress weakens,
        orange flow arrows become stronger, and the grounding-line retreat estimate increases.
        """)


    elif lab_choice == "Hydrofracture & Ice Shelf Collapse Lab":
        st.header("Hydrofracture & Ice Shelf Collapse Lab")

        with st.expander("Legend and collapse sequence", expanded=False):
            st.markdown("""
            - **Ice-blue slab:** Floating ice shelf.
            - **Deep blue ponds:** Surface meltwater ponds.
            - **Red cracks:** Hydrofracture pathways driven by water-filled crevasses.
            - **Gray separated blocks:** Collapsed / fragmented ice shelf pieces.
            - **Orange arrows:** Post-collapse acceleration of inland ice.
            - **Dark ocean background:** Open ocean beneath and around the floating shelf.
            """)


        st.caption(
            "This conceptual lab visualizes how atmospheric warming can create surface meltwater, "
            "how meltwater can deepen crevasses through hydrofracture, and how an ice shelf can fragment. "
            "It is designed for visual explanation rather than numerical prediction."
        )

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            surface_melt = st.slider("Surface Melt Intensity (%)", 0.0, 100.0, 45.0, 5.0, key="hydro_surface_melt")
            st.caption("Higher surface melt produces more melt ponds on top of the ice shelf.")

            firn_capacity = st.slider("Firn Air Capacity (%)", 0.0, 100.0, 45.0, 5.0, key="hydro_firn")
            st.caption("Higher firn capacity absorbs meltwater and delays ponding and fracture.")

        with col_b:
            crevasse_density = st.slider("Crevasse Density (%)", 0.0, 100.0, 40.0, 5.0, key="hydro_crevasse_density")
            st.caption("More pre-existing crevasses make hydrofracture easier once meltwater is present.")

            ice_shelf_strength = st.slider("Ice Shelf Strength (%)", 0.0, 100.0, 60.0, 5.0, key="hydro_shelf_strength")
            st.caption("Stronger ice resists crack propagation and large-scale breakup.")

        with col_c:
            ocean_swell = st.slider("Ocean Swell / Flexure (%)", 0.0, 100.0, 35.0, 5.0, key="hydro_swell")
            st.caption("Ocean swell and flexure can help existing fractures widen and connect.")

            play_stage = st.slider("Collapse Stage", 0, 4, 2, 1, key="hydro_stage")
            st.caption("Manually move through the collapse sequence: intact shelf ->ponds ->cracks ->fragmentation ->post-collapse acceleration.")

        ponding_index = np.clip((surface_melt * 0.75 - firn_capacity * 0.45 + 20) / 100, 0, 1)
        fracture_index = np.clip(
            0.45 * ponding_index
            + 0.30 * (crevasse_density / 100)
            + 0.20 * (ocean_swell / 100)
            - 0.25 * (ice_shelf_strength / 100),
            0, 1
        )
        collapse_risk = np.clip(
            100 * (0.55 * fracture_index + 0.35 * ponding_index + 0.10 * (ocean_swell / 100)),
            0, 100
        )

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

        buttressing_remaining = np.clip(100 - collapse_risk * 0.85 - (stage >= 3) * 25, 0, 100)
        post_collapse_velocity = 300 + (100 - buttressing_remaining) * 18
        sea_level_signal = (100 - buttressing_remaining) * 0.018

        st.info(
            f"Auto-diagnosed stage from the sliders: **{auto_stage}**. "
            f"The displayed stage is the larger of the auto-diagnosed stage and the manual Collapse Stage slider."
        )

        fig = go.Figure()

        # Ocean background
        fig.add_shape(
            type="rect",
            x0=0,
            x1=100,
            y0=0,
            y1=44,
            line=dict(width=0),
            fillcolor="rgba(10,45,85,0.92)",
            layer="below"
        )

        # Ice shelf base geometry
        shelf_y0, shelf_y1 = 12, 32
        shelf_x0, shelf_x1 = 8, 92

        if stage < 3:
            # Intact or cracking shelf
            fig.add_shape(
                type="rect",
                x0=shelf_x0,
                x1=shelf_x1,
                y0=shelf_y0,
                y1=shelf_y1,
                line=dict(color="rgb(120,220,250)", width=2),
                fillcolor="rgba(185,240,255,0.92)",
                layer="above"
            )
        else:
            # Fragmented shelf blocks
            blocks = [
                (8, 25, 13, 31, -1.2),
                (28, 42, 11, 28, 1.5),
                (46, 60, 15, 33, -0.8),
                (64, 78, 10, 27, 1.0),
                (81, 93, 14, 30, -1.6),
            ]
            for x0, x1, y0, y1, dy in blocks:
                fig.add_shape(
                    type="rect",
                    x0=x0,
                    x1=x1,
                    y0=y0 + dy,
                    y1=y1 + dy,
                    line=dict(color="rgb(165,220,235)", width=2),
                    fillcolor="rgba(200,245,255,0.78)",
                    layer="above"
                )

            # Open-water gaps
            for gx in [26, 44, 62, 79]:
                fig.add_shape(
                    type="rect",
                    x0=gx,
                    x1=gx + 2.8,
                    y0=8,
                    y1=36,
                    line=dict(width=0),
                    fillcolor="rgba(5,35,75,0.92)",
                    layer="above"
                )

        # Grounded ice / inland side
        fig.add_shape(
            type="rect",
            x0=0,
            x1=15,
            y0=10,
            y1=34,
            line=dict(color="rgb(0,65,160)", width=2),
            fillcolor="rgba(40,120,215,0.92)",
            layer="above"
        )
        fig.add_annotation(x=7.5, y=35.5, text="<b>Grounded ice</b>", showarrow=False, font=dict(color="rgb(0,45,120)", size=13))
        fig.add_annotation(x=50, y=34.8, text="<b>Floating ice shelf</b>", showarrow=False, font=dict(color="rgb(15,100,145)", size=15))
        fig.add_annotation(x=82, y=6.5, text="<b>Ocean</b>", showarrow=False, font=dict(color="white", size=15))

        # Surface melt ponds
        pond_positions = [
            (22, 27.5, 5.2, 1.5),
            (37, 25.0, 6.0, 1.7),
            (52, 28.5, 5.6, 1.4),
            (67, 24.3, 6.3, 1.8),
            (80, 27.8, 4.6, 1.3),
        ]
        n_ponds = int(np.clip(round(ponding_index * len(pond_positions) + (stage >= 1) * 2), 0, len(pond_positions)))
        if stage >= 1:
            for px, py, w, h in pond_positions[:n_ponds]:
                fig.add_shape(
                    type="circle",
                    x0=px - w / 2,
                    x1=px + w / 2,
                    y0=py - h / 2,
                    y1=py + h / 2,
                    line=dict(color="rgb(0,95,210)", width=2),
                    fillcolor="rgba(0,120,255,0.80)",
                    layer="above"
                )

        # Hydrofracture cracks
        crack_xs = [25, 39, 55, 70, 83]
        crack_depth = 3 + 18 * fracture_index + stage * 3
        if stage >= 2:
            for c_i, cx in enumerate(crack_xs[:max(2, int(2 + crevasse_density / 25))]):
                y_top = shelf_y1 - 1.5
                y_bottom = max(shelf_y0 - 4, y_top - crack_depth)
                fig.add_trace(go.Scatter(
                    x=[cx, cx + 0.8 * np.sin(c_i), cx - 0.5 * np.cos(c_i)],
                    y=[y_top, (y_top + y_bottom) / 2, y_bottom],
                    mode="lines",
                    line=dict(color="rgb(220,20,35)", width=5 if stage < 4 else 7),
                    name="Hydrofracture" if c_i == 0 else None,
                    showlegend=(c_i == 0)
                ))

        # Collapse burst lines / fragments
        if stage >= 4:
            burst_center = (55, 22)
            for angle in np.linspace(0, 2 * np.pi, 18, endpoint=False):
                r1 = 5
                r2 = 16 + 5 * np.sin(3 * angle)
                fig.add_trace(go.Scatter(
                    x=[burst_center[0] + r1 * np.cos(angle), burst_center[0] + r2 * np.cos(angle)],
                    y=[burst_center[1] + r1 * np.sin(angle), burst_center[1] + r2 * np.sin(angle)],
                    mode="lines",
                    line=dict(color="rgba(255,255,255,0.75)", width=2),
                    showlegend=False
                ))
            fig.add_annotation(
                x=55,
                y=22,
                text="<b>ICE SHELF BREAKUP</b>",
                showarrow=False,
                font=dict(size=22, color="rgb(255,70,50)")
            )

        # Inland acceleration arrows
        speed_scale = np.clip((post_collapse_velocity - 300) / 1800, 0.15, 1)
        arrow_n = 5
        for k in range(arrow_n):
            y_arrow = 15 + k * 3.4
            x0 = 3
            x1 = 16 + 14 * speed_scale
            fig.add_annotation(
                x=x1,
                y=y_arrow,
                ax=x0,
                ay=y_arrow,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1.6,
                arrowwidth=2.4 + 5 * speed_scale,
                arrowcolor="rgb(255,140,35)"
            )

        # Stage labels
        stage_labels = [
            "0 Intact shelf",
            "1 Melt ponds form",
            "2 Water-filled cracks deepen",
            "3 Shelf fragments",
            "4 Breakup and flow acceleration"
        ]
        fig.add_annotation(
            x=50,
            y=40.5,
            text=f"<b>{stage_labels[stage]}</b>",
            showarrow=False,
            font=dict(size=18, color="white")
        )

        fig.update_layout(
            title="Hydrofracture & Ice Shelf Collapse Experiment",
            height=620,
            margin=dict(l=20, r=20, t=65, b=25),
            xaxis=dict(visible=False, range=[0, 100]),
            yaxis=dict(visible=False, range=[0, 44]),
            plot_bgcolor="rgb(8,35,70)",
            paper_bgcolor="white",
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True, key="plot_hydrofracture_lab")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ponding Index", f"{ponding_index * 100:.0f} / 100")
        c2.metric("Fracture Index", f"{fracture_index * 100:.0f} / 100")
        c3.metric("Buttressing Remaining", f"{buttressing_remaining:.0f} / 100")
        c4.metric("Post-collapse Velocity", f"{post_collapse_velocity:.0f} m/yr")

        st.metric("Conceptual Sea-level Signal", f"{sea_level_signal:.2f} m")

        st.markdown("""
        **How to read this lab:**  
        Surface melt creates ponds on the ice shelf. If firn cannot absorb enough meltwater, water can fill crevasses.
        Water pressure helps cracks propagate downward, a process called **hydrofracture**. Once fractures connect,
        the shelf can fragment, buttressing is lost, and inland ice can accelerate toward the ocean.
        """)


elif module == "Read Raw Paper":
    st.markdown("<div class='atlas-module-title'><h1>&#128196; Read Raw Paper</h1></div>", unsafe_allow_html=True)
    search_query = st.text_input("Search within extracted paper text", placeholder="Example: grounding line, basal melt, Thwaites")
    search_keywords = extract_keywords(search_query) if search_query.strip() else []
    if search_query.strip():
        matches = search_pages(pages, search_keywords, max_results=8)
        if matches:
            page_options = [r["page"] for r in matches]
            selected_page = st.selectbox("Matching pages", page_options, format_func=lambda p: f"Page {p}")
            st.markdown("#### Search matches")
            for match in matches[:4]:
                excerpt = build_search_excerpt(match["text"], search_keywords)
                st.markdown(
                    f"""
                    <div class="ios-result-card">
                      <div class="ios-kicker">Page {match['page']} · score {match['score']}</div>
                      <div class="ios-muted">{excerpt}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.warning("No matching pages found. Showing page 1.")
            selected_page = 1
    else:
        selected_page = st.slider("Select page", 1, total_pages, 1)
    st.text_area(f"Page {selected_page}", pages[selected_page - 1]["text"], height=600)
