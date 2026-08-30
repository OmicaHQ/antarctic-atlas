# Changelog

All notable changes to Antarctic Research Atlas are documented here.

## Version Line Summary

- `v1`: Original Streamlit research atlas. Established the review-paper exploration product: Research Universe, Antarctic System Explorer, AI Visualizer, Mini Research Lab, Research Compass, and raw-paper access.
- `v2`: Streamlit productization and maintenance phase. Added iOS-style visual polish, Windows installer packaging, Streamlit module splitting, local AI options, and layout fixes while preserving the original app model.
- `v3.0`: Qt desktop reconstruction phase. Rebuilt the experience as a native Qt desktop shell while preserving the original function and UI intent.
- `v3.1`: Unified bilingual desktop phase. Consolidates English and Chinese into one app with in-app switching and broader i18n coverage.
- `v3.2`: Apple Silicon macOS phase. Adds a native arm64 package, macOS paths and assets, reproducible release tooling, and a Mac-focused source tree.

## v3.2.0 - Apple Silicon macOS Support

### Added

- Added a native Apple Silicon (`arm64`) application bundle for macOS 13 or later.
- Added the macOS PyInstaller spec, native `.icns` icon, external-cache development environment, reproducible setup/build scripts, and SHA-256 release artifact.
- Added macOS-native settings and paper-cache locations under the user's Library folders.
- Added source and packaged smoke tests that parse all 89 paper pages and construct all six modules without making an external AI request.

### Fixed

- Fixed nested-highlight corruption in search excerpts: keywords that are substrings of the `<span>` highlight markup (e.g. "color", "span") no longer nest into broken HTML.
- Fixed Chinese-mode corruption of raw paper text: the bare `" For "` → `" 对于 "` translation rule no longer mangles English sentences mid-text.
- Fixed Chinese search: queries are now jieba-segmented and expanded via `CHINESE_PAPER_KEYWORDS`, so e.g. "接地线后退" matches the English grounding-line pages.
- Fixed cross-thread Qt widget access in the Research Universe AI flows: backend/model/API-key are now snapshotted on the GUI thread before workers start.
- Fixed the OpenAI non-streaming fall-through divergence in the Research Universe answer path.

### Changed

- Extracted a single dependency-free AI client (`core/ai.py`) for Ollama, DeepSeek, and OpenAI payload, streaming, and parsing logic.
- Consolidated paper search/PDF into `core/paper.py` and added a persistent cache under `~/Library/Caches/Antarctic Atlas/pages.pkl`.
- Added `core/data.py` with bundle-aware shared JSON and resource loaders.
- Split pinned native runtime and developer dependencies for a smaller, reproducible Mac package.
- Removed Windows installers, Android experiments, legacy Streamlit/web surfaces, screenshots, and generated build material from the active Mac development tree.

### Validation

- 35 automated tests pass.
- The source and packaged applications load all 89 paper pages and construct all six modules.
- The packaged executable is verified as native `arm64`, its ad-hoc signature passes strict verification, and the extracted archive passes a cold-start smoke test.

## v3.1.2 - Chinese AI Answer Streaming Fix

### Fixed

- Fixed a Chinese-locale Research Universe issue where backend connectivity could succeed while the AI answer area stayed in a loading state.
- Restored the Universe answer generation helpers as Qt-bound page methods instead of unreachable nested functions.
- Made generated AI answer language follow the active app language, so Chinese mode answers in Chinese and English mode answers in English.
- Fixed remaining English labels and diagnosis text in the Chinese Mini Research Lab hydrofracture view.

## v3.1.1 - Qt-Only Installer Packaging

### Changed

- Removed the legacy Streamlit app, `atlas_app` page tree, pywebview shell dependency, and Streamlit runtime from the formal Windows installer package.
- Moved the Qt desktop constants from `atlas_app.config` to `qt_app.config`.
- Moved the packaged Research Universe legacy HTML template dependency into `qt_app/legacy_templates/`, so the Qt desktop no longer needs the Streamlit module tree at runtime.
- Kept the Streamlit source in the repository as a legacy web demo and historical reference rather than deleting it.

### Result

- The Windows installer is now a cleaner Qt desktop distribution and should be noticeably smaller than `v3.1.0`.

## v3.1.0 - Unified Bilingual Qt Desktop

### Changed

- Renumbered the current bilingual desktop package as `v3.1.0`.
- Restored distribution to one `Antarctic Atlas` installer with an in-app English / Chinese language selector.
- Persisted language preference in the user settings file so the app reopens in the last selected language.
- Expanded Chinese i18n coverage across Qt widgets, dynamic HTML cards, painter-drawn visual modules, Research Universe labels, story/export text, and status messages.
- Protected provider and scientific terms such as OpenAI, DeepSeek, Ollama, RAG, API, CDW, MISI, MICI, GIA, GRACE, GNSS, and InSAR from incorrect automatic translation.

### Fixed

- Fixed literal `${safe(data.labels...)}` template markers appearing inside the Research Universe hero and hint areas.
- Fixed remaining mixed-language AI Visualizer export text, including `Main message`, `Visual chain`, `Speaker note`, story names, node names, and storyboard table content.
- Fixed several Research Universe dynamic messages that still used English phrasing after switching to Chinese.

## v3.0.15 - Modular Qt Pages and Dual-Language Packaging

Former local version: `v2.0.23`.

### Changed

- Split the Qt desktop page implementations into `qt_app/pages/` modules while keeping the UI behavior stable.
- Added locale-based startup so English and Chinese builds could be produced from the same codebase.
- Added a generated Chinese localization map for Qt desktop page labels, cards, research data, and status text.
- Produced separate English and Chinese installers as an intermediate step before the unified bilingual app.

## v3.0.14 - Fresh Loading Pass

Former local version: `v2.0.22`.

### Changed

- Removed the desktop PDF text cache so every launch performs a fresh paper-loading pass.
- Reverted the experimental landing-page activity animation and kept the simpler progress-to-Enter flow.

## v3.0.13 - AI Retrieval and Desktop Polish

Former local version: `v2.0.21`.

### Changed

- Default DeepSeek API model uses `deepseek-v4-pro` with V4 thinking disabled for cleaner responses.
- Research Universe answers stream from the backend in real time.
- Paper retrieval follows the original app's keyword strategy more closely, including Chinese segmentation and overview-question handling.
- AI answers render as Markdown and the answer area adapts to actual rendered text height.
- Local Ollama connection checks run automatically when selected.
- API keys typed into the field can be used immediately before saving, with a clear unsaved-key prompt.
- The native Qt window sets the custom Antarctic Atlas icon for the title bar.

### Fixed

- Reduced Enter Project transition flash by prebuilding the Universe page before entry.
- Lowered reference-page dominance in broad paper-summary retrieval.

## v3.0.12 - 120Hz Foreground Animation Target

Former local version: `v2.0.20`.

### Changed

- Added a global 120Hz foreground animation target for native Qt animated scenes.
- Switched active animation timers to precise 8ms Qt timers while keeping hidden-page timers paused.
- Made the landing progress timer more responsive under the same high-refresh target.

## v3.0.11 - Performance and AI Status Placement

Former local version: `v2.0.19`.

### Changed

- Reduced desktop jank by lowering always-on animation frequency and pausing animated widgets while their page is hidden.
- Skipped heavy screenshot fade transitions when switching to or from the WebEngine-based Research Universe page.
- Moved AI module-classification and answer-generation progress messages beside the answer progress bar instead of reusing the connection-test status.

## v3.0.10 - Mojibake Repair

Former local version: `v2.0.18`.

### Fixed

- Restored desktop UI symbols that were mojibake-damaged during an encoding rewrite.
- Fixed affected emoji labels, middle dots, degree signs, and time-scale arrows.

## v3.0.9 - Backend Test Repair

Former local version: `v2.0.17`.

### Changed

- Research Universe backend testing freezes the selected backend, model, and key before starting the worker thread.
- Connectivity probes use a clean request and require a readable model reply.

### Fixed

- Fixed Save & Test using unstable UI state from a background thread.
- Fixed corrupted probe text and navigation marker strings that could break desktop startup after editing.

## v3.0.8 - Universe Focus Cleanup

Former local version: `v2.0.16`.

### Fixed

- Removed the remaining automatic Research Universe focus replay when returning to the Universe module.
- Removed an unused delayed Universe focus helper so only user clicks or user questions move the knowledge map.

## v3.0.7 - Interaction Reliability

Former local version: `v2.0.15`.

### Changed

- Landing progress advances with a non-linear heartbeat while the workspace prepares, then completes smoothly before showing Enter Project.
- AI backend testing uses the same short model-request path as real questions and requires a readable reply.
- Module transitions fade a non-interactive screenshot overlay instead of applying opacity effects to the live page.
- Page shells use lighter scroll settings to reduce repaint cost while scrolling.

### Fixed

- Fixed repeated Research Universe questions by isolating each AI classification and answer request with its own worker object and token.
- Fixed Research Universe controls becoming unclickable after returning from other modules by restoring interaction state after navigation.

## v3.0.6 - Flow Polish

Former local version: `v2.0.14`.

### Changed

- Module switching uses a short fade-in transition instead of an abrupt hard cut.
- Landing loading shows a determinate progress bar that advances while the atlas workspace prepares.
- AI backend tests verify that the selected provider returns a readable model response, not only an HTTP 200 status.

### Fixed

- Fixed Research Universe AI answer generation after navigating away and back by safely clearing completed worker references.

## v3.0.5 - Interaction Polish

Former local version: `v2.0.13`.

### Changed

- Returning to Research Universe from another module preserves the existing WebEngine scene instead of reloading the whole map or replaying node focus.
- Research Universe focus changes call the in-page focus bridge after load instead of rebuilding the HTML document.
- The landing page keeps Enter Project hidden while the atlas workspace is preparing, with clearer loading feedback.
- AI backend status uses inline color states: green for verified, blue for testing, red for failed or missing credentials.
- Rounded-corner polish covers more desktop controls, lists, trees, inputs, scrollbars, sliders, disabled buttons, and dropdown popups.

## v3.0.4 - Desktop Polish

Former local version: `v2.0.12`.

### Changed

- The Qt shell shows the landing page first and prepares the atlas workspace immediately after launch.
- Research Universe uses a dark WebEngine loading background and prewarmed main view to reduce white flash after Enter Project.
- API key testing keeps the entered key visible and reports success or failure inline.
- Qt desktop panels, controls, evidence cards, and scrollbars use softer iOS-style rounded corners.

## v3.0.3 - AI Module Matching

Former local version: `v2.0.11`.

### Changed

- In AI backend mode, Research Universe questions are classified by the selected AI model before the map jumps to a knowledge module.
- Model and backend selection surfaces explicit connection states: not configured, not tested, testing, connected, or failed.

### Fixed

- Added a clear success prompt when API-key or local-model connection tests pass.

## v3.0.2 - Qt Usability Fixes

Former local version: `v2.0.10`.

### Changed

- Let Research Universe use its own default state instead of forcing an initial focus from the Qt shell.
- Made AI answer generation and API-key connection tests run in the background so the Universe search UI stays responsive.

### Fixed

- Added immediate feedback when API keys are saved from the Qt Research Copilot.
- Clipped the Antarctic System sensor scene so animated tool graphics stay inside their frame.

## v3.0.1 - Installer Hotfix

Former local version: `v2.0.9`.

### Fixed

- Fixed bundled Qt desktop startup by resolving Research Universe source assets from PyInstaller's internal resource directory.

## v3.0.0 - First Qt Desktop Reconstruction

Former local version: `v2.0.8`.

### Changed

- Switched Windows packaging entry point to the Qt desktop preview.
- Recreated the original app's major pages in a native Qt desktop shell.
- Connected the Qt Research Copilot to real Local Ollama, DeepSeek API, and OpenAI API answer generation.
- Added live animation to the Antarctic System and AI Visualizer scene panels.

### Fixed

- Restored the Research Universe default focus to the Antarctic Ice Sheet core node.
