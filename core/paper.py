"""Core paper search and text processing with no interface dependencies."""
import hashlib
import html
import json
import os
import re
from pathlib import Path

import jieba
import pdfplumber

from .models import PaperPage
from .paths import paper_cache_path

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
_CACHE_VERSION = 1
_REFERENCE_HEADING_RE = re.compile(r"^\s*(?:references|bibliography)\s*(?::|$)", re.IGNORECASE)
_REFERENCE_TRAILING_HEADING_RE = re.compile(r"\b(?:references|bibliography)\s*$", re.IGNORECASE)
_REFERENCE_YEAR_RE = re.compile(r"\((?:18|19|20)\d{2}[a-z]?\)\s*[.,]", re.IGNORECASE)
_REFERENCE_DOI_RE = re.compile(r"(?:https?://)?doi\.org/|\bdoi\s*:", re.IGNORECASE)


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


def _normalized_keywords(keywords: list[str]) -> list[str]:
    normalized = []
    for keyword in keywords:
        cleaned = clean_text(str(keyword)).lower()
        if cleaned:
            normalized.append(cleaned)
    return sorted({keyword for keyword in normalized if len(keyword) > 1}, key=len, reverse=True)


def _match_window_bounds(text: str, keywords: list[str], radius: int) -> tuple[int, int]:
    """Choose the text window containing the densest cluster of keyword hits."""

    if not text:
        return 0, 0
    radius = max(1, int(radius))
    lowered = text.lower()
    occurrences: list[tuple[int, int, int]] = []
    for keyword in _normalized_keywords(keywords):
        weight = 3 if re.search(r"[\s-]", keyword) else 1
        for match in re.finditer(re.escape(keyword), lowered):
            occurrences.append((match.start(), match.end(), weight))
    if not occurrences:
        return 0, min(len(text), radius * 2)

    best_key = None
    best_bounds = (0, min(len(text), radius * 2))
    for hit_start, hit_end, hit_weight in occurrences:
        center = (hit_start + hit_end) // 2
        start = max(0, center - radius)
        end = min(len(text), center + radius)
        density = sum(
            weight
            for occurrence_start, occurrence_end, weight in occurrences
            if occurrence_start < end and occurrence_end > start
        )
        key = (density, hit_weight, -start)
        if best_key is None or key > best_key:
            best_key = key
            best_bounds = (start, end)
    return best_bounds


def extract_search_window(text: str, keywords: list[str], radius: int = 220) -> str:
    """Return a plain-text excerpt centered on the strongest match cluster."""

    cleaned = clean_text(text)
    start, end = _match_window_bounds(cleaned, keywords, radius)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(cleaned) else ""
    return prefix + cleaned[start:end] + suffix


def build_search_excerpt(text: str, keywords: list[str], radius: int = 220, highlight: str = "span") -> str:
    escaped = html.escape(extract_search_window(text, keywords, radius=radius))
    open_tag, close_tag = _highlight_tags(highlight)
    keywords = _normalized_keywords(keywords)
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


def _reference_heading_kind(text: str) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    for line in lines:
        if re.fullmatch(r"(?:references|bibliography)\s*:?", line, re.IGNORECASE):
            return "exact"
        if _REFERENCE_HEADING_RE.match(line):
            return "exact"
    if any(_REFERENCE_TRAILING_HEADING_RE.search(line) for line in lines):
        return "trailing"
    return ""


def _reference_density(text: str) -> tuple[int, int, float]:
    lines = [line.strip() for line in str(text or "").splitlines() if len(line.strip()) > 3]
    if not lines:
        return 0, 0, 0.0
    doi_count = len(_REFERENCE_DOI_RE.findall(str(text or "")))
    entry_lines = sum(bool(_REFERENCE_YEAR_RE.search(line)) for line in lines)
    return doi_count, entry_lines, entry_lines / len(lines)


def _is_dense_reference_page(text: str) -> bool:
    doi_count, entry_lines, entry_ratio = _reference_density(text)
    return doi_count >= 5 and entry_lines >= 5 and entry_ratio >= 0.18


def is_low_value_reference_page(text: str) -> bool:
    """Classify a page without mistaking citation-rich review prose for references."""

    return _reference_heading_kind(text) == "exact" or _is_dense_reference_page(text)


def reference_section_start(pages: list[PaperPage]) -> int | None:
    """Return the first pure-reference PDF page number, if one is detected.

    Detection is sequential so the final short tail page remains excluded once
    a References section starts. A mixed two-column heading page is retained and
    the first dense page after it becomes the boundary.
    """

    if not pages:
        return None
    search_from = len(pages) // 3
    for index in range(search_from, len(pages)):
        page = pages[index]
        heading_kind = _reference_heading_kind(page.text)
        current_dense = _is_dense_reference_page(page.text)
        next_dense = index + 1 < len(pages) and _is_dense_reference_page(pages[index + 1].text)
        if heading_kind == "exact":
            return page.page
        if heading_kind == "trailing" and next_dense:
            return pages[index + 1].page
        if current_dense and (next_dense or index == len(pages) - 1):
            return page.page
    return None


def _searchable_pages(
    pages: list[PaperPage], *, include_references: bool = False
) -> list[PaperPage]:
    if include_references:
        return pages
    boundary = reference_section_start(pages)
    if boundary is None:
        return pages
    return [page for page in pages if page.page < boundary]


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


def search_pages(
    pages: list[PaperPage],
    query: str,
    max_results: int = 12,
    *,
    include_references: bool = False,
) -> list[PaperPage]:
    keywords = _query_keywords(query)
    if not keywords:
        return []
    results = []
    for page in _searchable_pages(pages, include_references=include_references):
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
    for page in _searchable_pages(pages):
        lowered = page.text.lower()
        score = sum(lowered.count(keyword) for keyword in keywords)
        if score:
            results.append((score, page))
    return sorted(results, key=lambda item: item[0], reverse=True)[:max_results]


def scored_search_pages_by_keywords(
    pages: list[PaperPage], keywords: list[str], max_results: int = 5
) -> list[tuple[float, PaperPage]]:
    normalized = _normalized_keywords(keywords)
    if not normalized:
        return []
    results: list[tuple[float, PaperPage]] = []
    for page in _searchable_pages(pages):
        lowered = page.text.lower()
        score = 0.0
        for keyword in normalized:
            count = lowered.count(keyword)
            if count:
                score += count * (3 if " " in keyword else 1)
        if score:
            results.append((score, page))
    return sorted(results, key=lambda item: item[0], reverse=True)[:max_results]


# ── PDF loading (with persistent text cache) ─────────────────────────────

def _cache_path():
    """Per-user cache file for extracted paper text, keyed by PDF identity."""
    return paper_cache_path()


def _pdf_fingerprint(pdf_path):
    try:
        stat = pdf_path.stat()
        digest = hashlib.sha256()
        with pdf_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return {
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": digest.hexdigest(),
        }
    except OSError:
        return None


def _cached_pages(stored, fingerprint, x_tolerance, y_tolerance):
    if not isinstance(stored, dict) or stored.get("version") != _CACHE_VERSION:
        return None
    if stored.get("fingerprint") != fingerprint:
        return None
    if stored.get("x_tolerance") != x_tolerance or stored.get("y_tolerance") != y_tolerance:
        return None
    raw_pages = stored.get("pages")
    if not isinstance(raw_pages, list) or not raw_pages:
        return None
    pages = []
    previous_page = 0
    for raw_page in raw_pages:
        if not isinstance(raw_page, dict):
            return None
        page_number = raw_page.get("page")
        text = raw_page.get("text")
        if not isinstance(page_number, int) or page_number <= previous_page:
            return None
        if not isinstance(text, str) or not text.strip():
            return None
        pages.append(PaperPage(page_number, text))
        previous_page = page_number
    return pages


def _write_cache(cache: Path, payload: dict) -> None:
    cache.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache.with_name(f".{cache.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, cache)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def load_pdf_pages(pdf_path, x_tolerance=1.5, y_tolerance=3.0):
    """Parse a PDF into PaperPage list, using a persistent cache keyed by file
    identity. The cache turns a full pdfplumber parse into a fast JSON read."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Source PDF not found: {pdf_path}")
    fingerprint = _pdf_fingerprint(pdf_path)
    cache = _cache_path()
    if fingerprint is not None and cache.exists():
        try:
            stored = json.loads(cache.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            stored = None
        cached = _cached_pages(stored, fingerprint, x_tolerance, y_tolerance)
        if cached is not None:
            return cached

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
            _write_cache(cache, {
                "version": _CACHE_VERSION,
                "fingerprint": fingerprint,
                "x_tolerance": x_tolerance,
                "y_tolerance": y_tolerance,
                "pages": [{"page": p.page, "text": p.text} for p in pages],
            })
        except OSError:
            pass
    return pages
