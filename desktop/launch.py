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
import importlib.util
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
    exe_dir = Path(sys.executable).resolve().parent
else:
    exe_dir = Path(__file__).resolve().parent

if exe_dir.name == "desktop":
    BACKEND_DIR = exe_dir.parent / "backend"
elif exe_dir.name == "dist":
    BACKEND_DIR = exe_dir.parent.parent / "backend"
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
DESKTOP_DIR = Path(__file__).resolve().parent
DIST_DIR = DESKTOP_DIR / "dist"
LAUNCH_EXE = DIST_DIR / "launch.exe"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("desktop")

_backend_process: subprocess.Popen | None = None


def _build_launch_exe() -> bool:
    """Create a bundled launch.exe under desktop/dist when it is missing."""
    if getattr(sys, "_MEIPASS", None):
        return True

    if LAUNCH_EXE.is_file():
        logger.info("Executable already exists at %s", LAUNCH_EXE)
        return True

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    python_cmd = _find_python_executable()

    if importlib.util.find_spec("PyInstaller") is None:
        logger.info("PyInstaller is missing; installing it into the active Python environment")
        install = subprocess.run(
            [python_cmd, "-m", "pip", "install", "pyinstaller"],
            capture_output=True,
            text=True,
            cwd=str(DESKTOP_DIR),
        )
        if install.returncode != 0:
            logger.error("PyInstaller install failed: %s", install.stderr.strip() or install.stdout.strip())
            return False

    logger.info("Building desktop executable at %s", LAUNCH_EXE)
    build = subprocess.run(
        [
            python_cmd,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            "launch",
            str(DESKTOP_DIR / "launch.py"),
        ],
        capture_output=True,
        text=True,
        cwd=str(DESKTOP_DIR),
    )

    if build.returncode != 0:
        if build.stdout.strip():
            logger.error(build.stdout.strip())
        if build.stderr.strip():
            logger.error(build.stderr.strip())
        logger.error("Failed to build launch.exe")
        return False

    if LAUNCH_EXE.is_file():
        logger.info("Created %s", LAUNCH_EXE)
        return True

    alt_path = DIST_DIR / "launch.exe"
    if alt_path.is_file():
        logger.info("Created %s", alt_path)
        return True

    logger.warning("PyInstaller completed but launch.exe was not found in %s", DIST_DIR)
    return False


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
    uvicorn_available = importlib.util.find_spec("uvicorn") is not None
    hypercorn_available = importlib.util.find_spec("hypercorn") is not None

    if uvicorn_available:
        uvicorn_cmd = [python_cmd, "-m", "uvicorn", "app.main:app", "--host", HOST, "--port", str(PORT)]
        logger.info("Starting backend with uvicorn")
        process = _start_backend_process(uvicorn_cmd)
        if process is not None:
            process.wait()
            return

    if hypercorn_available:
        hypercorn_cmd = [python_cmd, "-m", "hypercorn", "app.main:app", "--bind", f"{HOST}:{PORT}"]
        logger.info("Starting backend with hypercorn")
        process = _start_backend_process(hypercorn_cmd)
        if process is not None:
            process.wait()
            return

    if not uvicorn_available and not hypercorn_available:
        logger.error("No ASGI server package is installed. Install requirements.txt or requirements-32bit.txt first.")
    else:
        logger.error("Could not start backend server with the available ASGI servers")
    return


def _should_launch_app() -> bool:
    return "--launch-app" in sys.argv or "--run-app" in sys.argv or getattr(sys, "_MEIPASS", None) is not None


def main() -> int:
    if not _should_launch_app() and not getattr(sys, "_MEIPASS", None):
        built = _build_launch_exe()
        if built:
            logger.info("Desktop build complete. Run %s manually to open the app.", LAUNCH_EXE)
            return 0
        return 1

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
