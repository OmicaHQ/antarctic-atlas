"""
Tests for Antarctic Atlas core logic — paper search, keyword extraction,
reference-page filtering, and answer cleaning.

Run: python -m pytest tests/ -v
"""

import json
import pickle
import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.models import PaperPage
from core.paper import (
    build_search_excerpt,
    clean_answer_markdown,
    clean_text,
    extract_paper_keywords,
    extract_search_window,
    extract_search_keywords,
    is_low_value_reference_page,
    is_overview_question,
    load_pdf_pages,
    reference_section_start,
    scored_search_pages,
    scored_search_pages_by_keywords,
    search_pages,
)

_SPAN_OPEN = "<span style='background-color:#7a5a13; color:#fff7d6; font-weight:700'>"


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def sample_pages() -> list[PaperPage]:
    """Five mock pages simulating Antarctic paper content."""
    return [
        PaperPage(1, "The Antarctic Ice Sheet is the largest ice mass on Earth. "
                      "Understanding its sensitivity to climate change is critical."),
        PaperPage(2, "Circumpolar Deep Water (CDW) intrusion onto the continental shelf "
                      "causes basal melting of ice shelves in the Amundsen Sea."),
        PaperPage(3, "Marine Ice Sheet Instability (MISI) may cause self-sustaining retreat "
                      "on retrograde beds. Grounding line migration is a key control."),
        PaperPage(4, "Satellite altimetry from ICESat-2 shows thinning rates of 5 m/yr "
                      "at Pine Island Glacier. GRACE data confirms mass loss."),
        PaperPage(5, "References: Smith et al. (2018), Journal of Geophysical Research. "
                      "Jones et al. (2019), Geophysical Research Letters. "
                      "Brown et al. (2020), doi:10.1029/example. Wilson et al. (2021). "
                      "Taylor et al. (2017), Geophysical Research Letters. "
                      "Anderson et al. (2019), doi:10.1029/example2. "
                      "Miller et al. (2020), Journal of Geophysical Research. "
                      "Davis et al. (2016), Geophysical Research Letters. "
                      "Garcia et al. (2018), doi:10.1029/example3. "
                      "Martinez et al. (2021), Journal of Geophysical Research. "
                      "Robinson et al. (2019), Geophysical Research Letters. "
                      "Clark et al. (2017), doi:10.1029/example4. "
                      "Lewis et al. (2020), Journal of Geophysical Research. "
                      "Walker et al. (2018), Geophysical Research Letters. "
                      "Hall et al. (2019), doi:10.1029/example5. "
                      "Young et al. (2021), Journal of Geophysical Research. "
                      "Allen et al. (2017), Geophysical Research Letters. "
                      "King et al. (2020), doi:10.1029/example6. "
                      "Wright et al. (2018), Journal of Geophysical Research. "
                      "Scott et al. (2019), Geophysical Research Letters."),
    ]


# ── clean_text ────────────────────────────────────────────

def test_clean_text_collapses_whitespace():
    assert clean_text("hello   world\n\t  foo") == "hello world foo"


def test_clean_text_strips_edges():
    assert clean_text("  \n  hello  \n  ") == "hello"


def test_clean_text_preserves_content():
    assert clean_text("Circumpolar Deep Water") == "Circumpolar Deep Water"


# ── extract_search_keywords ───────────────────────────────

def test_extract_search_keywords_english():
    keywords = extract_search_keywords("basal melt and grounding line retreat")
    assert "basal" in keywords
    assert "melt" in keywords
    assert "grounding" in keywords
    assert "line" in keywords
    assert "retreat" in keywords


def test_extract_search_keywords_ignores_short():
    keywords = extract_search_keywords("a b c ab cd")
    # "a", "b", "c" are length 1 → filtered out
    assert "a" not in keywords
    assert "b" not in keywords
    # "ab", "cd" are length 2 → kept
    assert "ab" in keywords
    assert "cd" in keywords


# ── build_search_excerpt ──────────────────────────────────

def test_build_search_excerpt_finds_keyword():
    text = "The grounding line is the boundary between grounded and floating ice."
    result = build_search_excerpt(text, ["grounding line"])
    assert "grounding" in result
    assert "line" in result


def test_build_search_excerpt_returns_truncated():
    long_text = "x " * 500 + "CDW intrusion" + " x" * 500
    result = build_search_excerpt(long_text, ["CDW"])
    assert len(result) < len(long_text)
    assert "CDW" in result


def test_build_search_excerpt_no_nested_highlight():
    """Keywords that are substrings of the inserted <span> markup must not nest."""
    text = "The color of the sea level rise is rising. Sea level responds to warming color."
    result = build_search_excerpt(text, ["sea level", "level", "color"])
    # Every <span> tag must close; no `<span` may appear inside an open span tag.
    assert result.count("<span") == result.count("</span>")
    assert "<span style" not in result.replace(_SPAN_OPEN, "", 4)
    # Each occurrence is wrapped exactly once.
    assert result.count(_SPAN_OPEN) == 4


def test_build_search_excerpt_escapes_html():
    """Raw HTML in source text must be escaped; keyword match is highlighted once."""
    result = build_search_excerpt("CDW <b>intrudes</b> onto <tag> the shelf", ["CDW", "shelf"])
    assert "<b>" not in result
    assert "&lt;b&gt;" in result
    assert result.count("<span") == result.count("</span>")


def test_build_search_excerpt_mark_highlight():
    result = build_search_excerpt("CDW drives basal melt", ["CDW"], highlight="mark")
    assert result == "<mark>CDW</mark> drives basal melt"


def test_extract_search_window_returns_plain_text_from_densest_match_cluster():
    text = (
        "How is basal forcing represented? "
        + "background material " * 40
        + "Grounding line retreat accelerates when basal melt removes ice-shelf support."
    )
    result = extract_search_window(
        text,
        ["how", "basal", "grounding line", "retreat", "basal melt", "ice-shelf"],
        radius=90,
    )
    assert "Grounding line retreat" in result
    assert "basal melt" in result
    assert "<span" not in result


def test_extract_search_window_falls_back_to_page_start_without_a_match():
    result = extract_search_window("alpha beta gamma delta", ["missing"], radius=6)
    assert result == "alpha beta g..."


# ── search_pages ──────────────────────────────────────────

def test_search_pages_finds_match(sample_pages):
    results = search_pages(sample_pages, "CDW intrusion")
    assert len(results) > 0
    # Page 2 should be the top match (contains "CDW")
    assert results[0].page == 2


def test_search_pages_no_match_returns_empty(sample_pages):
    results = search_pages(sample_pages, "zzz_nonexistent_term_zzz")
    assert results == []


def test_search_pages_respects_max_results(sample_pages):
    results = search_pages(sample_pages, "ice sheet", max_results=2)
    assert len(results) <= 2


def test_search_pages_chinese_query_matches_english(sample_pages):
    """A Chinese query must be jieba-segmented and expanded via CHINESE_PAPER_KEYWORDS
    to match the English paper text."""
    results = search_pages(sample_pages, "接地线后退")
    assert len(results) > 0
    # Page 3 discusses grounding line migration.
    assert results[0].page == 3


def test_extract_search_keywords_chinese_expands():
    keywords = extract_search_keywords("冰架融化")
    assert "ice shelf" in keywords
    assert "basal melt" in keywords
    assert "melt" in keywords


# ── scored_search_pages ───────────────────────────────────

def test_scored_search_pages_returns_sorted(sample_pages):
    results = scored_search_pages(sample_pages, "ice")
    assert len(results) > 0
    # Results sorted by score descending
    scores = [score for score, _ in results]
    assert scores == sorted(scores, reverse=True)


# ── is_low_value_reference_page ───────────────────────────

def test_is_low_value_reference_page_detects_references():
    ref_page = ("References: Smith et al. (2018), Journal of Geophysical Research. "
                "Jones et al. (2019), Geophysical Research Letters. "
                "Brown et al. (2020), doi:10.1029/example. Wilson et al. (2021). "
                "Taylor et al. (2017), Geophysical Research Letters. "
                "Anderson et al. (2019), doi:10.1029/example2.")
    assert is_low_value_reference_page(ref_page) is True


def test_is_low_value_reference_page_passes_science():
    science_page = "The grounding line retreat is driven by ocean-induced basal melting."
    assert is_low_value_reference_page(science_page) is False


def test_reference_classifier_keeps_citation_rich_review_prose():
    science_page = " ".join(
        f"Study {year} by Smith et al. supports grounding-line retreat in the scientific discussion."
        for year in range(1990, 2022)
    )
    assert is_low_value_reference_page(science_page) is False


def test_reference_section_start_keeps_mixed_heading_page_and_excludes_tail():
    dense_references = "\n".join(
        f"Author, A. ({year}). Ice study. https://doi.org/10.1000/{year}"
        for year in range(1990, 2000)
    )
    pages = [
        PaperPage(1, "Grounding line science."),
        PaperPage(2, "More grounding line evidence."),
        PaperPage(3, "Glossary material\nThis review was prepared at a References"),
        PaperPage(4, dense_references),
        PaperPage(5, "Tail, T. (2020). Grounding line. https://doi.org/10.1000/tail"),
    ]
    assert reference_section_start(pages) == 4
    assert [page.page for page in search_pages(pages, "grounding line")] == [1, 2]
    assert 5 in [
        page.page
        for page in search_pages(pages, "grounding line", include_references=True)
    ]


def test_bundled_paper_reference_boundary_and_match_window(tmp_path, monkeypatch):
    from config import PDF_PATH

    monkeypatch.setattr("core.paper._cache_path", lambda: tmp_path / "real-paper-cache.json")
    pages = load_pdf_pages(PDF_PATH)
    by_number = {page.page: page for page in pages}

    assert len(pages) == 89
    assert reference_section_start(pages) == 64
    assert is_low_value_reference_page(by_number[60].text) is False
    assert is_low_value_reference_page(by_number[63].text) is False
    assert is_low_value_reference_page(by_number[64].text) is True
    assert len([page for page in pages if page.page >= reference_section_start(pages)]) == 26

    window = extract_search_window(
        by_number[10].text,
        ["how", "does", "basal", "melting", "basal melt", "ice shelf", "ocean heat"],
        radius=220,
    )
    assert "basal" in window.lower()
    assert all(page.page < 64 for _, page in scored_search_pages(pages, "grounding line"))


# ── is_overview_question ──────────────────────────────────

def test_is_overview_question_detects_summary():
    assert is_overview_question("Can you summarize the paper?") is True
    assert is_overview_question("这篇论文讲了什么？") is True


def test_is_overview_question_passes_specific():
    assert is_overview_question("What is the basal melt rate at Thwaites?") is False


# ── clean_answer_markdown ─────────────────────────────────

def test_clean_answer_markdown_removes_page_refs():
    dirty = "The ice sheet is melting. (Page 42) This is critical.  (page 15)"
    clean = clean_answer_markdown(dirty)
    assert "Page 42" not in clean
    assert "page 15" not in clean


def test_clean_answer_markdown_collapses_newlines():
    dirty = "Line one\n\n\n\nLine two"
    clean = clean_answer_markdown(dirty)
    assert "\n\n\n\n" not in clean


# ── extract_paper_keywords ────────────────────────────────

def test_extract_paper_keywords_chinese():
    keywords = extract_paper_keywords("冰架融化导致海平面上升")
    # jieba should segment Chinese text
    assert len(keywords) > 0
    assert "冰架" in keywords or "融化" in keywords


def test_extract_paper_keywords_english_mixed():
    keywords = extract_paper_keywords("CDW intrusion onto continental shelf")
    assert "cdw" in keywords
    assert "intrusion" in keywords


# ── scored_search_pages_by_keywords ───────────────────────

def test_scored_search_by_keywords(sample_pages):
    results = scored_search_pages_by_keywords(sample_pages, ["cdw", "basal melt"])
    assert len(results) > 0
    # Page 2 should rank highest (has both CDW and basal melt)
    assert results[0][1].page == 2


def test_scored_search_by_keywords_excludes_references(sample_pages):
    """Evidence search should omit the detected reference section."""
    results = scored_search_pages_by_keywords(sample_pages, ["journal", "geophysical"])
    assert all(page.page != 5 for _, page in results)


# ── load_pdf_pages / cache ────────────────────────────────

class _FakeTextPage:
    def __init__(self, text):
        self._text = text

    def extract_text(self, x_tolerance=None, y_tolerance=None):
        return self._text


class _FakePDF:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakePDFPlumber:
    def __init__(self):
        self.open_count = 0

    def open(self, path):
        self.open_count += 1
        return _FakePDF([_FakeTextPage("CDW intrusion"), _FakeTextPage("Basal melt")])


def _write_pickle_marker(path):
    Path(path).write_text("pickle executed", encoding="utf-8")


class _UnsafePicklePayload:
    def __init__(self, marker):
        self.marker = str(marker)

    def __reduce__(self):
        return _write_pickle_marker, (self.marker,)


def test_load_pdf_pages_cache_roundtrip(tmp_path, monkeypatch):
    """load_pdf_pages must return PaperPage list and populate the cache so the
    next call skips pdfplumber (verified by reading the cache file)."""
    cache_file = tmp_path / "pages.json"
    monkeypatch.setattr("core.paper._cache_path", lambda: cache_file)

    pdf = tmp_path / "fake.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    fake_pdf = _FakePDFPlumber()
    monkeypatch.setattr("core.paper.pdfplumber", fake_pdf)

    pages = load_pdf_pages(pdf)
    assert [p.page for p in pages] == [1, 2]
    assert pages[0].text == "CDW intrusion"
    assert fake_pdf.open_count == 1

    # Cache written and keyed by fingerprint.
    assert cache_file.exists()
    stored = json.loads(cache_file.read_text(encoding="utf-8"))
    assert stored["version"] == 1
    assert stored["fingerprint"] is not None
    assert stored["pages"][0]["text"] == "CDW intrusion"

    # Second call must hit the persistent cache — pdfplumber must NOT be
    # invoked again (open_count stays 1).
    assert load_pdf_pages(pdf)[0].text == "CDW intrusion"
    assert fake_pdf.open_count == 1


def test_default_paper_cache_path_uses_safe_json_format():
    from core.paths import paper_cache_path

    assert paper_cache_path().name == "pages.json"


def test_load_pdf_pages_ignores_unsafe_pickle_cache(tmp_path, monkeypatch):
    cache_file = tmp_path / "pages.json"
    marker = tmp_path / "pickle-executed"
    cache_file.write_bytes(pickle.dumps(_UnsafePicklePayload(marker)))
    monkeypatch.setattr("core.paper._cache_path", lambda: cache_file)
    fake_pdf = _FakePDFPlumber()
    monkeypatch.setattr("core.paper.pdfplumber", fake_pdf)
    pdf = tmp_path / "fake.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    assert load_pdf_pages(pdf)[0].text == "CDW intrusion"
    assert fake_pdf.open_count == 1
    assert not marker.exists()
    assert json.loads(cache_file.read_text(encoding="utf-8"))["version"] == 1


def test_load_pdf_pages_rebuilds_structurally_invalid_json_cache(tmp_path, monkeypatch):
    from core.paper import _pdf_fingerprint

    cache_file = tmp_path / "pages.json"
    monkeypatch.setattr("core.paper._cache_path", lambda: cache_file)
    fake_pdf = _FakePDFPlumber()
    monkeypatch.setattr("core.paper.pdfplumber", fake_pdf)
    pdf = tmp_path / "fake.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    cache_file.write_text(json.dumps({
        "version": 1,
        "fingerprint": _pdf_fingerprint(pdf),
        "x_tolerance": 1.5,
        "y_tolerance": 3.0,
        "pages": [{"page": 1}],
    }), encoding="utf-8")

    assert load_pdf_pages(pdf)[0].text == "CDW intrusion"
    assert fake_pdf.open_count == 1
    assert json.loads(cache_file.read_text(encoding="utf-8"))["pages"][0]["text"] == "CDW intrusion"


def test_load_pdf_pages_missing_pdf_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_pdf_pages(tmp_path / "nope.pdf")
