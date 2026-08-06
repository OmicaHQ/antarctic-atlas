"""Core paper search and text processing — zero Qt/Streamlit dependencies."""
import html
import os
import pickle
import re
import sys
from pathlib import Path

import jieba
import pdfplumber

from .models import PaperPage

CHINESE_PAPER_KEYWORDS = {
    "接地线": ["grounding line", "grounding zone"],
    "后退": ["retreat", "migration"],
    "冰架": ["ice shelf", "buttressing"],
    "基底": ["basal", "bed"],
    "融化": ["melt", "melting", "basal melt"],
    "海平面": ["sea level", "sea-level rise"],
    "温水": ["warm water", "circumpolar deep water", "cdw"],
    "环南极深层水": ["circumpolar deep water", "cdw"],
    "不稳定": ["instability", "misi", "mici"],
    "雷达": ["radar", "ice penetrating radar"],
    "卫星": ["satellite", "remote sensing"],
    "重力": ["grace", "gravity"],
    "古气候": ["paleoclimate", "pliocene", "last interglacial"],
}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


_HIGHLIGHT_SPAN = "<span style='background-color:#7a5a13; color:#fff7d6; font-weight:700'>"


def extract_search_keywords(query: str) -> list[str]:
    return _query_keywords(query)


def _tokenize_query(query: str) -> list[str]:
    """Split a query into tokens, jieba-segmenting Chinese text.

    re.findall(r"[\\w-]+") treats an entire CJK query as one un-matchable token,
    so queries containing Chinese are segmented with jieba first.
    """
    query = str(query or "")
    if not query.strip():
        return []
    if re.search(r"[一-鿿]", query):
        return [word for word in jieba.lcut(query) if len(word.strip()) > 1]
    return [word for word in re.findall(r"[\w-]+", query) if len(word) > 1]


def _query_keywords(query: str) -> list[str]:
    """Searchable keywords for a query: jieba-segmented tokens (for CJK queries)
    plus English expansions for Chinese terms via CHINESE_PAPER_KEYWORDS, so a
    Chinese query can match the English paper text."""
    query = str(query or "")
    tokens = list(_tokenize_query(query))
    for chinese, mapped_terms in CHINESE_PAPER_KEYWORDS.items():
        if chinese in query:
            tokens.extend(mapped_terms)
    return [token.lower() for token in dict.fromkeys(tokens) if len(token.strip()) > 1]


def build_search_excerpt(text: str, keywords: list[str], radius: int = 220, highlight: str = "span") -> str:
    cleaned = clean_text(text)
    lowered = cleaned.lower()
    hit_positions = [lowered.find(keyword.lower()) for keyword in keywords if keyword and lowered.find(keyword.lower()) >= 0]
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
    open_tag, close_tag = _highlight_tags(highlight)
    keywords = sorted({k for k in (str(k).lower() for k in keywords) if len(k) > 1}, key=len, reverse=True)
    if keywords:
        pattern = re.compile("|".join(re.escape(html.escape(k)) for k in keywords), re.IGNORECASE)
        escaped = pattern.sub(lambda match: f"{open_tag}{match.group(0)}{close_tag}", escaped)
    return escaped


def _highlight_tags(highlight: str) -> tuple[str, str]:
    if highlight == "mark":
        return "<mark>", "</mark>"
    return _HIGHLIGHT_SPAN, "</span>"


def extract_paper_keywords(text: str) -> list[str]:
    raw = str(text or "")
    terms = [word for word in jieba.cut(raw) if len(word) > 1]
    terms.extend(re.findall(r"\w+", raw))
    for chinese, mapped_terms in CHINESE_PAPER_KEYWORDS.items():
        if chinese in raw:
            terms.extend(mapped_terms)
    return [term.lower() for term in dict.fromkeys(terms) if len(term) > 1]


def is_low_value_reference_page(text: str) -> bool:
    lowered = clean_text(text).lower()
    signals = [
        "references",
        "bibliography",
        " et al.",
        "doi:",
        "journal of geophysical research",
        "geophysical research letters",
    ]
    signal_count = sum(lowered.count(signal) for signal in signals)
    citation_like = len(re.findall(r"\(\d{4}\)|\b19\d{2}\b|\b20\d{2}\b", lowered))
    return signal_count >= 3 or citation_like >= 18


def is_overview_question(text: str) -> bool:
    lowered = str(text or "").lower()
    overview_terms = ["overview", "summary", "summarize", "paper about", "main idea",
                      "综述", "论文", "主要", "概括", "总结", "讲了什么"]
    return any(term in lowered for term in overview_terms)


def clean_answer_markdown(text: str) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(r"\s*\(?\bPage\s+\d+\b\)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*（?\bpage\s+\d+\b）?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*第\s*\d+\s*页", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def search_pages(pages: list[PaperPage], query: str, max_results: int = 12) -> list[PaperPage]:
    keywords = _query_keywords(query)
    if not keywords:
        return []
    results = []
    for page in pages:
        lowered = page.text.lower()
        score = sum(lowered.count(keyword) for keyword in keywords)
        if score:
            results.append((score, page))
    return [page for _, page in sorted(results, key=lambda item: item[0], reverse=True)[:max_results]]


def scored_search_pages(pages: list[PaperPage], query: str, max_results: int = 5) -> list[tuple[int, PaperPage]]:
    keywords = _query_keywords(query)
    if not keywords:
        return []
    results = []
    for page in pages:
        lowered = page.text.lower()
        score = sum(lowered.count(keyword) for keyword in keywords)
        if score:
            results.append((score, page))
    return sorted(results, key=lambda item: item[0], reverse=True)[:max_results]


def scored_search_pages_by_keywords(
    pages: list[PaperPage], keywords: list[str], max_results: int = 5
) -> list[tuple[float, PaperPage]]:
    normalized = [clean_text(str(keyword)).lower() for keyword in keywords if clean_text(str(keyword))]
    normalized = list(dict.fromkeys(normalized))
    if not normalized:
        return []
    results: list[tuple[float, PaperPage]] = []
    for page in pages:
        lowered = page.text.lower()
        score = 0.0
        for keyword in normalized:
            count = lowered.count(keyword)
            if count:
                score += count * (3 if " " in keyword else 1)
        if score:
            if is_low_value_reference_page(page.text):
                score *= 0.05
            results.append((score, page))
    return sorted(results, key=lambda item: item[0], reverse=True)[:max_results]


# ── PDF loading (with persistent text cache) ─────────────────────────────

def _cache_path():
    """Per-user cache file for extracted paper text, keyed by PDF identity."""
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "AntarcticAtlas" / "pages.pkl"


def _pdf_fingerprint(pdf_path):
    try:
        stat = pdf_path.stat()
        return stat.st_size, int(stat.st_mtime)
    except OSError:
        return None


def load_pdf_pages(pdf_path, x_tolerance=1.5, y_tolerance=3.0):
    """Parse a PDF into PaperPage list, using a persistent cache keyed by file
    identity. The cache turns a ~27s pdfplumber parse into a ~0.05s pickle read."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Source PDF not found: {pdf_path}")
    fingerprint = _pdf_fingerprint(pdf_path)
    cache = _cache_path()
    if fingerprint is not None and cache.exists():
        try:
            stored = pickle.loads(cache.read_bytes())
        except Exception:
            stored = None
        if isinstance(stored, dict) and stored.get("fingerprint") == fingerprint:
            return [PaperPage(p["page"], p["text"]) for p in stored["pages"]]

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for index, page in enumerate(pdf.pages):
            text = page.extract_text(x_tolerance=x_tolerance, y_tolerance=y_tolerance) or ""
            if text.strip():
                pages.append(PaperPage(index + 1, text))
    if not pages:
        raise RuntimeError("The PDF was found, but no readable text could be extracted.")

    if fingerprint is not None:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(pickle.dumps({"fingerprint": fingerprint, "pages": [
                {"page": p.page, "text": p.text} for p in pages
            ]}))
        except OSError:
            pass
    return pages
