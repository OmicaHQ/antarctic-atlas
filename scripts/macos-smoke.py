"""Headless source smoke test for the native Qt application on macOS."""

import os
import sys
import tempfile
import time
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

_SMOKE_WORKSPACE = tempfile.TemporaryDirectory(prefix="antarctic-atlas-source-smoke-")
_SMOKE_ROOT = Path(_SMOKE_WORKSPACE.name)
os.environ["ANTARCTIC_ATLAS_CONFIG_DIR"] = str(_SMOKE_ROOT / "config")
os.environ["ANTARCTIC_ATLAS_CACHE_DIR"] = str(_SMOKE_ROOT / "cache")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from desktop_qt_app import NativeAtlasWindow


TIMEOUT_SECONDS = 120


def main() -> int:
    app = QApplication(sys.argv)
    window = NativeAtlasWindow()
    started = time.monotonic()
    result = {"code": 1}

    def finish(code: int, message: str) -> None:
        result["code"] = code
        print(message, flush=True)
        window.close()
        app.exit(code)

    def poll() -> None:
        status_widget = getattr(window, "landing_status", None)
        status_text = status_widget.text() if status_widget else ""
        if "failed" in status_text.lower():
            finish(1, f"MACOS_SMOKE_FAILED: {status_text}")
            return
        if getattr(window, "_main_ready", False):
            try:
                for index in range(len(window._page_builders)):
                    window._ensure_page_built(index)
                built = sum(widget is not None for widget in window._page_widgets)
                if built != 6:
                    raise RuntimeError(f"expected 6 pages, built {built}")
                if not window.pages:
                    raise RuntimeError("paper loader returned no readable pages")
            except Exception as exc:
                finish(1, f"MACOS_SMOKE_FAILED: {exc}")
                return
            QTimer.singleShot(
                1000,
                lambda: finish(
                    0,
                    f"MACOS_SMOKE_OK pages={len(window.pages)} modules={built}",
                ),
            )
            return
        if time.monotonic() - started > TIMEOUT_SECONDS:
            finish(1, f"MACOS_SMOKE_TIMEOUT: {status_text}")
            return
        QTimer.singleShot(100, poll)

    QTimer.singleShot(0, poll)
    app.exec()
    return result["code"]


if __name__ == "__main__":
    raise SystemExit(main())
