"""
Tests for Antarctic Atlas i18n text handling (zh-mode translation safety).

Run: python -m pytest tests/ -v
"""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="module")
def zh_locale():
    os.environ["ATLAS_LOCALE"] = "zh"
    from qt_app import i18n

    i18n.set_locale("zh")
    return i18n


def test_zh_does_not_corrupt_english_for_sentences(zh_locale):
    """Regression: bare ' For ' replacement corrupted raw paper text."""
    text = "The shelf thins. For example, CDW drives basal melting."
    out = zh_locale.translate_text(text)
    assert "For example" in out
    assert "For the Amundsen Sea" in zh_locale.translate_text(
        ". For the Amundsen Sea, warm water intrudes."
    )


def test_zh_synthesis_card_keeps_duiyu(zh_locale):
    """The 'Synthesis: For ...' card template must translate to 综合判断：对于."""
    out = zh_locale.translate_text("Synthesis: For the grounding line, retreat accelerates.")
    assert "综合判断：对于" in out
    plain = zh_locale.translate_text("Synthesis: basal melting drives ice loss.")
    assert "综合判断： basal melting" in plain


def test_zh_exact_map_still_applies(zh_locale):
    out = zh_locale.translate_text("AI Backend")
    assert out  # translated (not empty), exact map applies


def test_zh_does_not_corrupt_title_case_words_in_prose(zh_locale):
    """Regression: bare title-case word replacements ('Compass', 'OBSERVATION', ...)
    corrupted arbitrary English prose the same way the removed ' For ' rule did."""
    for sentence in [
        "Compass shows the direction of ice flow.",
        "Timeline reveals the sequence of collapse.",
        "Key gap in the record is the ice-core interval.",
        "He wrote that OBSERVATION is important.",
        "The RESULT of the experiment was clear.",
    ]:
        assert zh_locale.translate_text(sentence) == sentence


def test_zh_standalone_labels_still_translate(zh_locale):
    """Standalone words still translate through the exact-map match."""
    assert zh_locale.translate_text("Compass") == "罗盘"
    assert zh_locale.translate_text("Key gap") == "关键缺口"
    assert zh_locale.translate_text("OBSERVATION") == "观测"
    assert zh_locale.translate_text("Altimetry") == "测高"
