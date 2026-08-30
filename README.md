# Antarctic Atlas for macOS

Antarctic Atlas is an Apple Silicon desktop application for exploring the
Antarctic Ice Sheet through an included 89-page scientific review. It combines
local paper search, six interactive research modules, bilingual English/Chinese
UI, and optional AI assistance.

## v3.2.1 stable Mac release

| Requirement | Support |
| --- | --- |
| Mac | Apple Silicon (`arm64`) only; Intel Macs are not supported |
| macOS | macOS 15.0 or later |
| Package | `Antarctic-Atlas-v3.2.1-macOS-arm64.zip` |
| Runtime | Self-contained; Python and `uv` are not required |

Download the current stable build from the
[latest release](https://github.com/OmicaChow/antarctic-atlas/releases/latest).

The v3.2.1 app is **ad-hoc signed**. It is not signed with an Apple Developer ID
and has not been notarized by Apple. Gatekeeper will therefore require an
explicit first-open approval. Only download the app from this repository's
official release page.

## What is included

- Research Universe Explorer with evidence retrieval and optional AI answers
- Antarctic System Explorer
- AI Visualizer for conceptual scientific exploration
- Mini Research Lab
- Research Directions with text export
- Read Raw Paper with page navigation and search
- The complete 89-page Noble et al. (2020) review paper

The visual and simulation modules are educational, conceptual tools. They are
not operational forecasts or substitutes for the underlying paper and expert
scientific judgment.

## Privacy and AI behavior

**Evidence-only mode is local and offline.** It searches the bundled paper on
the Mac, does not call an AI service, and sends no telemetry. The application
contains no analytics or usage tracking.

AI is optional:

- **Local Ollama** sends the question and retrieved paper passages only to the
  Ollama service on `127.0.0.1`.
- **DeepSeek API** or **OpenAI API** sends the question and locally retrieved
  paper passages to the selected online provider. That provider's terms and
  privacy policy then apply.
- API keys entered in the app are held only in memory for the current run. The
  app does not save them to settings, disk, or Keychain; they are cleared when
  the app quits. Keys supplied through environment variables remain managed by
  the launching environment.

The current DeepSeek V4 choices are `deepseek-v4-pro` and
`deepseek-v4-flash`.

## Install

1. Open the [latest release](https://github.com/OmicaChow/antarctic-atlas/releases/latest).
2. Download both `Antarctic-Atlas-v3.2.1-macOS-arm64.zip` and
   `Antarctic-Atlas-v3.2.1-macOS-arm64.zip.sha256`.
3. Verify the download as described below.
4. Double-click the ZIP file, then drag `Antarctic Atlas.app` into
   `/Applications`.
5. In Finder, Control-click `Antarctic Atlas.app`, choose **Open**, then choose
   **Open** again in the confirmation dialog.

If macOS still blocks the app, attempt to open it once, then go to **System
Settings > Privacy & Security**. In the Security section, choose **Open Anyway**,
authenticate, and confirm **Open**. This approval should only be needed for the
first launch of a downloaded build.

### Verify the SHA-256 checksum

With both downloaded files in `~/Downloads`, run:

```zsh
cd ~/Downloads
shasum -a 256 -c Antarctic-Atlas-v3.2.1-macOS-arm64.zip.sha256
```

Continue only if the result ends with `OK`. If it does not, delete the download
and obtain both files again from the official release page.

## Upgrade

1. Quit Antarctic Atlas.
2. Download and verify the new ZIP and checksum from the
   [latest release](https://github.com/OmicaChow/antarctic-atlas/releases/latest).
3. Extract the ZIP and replace the existing `Antarctic Atlas.app` in
   `/Applications`.
4. Use the first-open Gatekeeper steps above if macOS asks again.

Settings and the replaceable paper cache live outside the app bundle and are
kept during a normal upgrade.

## Uninstall or reset local data

Quit Antarctic Atlas, then move `/Applications/Antarctic Atlas.app` to the
Trash. If it was installed in `~/Applications`, remove that copy instead.

To remove local data as well, open Finder, choose **Go > Go to Folder**, and
visit these locations:

- `~/Library/Application Support/Antarctic Atlas/` — contains `settings.json`
- `~/Library/Caches/Antarctic Atlas/` — contains the replaceable `pages.json`
  paper cache

Delete only the Antarctic Atlas folder or the named file at each location.
Removing `pages.json` is safe; the bundled 89-page paper will be parsed again on
the next launch.

## Troubleshooting and issues

- Confirm that the Mac has Apple Silicon and is running macOS 15.0 or later.
- For an initial Gatekeeper block, follow the first-open steps under
  [Install](#install).
- Evidence-only search works without an API key. Online answers require a valid
  key for the selected provider; Local Ollama requires the configured local
  model to be running.
- If paper loading appears stale, quit the app and remove only
  `~/Library/Caches/Antarctic Atlas/pages.json`.

Report reproducible problems through
[GitHub Issues](https://github.com/OmicaChow/antarctic-atlas/issues). Include the
app version, macOS version, Mac model/chip, exact error text, and steps to
reproduce. Never include an API key in an issue or screenshot.

## Develop, test, and build

Development requires an Apple Silicon Mac, macOS 15.0 or later, and
[`uv`](https://docs.astral.sh/uv/). Packaging also requires Xcode.app. The setup
script creates a Python 3.12 environment in the macOS user cache and exposes it
through the repository's `.venv` link.

```zsh
scripts/setup-macos.sh
.venv/bin/python desktop_qt_app.py
```

Run the full automated test suite and source smoke test:

```zsh
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/macos-smoke.py
```

Build and verify the release archive:

```zsh
scripts/build-macos.sh
```

The build produces the versioned ZIP and SHA-256 file under `dist/`. It checks
the packaged dependencies, `arm64` architecture, macOS 15 deployment target,
signature, archive extraction, and a cold packaged-app smoke launch. Without an
explicit Developer ID identity, the script creates the ad-hoc signature used by
the v3.2.1 release; notarization is a separate, currently unperformed step.

## Repository and local files

```text
core/                  paper search, models, data loading, and macOS paths
data/                  research topics, areas, and keyword mappings
docs/                  migration and architecture notes
installer/             native macOS icon
locales/               English and Chinese translations
qt_app/                PySide6 pages and interface support
scripts/               setup, validation, and packaging scripts
tests/                 automated tests
desktop_qt_app.py      application entry point
VERSION                application and release version
```

Mutable files stay outside the repository and app bundle:

- Settings: `~/Library/Application Support/Antarctic Atlas/settings.json`
- Paper cache: `~/Library/Caches/Antarctic Atlas/pages.json`
- Development environment: the macOS user cache, linked as `.venv`

See the [macOS release guide](docs/MACOS_MIGRATION.md), the
[architecture handover](docs/architecture/handover.md), and
[third-party notices](THIRD_PARTY_NOTICES.md).

## License and scientific source

The Antarctic Atlas project code is licensed under the [MIT License](LICENSE).
Third-party libraries retain their own licenses; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The bundled paper is a separate copyrighted scientific work distributed under
the Creative Commons Attribution 4.0 International License
([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)):

> Noble, T. L. et al. (2020). *The Sensitivity of the Antarctic Ice Sheet to a
> Changing Climate: Past, Present, and Future.* Reviews of Geophysics, 58,
> e2019RG000663. [https://doi.org/10.1029/2019RG000663](https://doi.org/10.1029/2019RG000663)

Copyright © 2020 The Authors. Reuse must provide appropriate attribution. The
project's MIT license does not replace or extend to the paper's CC BY 4.0 terms.

Source repository: <https://github.com/OmicaChow/antarctic-atlas>
