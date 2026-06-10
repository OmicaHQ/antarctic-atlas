import atexit
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import webview


APP_TITLE = "Antarctic Ice Sheet Research Atlas"
APP_ICON = "antarctic_atlas.ico"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def log_path() -> Path:
    return app_dir() / "atlas_desktop.log"


def write_log(message: str):
    try:
        with log_path().open("a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except Exception:
        pass


def bundled_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", app_dir()))
    candidate = base / name
    if candidate.exists():
        return candidate
    return app_dir() / name


def app_icon_path():
    icon_path = bundled_path(APP_ICON)
    return str(icon_path) if icon_path.exists() else None


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(url: str, timeout: float = 45.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.5) as response:
                if response.status < 500:
                    return True
        except URLError:
            time.sleep(0.35)
        except Exception:
            time.sleep(0.35)
    return False


def streamlit_command(app_file: Path, port: int) -> list[str]:
    if getattr(sys, "frozen", False):
        return [
            sys.executable,
            "--streamlit",
            str(app_file),
            str(port),
        ]
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_file),
        "--server.headless=true",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
        "--global.developmentMode=false",
    ]


class AtlasDesktopApp:
    def __init__(self):
        self.process: subprocess.Popen | None = None

    def start_streamlit(self) -> str:
        root = app_dir()
        app_file = bundled_path("app.py")
        if not app_file.exists():
            raise FileNotFoundError(f"Cannot find app.py at {app_file}")

        port = find_free_port()
        url = f"http://127.0.0.1:{port}"
        cmd = streamlit_command(app_file, port)
        env = os.environ.copy()
        env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
        env["STREAMLIT_SERVER_HEADLESS"] = "true"

        creationflags = 0
        startupinfo = None
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        self.process = subprocess.Popen(
            cmd,
            cwd=str(root),
            env=env,
            stdout=(log_path().open("a", encoding="utf-8") if getattr(sys, "frozen", False) else subprocess.DEVNULL),
            stderr=subprocess.STDOUT if getattr(sys, "frozen", False) else subprocess.DEVNULL,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )

        if not wait_for_server(url):
            self.stop_streamlit()
            raise RuntimeError("Streamlit did not start in time.")
        return url

    def stop_streamlit(self):
        proc = self.process
        self.process = None
        if not proc:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main():
    desktop = AtlasDesktopApp()
    atexit.register(desktop.stop_streamlit)
    try:
        url = desktop.start_streamlit()
    except Exception as exc:
        webview.create_window(APP_TITLE, html=f"<h2>Startup failed</h2><pre>{exc}</pre>", width=760, height=420)
        webview.start(icon=app_icon_path())
        return

    window = webview.create_window(
        APP_TITLE,
        url,
        width=1440,
        height=960,
        min_size=(1180, 760),
        text_select=True,
    )

    def on_closed():
        desktop.stop_streamlit()

    window.events.closed += on_closed
    webview.start(debug=False, icon=app_icon_path())


def run_streamlit_child():
    try:
        write_log(f"Starting Streamlit child with argv={sys.argv!r}")
        if len(sys.argv) < 4:
            raise SystemExit("Missing Streamlit child arguments.")
        app_file = sys.argv[2]
        port = sys.argv[3]
        sys.argv = [
            "streamlit",
            "run",
            app_file,
            "--server.headless=true",
            f"--server.port={port}",
            "--browser.gatherUsageStats=false",
            "--server.fileWatcherType=none",
            "--global.developmentMode=false",
        ]
        from streamlit.web.cli import main as streamlit_main

        streamlit_main()
    except Exception as exc:
        write_log(f"Streamlit child failed: {exc!r}")
        raise


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--streamlit":
        run_streamlit_child()
    else:
        main()
