import html
import re

import jieba
import pdfplumber
import streamlit as st

from .config import PDF_FILENAME, PDF_PATH


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
