# Handover Log — Antarctic Atlas Technical Optimization

**Date:** 2026-08-06
**Status:** All 5 phases of the approved optimization plan are complete.
**For:** Any agent or human continuing work on this project.

---

## What was done (per file)

### Phase 1 — Bug fixes (3 high-severity bugs reproduced + fixed)

- **`core/paper.py`** — `build_search_excerpt` no longer self-corrupts: replaced the per-keyword `re.sub` loop with a single-pass alternation regex that never rescans inserted markup. Added `highlight` param (`"span"` desktop default, `"mark"` for the web app).
- **`qt_app/i18n.py`** — removed the bare `" For " → " 对于 "` replacements that corrupted English prose in zh mode. Added a `"Synthesis: For "` guard so the card template still translates to `综合判断：对于`.
- **`core/paper.py`** — Chinese search fixed: queries are jieba-segmented (`_tokenize_query`) and expanded via `CHINESE_PAPER_KEYWORDS` so e.g. `"接地线后退"` matches the English grounding-line pages.

### Phase 2 — `core/ai.py`: single dependency-free AI client

- **`core/ai.py` (new)** — one client for Ollama/DeepSeek/OpenAI: `chat`, `test_connection`, `classify`, payload builders, response parsers (`extract_openai_text`, `extract_backend_text`). Zero Qt/Streamlit imports; runs on any thread.
- **`atlas_app/ai.py`** — thin wrapper: keeps Streamlit-only bits (st.secrets/st.session_state key lookup, widget-drawing stream helpers, classifier wrappers), re-exports the shared client from `core.ai`.
- **`qt_app/pages/research_universe.py`** — `_call/_stream/_classify_universe_backend_text` are now thin wrappers over `core.ai.chat`/`classify`. **Cross-thread fix:** backend/model/API-key are snapshotted on the GUI thread before workers start (`FunctionWorker`/`StreamWorker` no longer read Qt widgets). Fixed the OpenAI non-streaming fall-through divergence as a side effect.

### Phase 3 — Search/PDF/data consolidation into `core/`

- **`core/paper.py`** — added `load_pdf_pages(pdf_path, x_tolerance, y_tolerance)` with a **persistent PDF text cache** at `%APPDATA%/AntarcticAtlas/pages.pkl` keyed by file size+mtime. **Measured: 30.5s cold parse → 0.019s warm cache (~1648x speedup)**. This kills the startup PDF-parse block.
- **`core/data.py` (new)** — bundle-aware `load_data_json`/`data_dir`/`resource_path` shared by both apps.
- **`atlas_app/paper.py`** — thin Streamlit shim over `core.paper`: keeps `load_pdf()` (`@st.cache_data`, `list[dict]` shape), legacy `search_pages` pages-1-5 fallback, and `<mark>` highlight via `highlight="mark"`.
- **`desktop_qt_app.py`** — now imports `load_pdf_pages`/`load_data_json`/`resource_path` from `core`; removed the duplicated local copies and the `pdfplumber`/`PaperPage` imports.

### Phase 4 — Repo hygiene + tooling

- **`.gitignore`** — added `/build/`, `/.pytest-tmp/`, `/tests/.pytest-tmp/`.
- **`requirements.txt`** — pinned exact versions; removed retired `pywebview`; split legacy Streamlit demo deps (streamlit/pandas/plotly/numpy) from desktop runtime deps.
- **`Antarctic Atlas.spec`** — dropped retired `pandas`/`numpy`/`PIL`/`plotly` hiddenimports and the `collect_all('plotly')` bundle (desktop path doesn't use plotly).
- **`Antarctic Atlas ZH.spec`** — removed the retired `app.py`/`atlas_app`/`streamlit` bundling (and the `collect_all('streamlit'/'plotly')`), added `data/`, aligned with the EN spec.
- **`installer/AntarcticAtlasSetup.iss`** — version corrected 3.1.3 → 3.1.2 (CHANGELOG's latest release).
- **`installer/AntarcticAtlasSetup.zh.iss`** — version aligned to 3.1.2; added `[InstallDelete]` cleanup of retired Streamlit leftovers.
- **`CHANGELOG.md`** — added v3.1.3 entry.
- **`tests/test_core.py`** — imports already pointed at `core.*`; added PDF-cache regression tests.
- **`pytest.ini`** + **`tests/conftest.py`** — work around a permission-locked system temp dir on Windows by forcing a project-local `.pytest-tmp` temp root.

### Phase 5 — Dead code removal + verification + this log

- **`qt_app/pages/research_universe.py`** — removed `_extract_universe_test_text`, `_build_universe_answer`, `_finish_universe_answer`, `_start_universe_answer_typewriter`, `_tick_universe_answer_typewriter` (all unreferenced; the streaming path `_stream_universe_answer`/`_finish_universe_stream_answer` replaced them).
- **`desktop_qt_app.py`** — removed `UniverseMapWidget` (381 lines, never instantiated — the page uses `OriginalUniverseWebWidget`) and the `_on_shell_changed` no-op plus its signal connection.

---

## Verification (all green)

```
python -m pytest tests/ -q        → 31 passed
python -m compileall -q app.py desktop_qt_app.py atlas_app qt_app core   → OK
python -c "import core.ai, core.data, core.paper"                        → imports headlessly (no Qt/Streamlit)
python -c "import desktop_qt_app"  → imports headlessly (Qt classes only constructed in main())
```

The three bug repro scripts now show clean output (balanced `<span>` tags, intact "For example", Chinese query matching the grounding-line page).

**Known caveat:** I could not launch the GUI window (headless session) — the manual step `python desktop_qt_app.py` should be done once to confirm the landing page renders and the Research Universe tab works end-to-end.

---

## Independent regression review (6-agent workflow) — 5 confirmed defects, all fixed

After the main pass, a 6-dimension multi-agent review (refactor-correctness, api-compat, threading-qt, i18n, packaging-tooling, tests-coverage) with adversarial verification found 5 real defects. **All 5 are fixed and verified; 2 claims were refuted (no change needed).**

1. **`core/data.py` `resource_path` repo-root regression (CRITICAL)** — when moved from `desktop_qt_app.py`, `Path(__file__).resolve().parent` resolved to `core/`, so `resource_path("qt_app", ...)`/`resource_path("antarctic_atlas.ico")` returned non-existent paths. The Research Universe default page (template read) failed → landing showed "Atlas preparation failed" and `_main_ready` stayed False. **Fixed:** bases are now `_MEIPASS` / `_internal` / `_PROJECT_ROOT` (repo root); `core/` is no longer a base. Verified headless: template + icon resolve, `_main_ready=True` after the deferred init chain.
2. **`qt_app/i18n.py` bare title-case word replacement (same class as the " For " bug)** — the `_clean_translation` loop replaced `OBSERVATION`/`RESULT`/`Compass`/`Timeline`/`Key gap`/`Region map`/`Proposal builder`/`Beginner-researcher angle` anywhere in zh-mode text ("Compass shows the direction..." → "罗盘 shows the direction..."). Standalone labels still translate via the exact-map path, so the loop was redundant AND harmful. **Fixed:** removed the loop; added regression tests `test_zh_does_not_corrupt_title_case_words_in_prose` + `test_zh_standalone_labels_still_translate`.
3. **`atlas_app/ai.py` Ollama model regression** — `_stream_into_widget` passed `get_selected_openai_model()` (default `gpt-4o`) as the Ollama model → Ollama 404. **Fixed:** explicit backend branch; Ollama passes `model=None` so `core.ai.chat` falls back to `OLLAMA_MODEL`.
4. **`core/ai.py` `check_ollama` semantic change** — refactor changed `OLLAMA_MODEL in model_names` (exact) to `bool(model_names)` (any model). The Streamlit page's "connected" message names `OLLAMA_MODEL`, so tolerant semantics falsely reported connected. **Fixed:** restored exact-name match.
5. **PDF-cache test didn't assert the fast path** — `FakePDFPages.open` couldn't distinguish cache-hit from re-parse; deleting the cache-hit return passed the test. **Fixed:** added an `open_count`; the second call now asserts `open_count == 1`.

**Refuted (verified harmless, no change):** the `build_search_excerpt` no-nesting test (alternation semantics guarantee no overlap; count=4 is robust) and the `test_zh_synthesis_card_keeps_duiyu` regression test (it does catch the regression).

Tests now: **33 passed** (was 31). Offscreen GUI verified end-to-end: window + default page + deferred init all succeed.

---

## Architecture invariants (MUST preserve)

1. `desktop_qt_app.py` — `sys.modules.setdefault("desktop_qt_app", sys.modules[__name__])` short-circuits the circular import between the main module and `qt_app/pages/*.py`. Do not reorder imports before this line.
2. `desktop_qt_app.py` near the bottom — imports `qt_app.pages.*`, then `setattr`s every `_`-prefixed callable onto `NativeAtlasWindow`. The six `qt_app/pages/*.py` are **mixin method-modules** (each opens `from desktop_qt_app import *`), NOT independent widget classes.

## Recommended next work (out of scope for this pass)

1. **Convert the six method-mixin page modules into real `QWidget` subclasses** — the ~3700-line monolith's biggest structural win, but high risk; needs manual UI verification after.
2. **Collapse the three i18n mechanisms** (22-key locale files, 1157-key zh_auto.json exact map, ~250-entry `_MANUAL_ZH` dict in `qt_app/i18n.py`) into one, and remove the `QPainter.drawText` monkey-patch. Large behavioral surface.
3. **`data/` is now runtime-critical but untracked in git** — commit `data/*.json` (topics.json, research_areas.json, keywords.json) so a fresh clone / CI can build the installer. The EN spec already bundles `data/`; the ZH spec now does too.
4. **Retire `desktop_app.py`** — the old pywebview shell (still imports `webview`), plus `pywebview` from requirements (already removed). Keep the file as reference or delete; it's not in any build.
5. **CI workflow + git tags** — none exist yet.
6. **PDF cache invalidation** is by file size+mtime. If the bundled PDF changes without a size/mtime change (rare), the stale cache persists until `%APPDATA%/AntarcticAtlas/pages.pkl` is deleted.

## Where the full 6-agent audit lives

`C:\Users\Omica\Desktop\WORK\The road of Geology\antarctic-atlas\.claude\handoff\analysis-digest.md` and the workflow journal at
`C:\Users\Omica\.claude\projects\C--Users-Omica-Desktop-WORK-The-road-of-Geology-antarctic-atlas\5c1b5230-4c60-4255-88f6-694b22d805ec\subagents\workflows\wf_f7cc72fb-e78\journal.jsonl`
(one `{"type":"result"}` line per agent).
