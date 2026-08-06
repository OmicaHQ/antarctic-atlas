"""pytest configuration — force a project-local temp root.

On this Windows machine the default system temp base
(%LOCALAPPDATA%/Temp/pytest-of-<user>) is permission-locked, so tests that use
the tmp_path fixture fail at setup. Pointing pytest's temp root at a writable
project-local directory keeps the suite hermetic and CI-safe.
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
_TEMP_ROOT = PROJECT_ROOT / ".pytest-tmp"

# pytest's temp-root mkdir does not create parents, so pre-create the dir.
_TEMP_ROOT.mkdir(exist_ok=True)

os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(_TEMP_ROOT))

# Ensure the project root is importable for `from core import ...`.
sys.path.insert(0, str(PROJECT_ROOT))
