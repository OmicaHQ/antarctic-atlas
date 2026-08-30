"""Keep tests isolated from real user settings and caches on every platform."""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_TEMP_ROOT = PROJECT_ROOT / ".pytest-tmp"

# pytest's temp-root mkdir does not create parents, so pre-create the dir.
_TEMP_ROOT.mkdir(exist_ok=True)

os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(_TEMP_ROOT))
os.environ.setdefault("ANTARCTIC_ATLAS_CONFIG_DIR", str(_TEMP_ROOT / "config"))
os.environ.setdefault("ANTARCTIC_ATLAS_CACHE_DIR", str(_TEMP_ROOT / "cache"))

# Ensure the project root is importable for `from core import ...`.
sys.path.insert(0, str(PROJECT_ROOT))
