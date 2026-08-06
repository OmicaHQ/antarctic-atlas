"""Dependency-free loaders for the data/*.json files (and direction data).

Both the desktop app and the legacy Streamlit app read the same JSON files, so
the loaders live here. resource_path covers PyInstaller bundle paths.
"""
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DATA_DIR = _PROJECT_ROOT / "data"


def _search_bases():
    return [
        Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "_MEIPASS", "") else _PROJECT_ROOT,
        Path(sys.executable).resolve().parent / "_internal",
        _PROJECT_ROOT,
    ]


def resource_path(*parts):
    """Resolve a bundled resource (template, icon, ...) against the bundle or repo root.

    In a PyInstaller bundle these files live next to the executable (_internal),
    so _MEIPASS/_internal are checked first; running from source they sit at the
    repo root. `core/` is NOT a valid base — this module lives there, the files
    it resolves do not.
    """
    for base in _search_bases():
        path = base.joinpath(*parts)
        if path.exists():
            return path
    return _search_bases()[0].joinpath(*parts)


def data_dir() -> Path:
    """Directory containing the data JSON files (bundle-aware)."""
    for base in _search_bases():
        candidate = base / "data"
        if candidate.exists():
            return candidate
    return _DATA_DIR


def load_data_json(filename: str) -> dict:
    """Load a data/*.json file from the project root or PyInstaller bundle."""
    path = data_dir() / filename
    if not path.exists():
        path = _DATA_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))
