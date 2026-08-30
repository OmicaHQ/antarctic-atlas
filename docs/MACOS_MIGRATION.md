# macOS Apple Silicon release

Version 3.2.1 is the stable Apple Silicon (`arm64`) desktop release for macOS
15.0 or later. Intel Macs are not supported. The active working tree is
intentionally Mac-only; earlier Windows,
Android, web, and Streamlit work remains available through Git history where it
was committed, but is not carried in the development checkout.

## Local setup

The setup deliberately uses the existing `uv` runtime instead of the system
Python, which may be coupled to Xcode command-line tools.

The native Qt environment is stored under macOS's per-user cache directory and
the repository's `.venv` is only a link to it. This keeps the large environment
outside the working tree and avoids sync metadata invalidating Qt plug-in
discovery.

```zsh
scripts/setup-macos.sh
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/macos-smoke.py
```

The smoke test parses the bundled paper, prepares the Qt shell, and constructs
all six modules without making an AI API request.

## Development build

The tracked `.icns` asset is generated from the existing 1024 px project icon.
Build the app with:

```zsh
scripts/build-macos.sh
```

The script creates `dist/Antarctic-Atlas-v3.2.1-macOS-arm64.zip` and its SHA-256
file. It builds and signs the `.app` in a private temporary directory, verifies
its `arm64` architecture, extracts the archive again, and performs a cold
packaged-app smoke test. Extract the archive and move `Antarctic Atlas.app` into
the user's Applications folder before opening it.

On the current macOS 27 environment, launching a thinned packaged Qt app can
temporarily shadow the universal Qt plug-ins used for source development. The
build script refreshes the four already-cached Qt wheels offline and immediately
checks that the development runtime is still loadable.

The published v3.2.1 app uses an ad-hoc signature. It is not signed with an
Apple Developer ID and has not been notarized, so the README documents the
required first-open Gatekeeper approval. The build script can use a Developer
ID Application identity when one is explicitly configured, but notarization,
stapling, and DMG distribution remain future release-hardening work.

## Platform paths

- Settings: `~/Library/Application Support/Antarctic Atlas/settings.json`
- Extracted-paper cache: `~/Library/Caches/Antarctic Atlas/pages.json`

Source and packaged smoke tests redirect both locations into temporary
directories, so validation never changes the user's real settings or cache.

## Stable-release verification

1. Native imports report `arm64` for Python, Qt, PDFium, and packaged helpers.
2. The paper cold-loads once and the second launch reuses the macOS cache.
3. All six modules render at Retina scale without font clipping.
4. QWebEngine and QWebChannel work in Research Universe.
5. English/Chinese switching restarts the packaged app exactly once.
6. Evidence-only search and proposal export work without an API key.
7. The Finder-launched `.app` has no working-directory dependency.
8. The downloaded ad-hoc-signed ZIP follows the documented Gatekeeper approval
   flow on a clean Mac account.

## Deferred release hardening

- Intel or universal2 packaging
- Mac App Store sandboxing
- Persisting API keys in Keychain
- Developer ID signing, notarization, stapling, and public DMG distribution
