# Antarctic Atlas iOS

SwiftUI iOS wrapper for Antarctic Research Atlas.

Open `AntarcticAtlas.xcodeproj` in Xcode 16 or newer, select the `AntarcticAtlas` scheme, and run on an iOS 17+ simulator or device.

GitHub Actions also builds the app on hosted macOS runners:

- `iOS`: simulator compilation check for development.
- `iOS Unsigned IPA`: produces `AntarcticAtlas-unsigned.ipa` for Windows sideloading.
- `iOS Signed IPA`: produces a signed `.ipa` when Apple Developer signing secrets are configured.

See `INSTALL_IPHONE.md` for the iPhone installation path.

The app is being migrated toward native SwiftUI. A Web tab remains as a temporary fallback so the existing web product stays reachable while native modules catch up:

- Research Universe Explorer
- Antarctic System Explorer
- AI Visualizer
- Mini Research Lab
- Research Compass
- Read Raw Paper
- Existing Streamlit controls, PDF text, and AI backend settings

Native SwiftUI modules currently include:

- Research Universe with keyword matching and topic sheets
- Antarctic System Explorer with case and observation tool switching
- Scientific Story Engine with step-by-step story beats
- Mini Research Lab with conceptual vulnerability controls
- Research Compass with frontier directions, metrics, regions, and methods
- Raw Paper reader using bundled PDFKit and keyword search

The Python/Streamlit app remains unchanged. Future iOS work can progressively replace remaining WebView-only behavior with native SwiftUI, API-backed RAG answers, richer canvas animations, and persistent saved research notes.
