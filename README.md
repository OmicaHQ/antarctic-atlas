# Antarctic Research Atlas for macOS

Antarctic Atlas is a native Apple Silicon desktop application for exploring the
Antarctic Ice Sheet through the 89-page review paper:

> Noble, T. L. et al. (2020). *The Sensitivity of the Antarctic Ice Sheet to a
> Changing Climate: Past, Present, and Future.* Reviews of Geophysics, 58,
> e2019RG000663.

The app combines paper search, interactive scientific modules, and optional AI
assistance. Evidence-only search and every non-AI module work without an API
key.

## Included modules

- Research Universe Explorer
- Antarctic System Explorer
- AI Visualizer
- Mini Research Lab
- Research Directions
- Read Raw Paper

## Install the Apple Silicon release

1. Download `Antarctic-Atlas-v3.2.0-macOS-arm64.zip` and its `.sha256` file from
   [GitHub Releases](https://github.com/OmicaChow/antarctic-atlas/releases).
2. Verify the checksum, extract the archive, and move `Antarctic Atlas.app` to
   your Applications folder.
3. Open the app. The packaged application does not require Python or `uv`.

The current build is ad-hoc signed and has not been notarized by Apple. macOS
Gatekeeper may require Control-clicking the app and choosing **Open** on the
first launch. Only download the app from the official repository release.

## Development requirements

- Apple Silicon Mac
- macOS 13 or later
- [`uv`](https://docs.astral.sh/uv/)

## Set up and run

```zsh
scripts/setup-macos.sh
.venv/bin/python desktop_qt_app.py
```

The app can switch between English and Chinese from inside the interface.

## Validate

```zsh
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/macos-smoke.py
```

The smoke test parses the bundled paper and constructs all six modules without
making an external AI request.

## Build the Mac app

```zsh
scripts/build-macos.sh
```

The build produces `dist/Antarctic-Atlas-v3.2.0-macOS-arm64.zip` plus a SHA-256
file, verifies the app's architecture and ad-hoc signature, then runs a packaged
cold-start smoke test. Developer ID signing, notarization, stapling, and DMG
distribution remain separate release-hardening steps.

## Repository layout

```text
core/                  paper search, models, data loading, and macOS paths
data/                  research topics, areas, and keyword mappings
docs/                  migration and architecture notes
installer/             native macOS icon
locales/               English and Chinese translations
qt_app/                PySide6 pages and interface support
scripts/               setup, validation, and packaging scripts
tests/                 Python tests
desktop_qt_app.py      application entry point
VERSION                application and release version
```

Mutable files stay outside the repository:

- Settings: `~/Library/Application Support/Antarctic Atlas/settings.json`
- Paper cache: `~/Library/Caches/Antarctic Atlas/pages.pkl`
- Development environment: the macOS user cache, linked as `.venv`

See [the macOS migration guide](docs/MACOS_MIGRATION.md) for release gates and
[the architecture handover](docs/architecture/handover.md) for internal design
constraints.

Source repository: <https://github.com/OmicaChow/antarctic-atlas>

## License and credits

Developed by Omica Chow. Licensed under the MIT License.

Scientific source: Noble et al. (2020), *Reviews of Geophysics*.
