# Antarctic Atlas Native Preview

This directory contains the next-generation macOS client. It is a native
SwiftUI/AppKit application targeting macOS 15 and Apple Silicon while the
published Qt-based v3.2.2 release remains the stable line. The v4.0.0 build is
published as a GitHub Pre-release for parity testing.

The preview intentionally uses a separate bundle identifier and application
name, so it can be installed beside the stable release during parity testing.

## Build

```bash
./macos-native/scripts/build-app.sh
```

The app is assembled at
`dist-native/Antarctic Atlas Native Preview.app` and ad-hoc signed for local
testing. Developer ID signing and notarization remain release gates.

Build the distributable Preview artifacts (DMG, ZIP, and checksums):

```bash
./macos-native/scripts/build-release.sh
```

Artifacts are written to `dist-native-release/` and can be installed beside
the stable app without replacing it.

## Install beside the stable app

```bash
./macos-native/scripts/install-preview.sh
```

## Design principles

- Native window, sidebar, toolbar, inspector, menus, Settings, and shortcuts.
- Scientific canvases keep the Antarctic polar-night identity; system chrome
  follows macOS appearance, accent, contrast, and motion preferences.
- The app opens directly into the research workspace without a fake loading
  gate.
- Evidence-only mode stays offline by default.
- The bundled paper remains available through PDFKit with its original layout.
