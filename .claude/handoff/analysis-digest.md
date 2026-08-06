# Analysis Digest — Antarctic Atlas Optimization

**Date:** 2026-08-06
**Audit:** 6 agents, 553K tokens, 427 tool calls (5 dimension audits + 1 completeness critic)
**Reproduced:** 3 high-severity bugs confirmed against real code (scripts below).

This digest captures the audit findings for any agent continuing this work. Full source of truth:
`C:\Users\Omica\.claude\projects\C--Users-Omica-Desktop-WORK-The-road-of-Geology-antarctic-atlas\5c1b5230-4c60-4255-88f6-694b22d805ec\subagents\workflows\wf_f7cc72fb-e78\journal.jsonl` (one `{"type":"result"}` line per agent) and the optimized plan at `C:\Users\Omica\.claude\plans\graceful-jingling-otter.md`.

---

## Architecture invariants (MUST preserve)

1. `desktop_qt_app.py:60` — `sys.modules.setdefault("desktop_qt_app", sys.modules[__name__])` short-circuits the circular import.
2. `desktop_qt_app.py:3662-3686` — imports `qt_app.pages.*`, then `setattr`s every `_`-prefixed callable onto `NativeAtlasWindow`. The six `qt_app/pages/*.py` are **mixin method-modules** (each opens `from desktop_qt_app import *`), NOT independent widgets.

## The 3 reproduced bugs

1. **`build_search_excerpt` self-corrupting highlight** — `core/paper.py:34-56`. Per-keyword `re.sub` loop rewrites inside previously-inserted `<span>` markup when a keyword is a substring of the markup (e.g. `color`, `span`, `style`). Repro:
   ```python
   build_search_excerpt("The color of the sea level rise.", ["sea level", "level", "color"])
   ```
   → 10 nested `<span>`. Fix: single-pass alternation regex (matches consumed left-to-right, never rescans). Same bug in `atlas_app/paper.py:72-79`.

2. **zh-mode ` For ` corruption** — `qt_app/i18n.py:438` `text.replace(" For ", " 对于 ")` runs unconditionally in `_clean_translation`, corrupting raw paper text (`translate_text("The shelf thins. For example, CDW drives basal melting.")` → "对于 example"). Also lines 439-440 (`> For <`, `> For `). `i18n.py` imports only stdlib (json/os/re/pathlib/copy) — testable headlessly. Fix: delete the bare rules; keep `"Synthesis: For "` (line 435).

3. **Chinese search broken** — `core/paper.py:30-31,101-123`. `re.findall(r"[\w-]+", query)` — `\w` matches CJK, so a Chinese query becomes one token that never matches English text. Repro: `search_pages(pages, "接地线后退")` → `[]`. Fix: CJK-aware tokenizer using jieba (already imported in `core/paper.py:5`).

## Top structural findings

- **Triplicated AI backend logic** (~1068 lines): `atlas_app/ai.py` (408) + `qt_app/pages/research_universe.py:397-695` (`_test/_call/_stream/_classify_universe_backend_*`) + frozen copy in `dist/`. OpenAI path in research_universe falls through to non-streaming (`:646-658`) — UX divergence. `atlas_app/ai.py:24` `check_ollama` uses exact-name match → silent failure on model-name drift.
- **Triplicated paper search/PDF logic**: `core/paper.py` (new, `<span>` highlight), `atlas_app/paper.py` (old, `<mark>` highlight + divergent `extract_keywords` + pages-1-5 fallback), `desktop_qt_app.py:122-134` `load_pdf_pages`.
- **Duplicated data**: `DIRECTION_DATA` `desktop_qt_app.py:295-457` == `atlas_app/pages/research_directions.py:181-315`; `SYSTEM_LAYERS/CASES/PROCESSES` `desktop_qt_app.py:961-1290` == `atlas_app/pages/antarctic_system.py`; research-universe HTML template byte-dup between `atlas_app/pages/research_universe.py:413-833` and `qt_app/legacy_templates/research_universe_template.html`.
- **PDF parsed every launch**: `load_pdf_pages` runs pdfplumber on 89 pages (~27s) with zero cache, gating the landing Enter button.
- **Tests couple to monolith**: `tests/test_core.py:17-29` imports from `desktop_qt_app` (drags Qt into pytest).
- **Tooling drift**: unpinned `requirements.txt` (pywebview/pandas/plotly/numpy unused by desktop path); untracked `Antarctic Atlas ZH.spec` bundles retired streamlit/atlas_app/app.py; EN .iss v3.1.3 vs CHANGELOG v3.1.2 vs ZH .iss v2.0.23; `build/`, `.claude/`, `db/` not gitignored.

## Confirmed dead code (grep-verified)

- `UniverseMapWidget` `desktop_qt_app.py:511-889` + `UniverseBridge` `:892-899` — never instantiated (page uses `OriginalUniverseWebWidget`).
- `_on_shell_changed` `desktop_qt_app.py:3107-3108` — no-op.
- `_build_universe_answer`/`_finish_universe_answer` `research_universe.py:698,1111` — no callers (all paths stream).
- `desktop_qt_app.py:11-12` — `requests` + `jieba` imported at module scope, unused by the monolith body (re-exported for pages).

## Cross-thread Qt bug

`research_universe.py:483-492` `_universe_api_key` reads `self.universe_api_key.text()` from inside `FunctionWorker`/`StreamWorker` (worker thread) — undefined behavior, crash risk on widget deletion. Fix: snapshot `api_key` on GUI thread before starting the worker.

## Recommended next work (out of this session's scope)

1. Convert the six method-mixin page modules into real `QWidget` subclasses (keystone; ~3700-line risk; do AFTER core/ai.py extraction so it operates against a stable AI client).
2. Collapse the three i18n mechanisms (t() 22-key locale files, translate_text vs 1157-key zh_auto.json + ~250-entry `_MANUAL_ZH` dict in i18n.py:37-304, inline `_u_text` pairs) into one; remove the `QPainter.drawText` monkey-patch (i18n.py:640-643) from the 120fps paint path.
3. CI workflow; git tags for v2.0.6–v3.1.1; `pyproject.toml` with `python -m` entry points.
