"""
Desktop launcher (pywebview) for Windows — works with 32-bit or 64-bit Python.

Starts FastAPI on 127.0.0.1:8000 via uvicorn or Hypercorn, waits for /health, opens a native window.

Usage (from repo, after frontend build and venv install):
  cd backend
  .venv\\Scripts\\activate
  pip install pywebview
  python ..\\desktop\\launch.py
"""

from __future__ import annotations

import atexit
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

# Resolve paths both for source repo and packaged launch.exe.
if getattr(sys, "_MEIPASS", None):
    exe_dir = Path(sys.argv[0]).resolve().parent
else:
    exe_dir = Path(__file__).resolve().parent

if exe_dir.name == "desktop":
    BACKEND_DIR = exe_dir.parent / "backend"
elif exe_dir.name == "dist":
    BACKEND_DIR = exe_dir.parent
else:
    BACKEND_DIR = exe_dir

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}/"
HEALTH_URL = f"http://{HOST}:{PORT}/health"

BACKEND_EXE_NAMES = ["backend.exe", "main.exe"]
BACKEND_EXE = next((BACKEND_DIR / name for name in BACKEND_EXE_NAMES if (BACKEND_DIR / name).is_file()), BACKEND_DIR / "backend.exe")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("desktop")

_backend_process: subprocess.Popen | None = None


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


def _find_python_executable() -> str:
    if not getattr(sys, "_MEIPASS", None):
        return sys.executable

    candidate = os.environ.get("PYTHON")
    if candidate:
        return candidate

    for name in ["python.exe", "python3.exe", "python"]:
        try:
            result = subprocess.run([name, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                return name
        except OSError:
            continue

    return sys.executable


def _shutdown_backend() -> None:
    global _backend_process
    if _backend_process is None:
        return
    if _backend_process.poll() is None:
        logger.info("Stopping backend process")
        _backend_process.terminate()
        try:
            _backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Backend process did not exit gracefully, killing")
            _backend_process.kill()
    _backend_process = None


def _start_backend_process(cmd: list[str]) -> subprocess.Popen | None:
    global _backend_process
    log_dir = BACKEND_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "desktop-backend.log"
    try:
        log_file = open(log_file_path, "a", encoding="utf-8")
    except OSError:
        log_file = subprocess.DEVNULL

    try:
        _backend_process = subprocess.Popen(
            cmd,
            cwd=BACKEND_DIR,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        time.sleep(1.0)
        if _backend_process.poll() is not None:
            logger.error("Backend process exited immediately with code %s. See %s", _backend_process.returncode, log_file_path)
            return None
        return _backend_process
    except Exception as exc:
        logger.exception("Failed to start backend process: %s", exc)
        return None


def _run_server() -> None:
    if BACKEND_EXE.is_file():
        process = _start_backend_process([str(BACKEND_EXE)])
        if process is None:
            return
        process.wait()
        return

    python_cmd = _find_python_executable()
    uvicorn_cmd = [python_cmd, "-m", "uvicorn", "app.main:app", "--host", HOST, "--port", str(PORT)]
    hypercorn_cmd = [python_cmd, "-m", "hypercorn", "app.main:app", "--bind", f"{HOST}:{PORT}"]

    process = _start_backend_process(uvicorn_cmd)
    if process is not None:
        process.wait()
        return

    logger.info("uvicorn launch failed, trying hypercorn")
    process = _start_backend_process(hypercorn_cmd)
    if process is not None:
        process.wait()
        return

    logger.error("Could not start backend server")
    return


def main() -> int:
    os.chdir(BACKEND_DIR)

    atexit.register(_shutdown_backend)

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

    server = threading.Thread(target=_run_server, name="asgi-server", daemon=True)
    server.start()
    logger.info("Starting API at %s …", URL)

    if not _wait_for_health():
        logger.error("API did not become ready at %s", HEALTH_URL)
        _shutdown_backend()
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
    _shutdown_backend()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())