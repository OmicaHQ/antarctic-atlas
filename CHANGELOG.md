# Changelog

All notable changes to Antarctic Research Atlas are documented here.

## Unreleased

### Changed

- Removed internal scrolling from the Research Universe map knowledge card so the card displays as a fixed glass panel inside the map.

## v2.0.1 - Documentation Update

### Added

- Added explicit desktop app documentation to `README.md`.
- Added this changelog so GitHub users can quickly understand version differences.

### Clarified

- Documented that `desktop_app.py` is the desktop app entry point.
- Documented that `Antarctic Atlas.spec` is the PyInstaller build configuration for the Windows app package.
- Clarified that build outputs should be distributed as release assets instead of committed to the repository.

## v2.0 - Local Atlas Update

### Added

- Added Windows desktop app support through `desktop_app.py`.
- Added PyInstaller configuration through `Antarctic Atlas.spec`.
- Added `.streamlit/secrets.example.toml` for safe local API key setup.
- Added `.gitignore` rules for local secrets, virtual environments, build outputs, backups, logs, and Python cache files.

### Changed

- Updated the local Ollama model target to `gemma4:e4b`.
- Improved the visual system toward a stronger iOS-style liquid glass interface.
- Unified module title styling and spacing.
- Improved module layout behavior for desktop use.
- Expanded README setup and API key instructions.
- Added desktop packaging dependencies to `requirements.txt`.

### Fixed

- Fixed AI Visualizer playback so modules can be shown correctly during playback.
- Fixed clipped module titles by adjusting title block spacing.
- Fixed GNSS vector labels that rendered as `92` instead of arrows.
- Fixed Research Universe card behavior so updated card content resets to the top instead of staying scrolled down.
- Fixed several text encoding and symbol display issues in the app UI.
- Reduced layout overlap issues in map/card areas.

## v1.0 - Preserved GitHub Version

### Notes

- Preserved the GitHub version that existed before the local 2.0 update.
- This version remains available through the `v1.0` Git tag.
