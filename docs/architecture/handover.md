# Antarctic Atlas macOS architecture handover

This note records the design constraints that matter for continued Mac
development.

## Release contract

- v3.2.2 is an Apple Silicon (`arm64`) release and requires macOS 15.0 or
  later. Intel and universal2 builds are out of scope.
- The published app is ad-hoc signed, not Developer ID signed, and not
  notarized. Keep the README's first-open Gatekeeper instructions accurate
  until the signing and notarization pipeline changes.

## Runtime shape

- `desktop_qt_app.py` is the single application entry point.
- `core/` owns paper parsing/search, shared models, data loading, API clients,
  and macOS settings/cache paths.
- `qt_app/pages/` contains the six product modules.
- `qt_app/templates/` contains the embedded Research Universe document.
- `data/`, `locales/`, the source PDF, and the root PNG icon are packaged
  resources.

## Invariants

1. `sys.modules.setdefault("desktop_qt_app", sys.modules[__name__])` must stay
   before the page imports. It breaks the circular import between the entry
   module and the page mixins.
2. The six page modules are method mixins, not independent widgets. Near the
   bottom of `desktop_qt_app.py`, their private callables are attached to
   `NativeAtlasWindow`. Do not convert one module in isolation.
3. Values read from Qt widgets must be captured on the main thread before work
   is handed to `FunctionWorker` or `StreamWorker`.
4. `core.data.resource_path` must resolve both source-tree and PyInstaller
   bundle resources.
5. Paper highlighting must remain a single-pass replacement, and Chinese search
   must retain its keyword expansion.
6. Translation cleanup must not replace ordinary English words inside paper
   prose.

## Local state

- Settings: `~/Library/Application Support/Antarctic Atlas/settings.json`
- Parsed-paper cache: `~/Library/Caches/Antarctic Atlas/pages.json`
- Development environment: macOS user cache, exposed through the repository's
  `.venv` link

Tests and smoke checks redirect settings and caches to temporary directories.

## Verification boundary

A source smoke check is complete only when the paper loads and all six modules
construct without an external AI request. A packaged build is complete only
when the archive extracts, its executable is `arm64`, every packaged Mach-O is
compatible with the macOS 15.0 deployment target, its configured signature
verifies, and the packaged smoke check exits successfully. For v3.2.2, that
configured signature is ad-hoc; Developer ID signing and notarization are not
release claims.

## Recommended next refactor

The largest structural improvement is converting all six page mixins into real
`QWidget` subclasses in one coordinated change. Treat this as a high-risk UI
refactor and verify every module afterward.
