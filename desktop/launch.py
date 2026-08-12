"""
Frontend-only desktop launcher (WebView2 / pywebview).

- Serves local React build from frontend/dist (does NOT start FastAPI).
- Opens a native Windows window.
- Backend runs separately (Python uvicorn or IIS).
- Packaged as POC-UI.exe via PyInstaller (see build-windows.bat / poc-ui.spec).

Dev:
  python desktop/launch.py

Production:
  Double-click POC-UI.exe (after build-windows.bat)
"""

from __future__ import annotations

import json
import logging
import mimetypes
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def _app_dirs() -> tuple[Path, Path, Path]:
    """
    Return (desktop_or_exe_dir, frontend_dist, config_path).

    Frozen EXE: UI files under _MEIPASS; editable config.json next to the EXE.
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        meipass = Path(getattr(sys, "_MEIPASS", exe_dir))
        dist = meipass / "frontend" / "dist"
        if not dist.is_dir():
            dist = exe_dir / "frontend" / "dist"
        config = exe_dir / "config.json"
        if not config.is_file():
            bundled = meipass / "config.json"
            if bundled.is_file():
                config = bundled
        return exe_dir, dist, config

    desktop_dir = Path(__file__).resolve().parent
    repo = desktop_dir.parent
    return desktop_dir, repo / "frontend" / "dist", desktop_dir / "config.json"


DESKTOP_DIR, FRONTEND_DIST, CONFIG_PATH = _app_dirs()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("desktop-ui")


def _load_config() -> dict:
    defaults = {
        "apiBaseUrl": "http://127.0.0.1:8000",
        "fallbackApiBaseUrl": "",
        "preferLocalhost": True,
        "uiHost": "127.0.0.1",
        "uiPort": 17890,
    }
    if not CONFIG_PATH.is_file():
        logger.warning("No %s — using defaults", CONFIG_PATH)
        return defaults
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    defaults.update({k: v for k, v in data.items() if v is not None})
    return defaults


def _health_ok(base_url: str, timeout: float = 1.2) -> bool:
    url = base_url.rstrip("/") + "/health"
    try:
        with urlopen(url, timeout=timeout) as resp:
            return resp.status == 200
    except (URLError, TimeoutError, OSError):
        return False


def _resolve_api_base(cfg: dict) -> str:
    local = str(cfg.get("apiBaseUrl") or "http://127.0.0.1:8000").rstrip("/")
    fallback = str(cfg.get("fallbackApiBaseUrl") or "").rstrip("/")
    prefer_local = bool(cfg.get("preferLocalhost", True))

    if prefer_local and _health_ok(local):
        logger.info("Backend reachable at %s (localhost)", local)
        return local
    if fallback and _health_ok(fallback):
        logger.info("Backend reachable at %s (domain/fallback)", fallback)
        return fallback
    if prefer_local:
        logger.warning(
            "Local backend not reachable at %s — UI will still open; "
            "start uvicorn/IIS or set fallbackApiBaseUrl in config.json",
            local,
        )
        return local
    return fallback or local


class SpaStaticHandler(SimpleHTTPRequestHandler):
    """Serve frontend/dist with SPA fallback and /app-config.json."""

    def __init__(self, *args, directory: str, app_config: dict, **kwargs):
        self._app_config = app_config
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        logger.debug("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] in ("/app-config.json", "/app-config.json/"):
            body = json.dumps(self._app_config).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        path_only = self.path.split("?", 1)[0]
        rel = path_only.lstrip("/") or "index.html"
        candidate = Path(self.directory) / rel
        if candidate.is_file():
            return super().do_GET()

        index = Path(self.directory) / "index.html"
        if index.is_file() and "." not in Path(rel).name:
            self.path = "/index.html"
            return super().do_GET()

        return super().do_GET()


def _start_ui_server(host: str, port: int, app_config: dict) -> ThreadingHTTPServer:
    handler = partial(
        SpaStaticHandler,
        directory=str(FRONTEND_DIST),
        app_config=app_config,
    )
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("application/json", ".json")

    httpd = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(target=httpd.serve_forever, name="ui-static", daemon=True)
    thread.start()
    return httpd


def main() -> int:
    global FRONTEND_DIST, CONFIG_PATH, DESKTOP_DIR
    DESKTOP_DIR, FRONTEND_DIST, CONFIG_PATH = _app_dirs()

    if not FRONTEND_DIST.is_dir():
        logger.error(
            "frontend/dist not found at %s\n"
            "Build the UI first (npm run build), then rebuild the EXE.",
            FRONTEND_DIST,
        )
        return 1

    try:
        import webview
    except ImportError:
        logger.error("pywebview is not installed. Run: pip install pywebview")
        return 1

    cfg = _load_config()
    api_base = _resolve_api_base(cfg)
    ui_host = str(cfg.get("uiHost") or "127.0.0.1")
    ui_port = int(cfg.get("uiPort") or 17890)

    app_config = {
        "apiBaseUrl": api_base,
        "fallbackApiBaseUrl": str(cfg.get("fallbackApiBaseUrl") or "").rstrip("/"),
        "preferLocalhost": bool(cfg.get("preferLocalhost", True)),
    }

    httpd = _start_ui_server(ui_host, ui_port, app_config)
    ui_url = f"http://{ui_host}:{ui_port}/"
    logger.info("UI: %s | API: %s | config: %s", ui_url, api_base, CONFIG_PATH)

    try:
        webview.create_window(
            "Document Processing POC",
            ui_url,
            width=1280,
            height=840,
            min_size=(900, 600),
        )
        webview.start()
    finally:
        httpd.shutdown()
        logger.info("UI server stopped")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
