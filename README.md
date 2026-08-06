# Antarctic Research Atlas

<p align="center">
  <img src="assets/antarctic-atlas-social-preview.png" alt="Antarctic Atlas preview" width="820">
</p>

**Antarctic Atlas is an interactive educational and research platform for exploring the Antarctic Ice Sheet.**

The project transforms the 89-page review paper:

> Noble, T. L. et al. (2020). *The Sensitivity of the Antarctic Ice Sheet to a Changing Climate: Past, Present, and Future.* Reviews of Geophysics, 58, e2019RG000663.

into a visual, AI-assisted environment for exploring scientific concepts, observations, system processes, research questions, and evidence from the paper.

- [Online demo](https://antarctic-research-atlas.streamlit.app/)
- [Windows releases](https://github.com/OmicaHQ/antarctic-atlas/releases/latest)
- [Source repository](https://github.com/OmicaHQ/antarctic-atlas)

## Product surfaces

The repository contains three related surfaces:

| Surface | Role | Entry point |
| --- | --- | --- |
| PySide6 desktop app | Main, full-featured Windows application | `desktop_qt_app.py` |
| Streamlit app | Legacy web demo and historical implementation | `app.py` |
| vinext site | Public project and launch page | `app/page.tsx` |

The desktop application is the primary product. The Streamlit source remains available for the online demo and project history. The vinext site introduces the project and links to the interactive demo.

## Existing modules

- **Research Universe Explorer** — explores concepts, evidence, and relationships as an interactive knowledge universe.
- **Antarctic System Explorer** — compares glaciers, ice shelves, processes, and observation layers.
- **AI Visualizer** — creates scientific narratives and storyboards from the review.
- **Mini Research Lab** — explores existing interactive Antarctic system scenarios.
- **Research Directions** — examines research questions, methods, regions, and proposal outlines.
- **Read Raw Paper** — searches and reads the bundled review paper.

AI features are optional. Evidence-only retrieval and the non-AI modules remain usable without an API key.

## Repository structure

```text
app/                  vinext project website
atlas_app/            legacy Streamlit application
core/                 shared paper-search models and text processing
data/                 shared research topics, areas, and keyword mappings
qt_app/               PySide6 desktop pages, configuration, and localization
tests/                Python core tests and website rendering tests
installer/            Windows installer definitions and artwork
desktop_qt_app.py     main desktop application
app.py                Streamlit entry point
```

The source review PDF is expected in the project root using the filename configured in `config.py`.

## Run the desktop app from source

Python 3.9 or later is recommended.

```bash
python -m venv .venv
```

Activate the environment, install dependencies, and run:

```bash
python -m pip install -r requirements.txt
python desktop_qt_app.py
```

Start directly in Chinese:

```bash
python desktop_qt_app_zh.py
```

The unified desktop app also supports changing language from inside the application.

## Run the Streamlit demo

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Then open `http://localhost:8501`.

## Run the project website

The website requires Node.js 22.13 or later.

```bash
npm install
npm run dev
```

Production verification:

```bash
npm test
```

The npm scripts are cross-platform and set the Wrangler log path through a small Node launcher.

## AI backends and keys

Supported existing backends are:

- Evidence only
- Local Ollama
- DeepSeek API
- OpenAI API

For Streamlit development, copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and enter your own keys:

```toml
DEEPSEEK_API_KEY = ""
OPENAI_API_KEY = ""
```

Keys may also be supplied through environment variables or entered in the existing application settings. Do not commit real credentials.

The configured local Ollama endpoint and model are defined in `config.py`.

## Tests

Run the shared Python search and text-processing tests:

```bash
python -m pytest tests/test_core.py -q
```

Run the website build and rendered-page tests:

```bash
npm test
```

Run a Python syntax check across the application:

```bash
python -m compileall -q app.py desktop_qt_app.py atlas_app qt_app core
```

## Windows packaging

`Antarctic Atlas.spec` defines the current PyInstaller desktop package. It includes the Qt page modules, localization files, shared research data, source PDF, and installer icon.

The Inno Setup definition is located at `installer/AntarcticAtlasSetup.iss`. Release installers are distributed through GitHub Releases.

See [CHANGELOG.md](CHANGELOG.md) for the version history.

## License and credits

Developed by Omica Chow.

Scientific source: Noble et al. (2020), *Reviews of Geophysics*.

This project is licensed under the MIT License.
