"""Legacy Streamlit shim over the shared core.paper logic.

The heavy lifting (clean_text, search, excerpts, PDF parsing) now lives in
core/paper.py; this module keeps only the Streamlit-cached loader and the
list[dict] page shape the Streamlit pages expect. build_search_excerpt keeps
the <mark> highlight the web UI uses (the desktop app uses <span>).
"""
from typing import List

import streamlit as st

from .config import PDF_FILENAME, PDF_PATH
from core.paper import (
    clean_text,
    extract_paper_keywords,
    extract_search_keywords,
    load_pdf_pages,
    build_search_excerpt as _core_build_search_excerpt,
    scored_search_pages,
    scored_search_pages_by_keywords,
)

__all__ = [
    "load_pdf",
    "clean_text",
    "extract_keywords",
    "search_pages",
    "build_search_excerpt",
    "extract_paper_keywords",
    "extract_search_keywords",
    "scored_search_pages",
    "scored_search_pages_by_keywords",
]


@st.cache_data
def load_pdf() -> list[dict]:
    if not PDF_PATH.exists():
        st.error(
            "Source PDF not found. Put the review paper in the project root with this exact filename: "
            f"{PDF_FILENAME}"
        )
        st.stop()
    return [{"page": p.page, "text": p.text} for p in load_pdf_pages(PDF_PATH)]


def extract_keywords(question: str) -> List[str]:
    """Legacy keyword extraction (Chinese-aware) for the web app."""
    return extract_paper_keywords(question)


def build_search_excerpt(text: str, keywords: list[str], radius: int = 220) -> str:
    """Web-app excerpt with <mark> highlight (the desktop app uses <span>)."""
    return _core_build_search_excerpt(text, keywords, radius=radius, highlight="mark")


def search_pages(pages: list[dict], keywords: list[str], max_results: int = 5) -> list[dict]:
    """Search a list[dict] page list by pre-extracted keywords, keeping the
    legacy pages-1-5 fallback when nothing matches."""
    results = []
    for item in pages:
        text_lower = item["text"].lower()
        score = sum(text_lower.count(k.lower()) for k in keywords if k)
        if score > 0:
            results.append({"page": item["page"], "score": score, "text": clean_text(item["text"])})
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:max_results]
    if not results:
        for item in pages:
            if item["page"] in [1, 2, 3, 4, 5]:
                results.append({"page": item["page"], "score": 0, "text": clean_text(item["text"])})
    return results
