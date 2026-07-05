# Antarctic Research Atlas

<p align="center">
  <img src="assets/antarctic-atlas-social-preview.png" alt="Antarctic Atlas logo" width="820">
</p>

**Antarctic Atlas is an interactive educational and research platform for exploring the Antarctic Ice Sheet.**

Current release: **v3.1.2**

[Live Demo](https://antarctic-research-atlas.streamlit.app/)

[Download the latest Windows installer](https://github.com/OmicaHQ/antarctic-atlas/releases/latest)

---

## Project Overview

Antarctic Atlas is the desktop and web implementation of the Antarctic Research Atlas project.

The project transforms an 89-page review paper:

**Noble, T. L. et al. (2020). _The Sensitivity of the Antarctic Ice Sheet to a Changing Climate: Past, Present, and Future._ Reviews of Geophysics, 58, e2019RG000663.**

into a visual, AI-assisted platform where users can explore Antarctic research interactively.

The platform combines scientific visualization, interactive exploration, AI-assisted storytelling, educational tools, and a Windows desktop app for local use.

---

## Features

### Research Universe Explorer

![Research Universe Explorer](research_universe_explorer.png)

Explore key concepts and relationships in Antarctic Ice Sheet research through an interactive knowledge universe.

### Antarctic System Explorer

![Antarctic System Explorer](antarctic_system_explorer.png)

Visualize satellite observations and compare different glaciers and ice shelves using multiple observation layers.

### AI Visualizer

![AI Visualizer](ai_visualizer.png)

Generate scientific stories and animations based on the review paper.

### Mini Research Lab

![Mini Research Lab](mini_research_lab1.png)

![Mini Research Lab](mini_research_lab2.png)

![Mini Research Lab](mini_research_lab3.png)

![Mini Research Lab](mini_research_lab4.png)

Conduct interactive experiments and explore Antarctic system responses under different scenarios.

### Research Compass

![Research Compass](research_compass.png)

Explore future research questions, open scientific challenges, and emerging directions in Antarctic science.

### Read Raw Paper

Access the full review paper PDF and navigate it directly within the platform.

---

## Windows Desktop App

The recommended Windows download is the latest installer on the GitHub Releases page:

[Antarctic Atlas v3.1.2 - Windows Desktop Installer](https://github.com/OmicaHQ/antarctic-atlas/releases/tag/v3.1.2)

Installer file:

- `Antarctic-Atlas-v3.1.2-Setup.exe`
- SHA256: `394BC66DE8A417BA3B4BC94D1212F9CA2E1A8AC51E0E868CBD893FC451E166FC`

The installer creates Start Menu and optional Desktop shortcuts for one-click launch. No Python, Streamlit server, or manual dependency setup is required for the installer version.

Note: the installer metadata shows `Omica Chow`, but the installer is not code-signed yet. Windows may still show an unknown-publisher warning until a code-signing certificate is applied.

---

## Run From Source

Clone the repository:

```bash
git clone https://github.com/OmicaHQ/antarctic-atlas.git
cd antarctic-atlas
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the legacy Streamlit web demo locally:

```bash
streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

## API Keys

AI features are optional. For local development, copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and add your own keys:

```toml
DEEPSEEK_API_KEY = ""
OPENAI_API_KEY = ""
```

Do not commit real API keys. Evidence-only mode works without an API key.

You can also enter and test API keys inside the app's AI Backend settings. The local Ollama backend targets `gemma4:e4b`, so local AI features require Ollama with that model available.

## Distribution Notes

Windows installers are distributed through GitHub Releases. The `release-assets/` folder is kept only for historical and direct installer references.

See `CHANGELOG.md` for version notes.

## Version History

Antarctic Atlas is now documented as three major product phases:

- `v1`: Original Streamlit research atlas. This established the paper-centered exploration flow, Research Universe concept, Antarctic System views, AI Visualizer, Mini Research Lab, Research Compass, and raw-paper access.
- `v2`: Streamlit desktop/productization phase. This added iOS-style visual polish, Windows installer packaging, Streamlit module splitting, improved layouts, local AI options, and maintenance fixes while keeping the original Streamlit experience.
- `v3.0`: Native Qt desktop reconstruction phase. This is the 1:1 desktop recreation line that moved the product from Streamlit-in-a-window toward a native Qt shell with animated System and Visualizer scenes, WebEngine Research Universe, real AI/RAG calls, smoother startup, and packaged desktop delivery.
- `v3.1`: Unified bilingual desktop phase. This consolidates the app back into one installer with in-app English / Chinese switching, broader i18n coverage for Qt widgets, painter-drawn scenes, HTML cards, Universe labels, and storytelling/export text.

### Current Release

- `v3.1.2`: Fixed Chinese-locale Research Universe AI answers getting stuck after backend connectivity succeeded. Streaming answers are correctly bound to the Qt page, and answer language now follows the active app language.
- `v3.1.1`: Qt-only desktop installer packaging. The formal Windows installer no longer bundles the legacy Streamlit app, `atlas_app` page tree, pywebview shell, or Streamlit runtime; Qt now owns its configuration and packaged Universe template directly. The legacy Streamlit source remains in the repository for web-demo/history use.
- `v3.1.0`: Unified bilingual Qt desktop app with improved Chinese localization, fixed Universe template labels, cleaned AI Visualizer story/export translation, and persisted in-app language preference.

### Qt Reconstruction Line

The former Qt reconstruction installers have been renumbered from the old local `v2.0.x` sequence:

- `v3.0.0`: First Qt desktop preview, corresponding to the former `v2.0.8`.
- `v3.0.1` - `v3.0.15`: Iterative Qt fixes and polish from installer resource repair through dual-language desktop packaging, corresponding to former `v2.0.9` - `v2.0.23`.
- `v3.0.13`: DeepSeek V4 Pro streaming answers, improved paper retrieval, adaptive AI answer layout, automatic Ollama checks, API-key usability improvements, smoother Enter Project behavior, and explicit title-bar branding icon.
- `v3.0.14`: Fresh loading pass with the desktop PDF text cache removed and simplified loading-page behavior restored.
- `v3.0.15`: Qt page module splitting plus separate English and Chinese installer builds.

## Credits

Developed by Omica Chow

Based on:

Noble et al. (2020), Reviews of Geophysics

Built with Python, Qt/PySide6, and scientific Python tooling. The original Streamlit implementation remains in the source tree as the legacy web demo.

## License

This project is licensed under the MIT License.
