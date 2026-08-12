"""
Desktop launcher (pywebview) for Windows — works with 32-bit or 64-bit Python.

Starts FastAPI (uvicorn) on 127.0.0.1:8000, waits for /health, opens a native window.

Usage (from repo, after frontend build and venv install):
  cd backend
  .venv\\Scripts\\activate
  pip install pywebview
  python ..\\desktop\\launch.py
"""

from __future__ import annotations

import logging
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

# Ensure backend package imports work when launched from desktop/
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}/"
HEALTH_URL = f"http://{HOST}:{PORT}/health"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("desktop")


def _wait_for_health(timeout_sec: float = 60.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.4)
    return False


def _run_uvicorn() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )


def main() -> int:
    import os

    os.chdir(BACKEND_DIR)

    frontend_dist = BACKEND_DIR.parent / "frontend" / "dist"
    if not frontend_dist.is_dir():
        logger.error(
            "frontend/dist not found at %s\n"
            "On this machine run:\n"
            "  cd frontend\n"
            "  npm ci\n"
            "  set VITE_API_URL=http://127.0.0.1:8000\n"
            "  npm run build",
            frontend_dist,
        )
        return 1

    try:
        import webview
    except ImportError:
        logger.error("pywebview is not installed. Run: pip install pywebview")
        return 1

    server = threading.Thread(target=_run_uvicorn, name="uvicorn", daemon=True)
    server.start()
    logger.info("Starting API at %s …", URL)

    if not _wait_for_health():
        logger.error("API did not become ready at %s", HEALTH_URL)
        return 1

    logger.info("Opening desktop window")
    webview.create_window(
        "Document Processing POC",
        URL,
        width=1280,
        height=840,
        min_size=(900, 600),
    )
    webview.start()
    logger.info("Window closed — exiting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
