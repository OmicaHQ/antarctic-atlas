# Antarctic Atlas iOS

Native SwiftUI iOS version of Antarctic Research Atlas.

Open `AntarcticAtlas.xcodeproj` in Xcode 16 or newer, select the `AntarcticAtlas` scheme, and run on an iOS 17+ simulator or device.

GitHub Actions also builds the app on hosted macOS runners:

- `iOS`: simulator compilation check for development.
- `iOS Unsigned IPA`: produces `AntarcticAtlas-unsigned.ipa` for Windows sideloading.
- `iOS Signed IPA`: produces a signed `.ipa` when Apple Developer signing secrets are configured.

See `INSTALL_IPHONE.md` for the iPhone installation path.

This first native build ports the main product structure from the Streamlit app:

- Research Universe with keyword matching and topic sheets
- Antarctic System Explorer with case and observation tool switching
- Scientific Story Engine with step-by-step story beats
- Mini Research Lab with conceptual vulnerability controls
- Research Compass with frontier directions, metrics, regions, and methods

The Python/Streamlit app remains unchanged. Future iOS work can add PDFKit paper reading, API-backed RAG answers, richer canvas animations, and persistent saved research notes.
