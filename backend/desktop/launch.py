"""Desktop launcher for the Document Processing app.

This script starts the FastAPI backend in a background thread and opens the app
in a native Windows window using pywebview. It is suitable for packaging into a
PyInstaller EXE for local desktop deployment.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.chdir(BACKEND_ROOT)


def start_backend() -> None:
    """Run the FastAPI app on localhost:8000 in a background thread."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )


def main() -> None:
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    # Give uvicorn time to start before opening the window.
    time.sleep(2)

    import webview

    frontend_dist = BACKEND_ROOT.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        url = "http://127.0.0.1:8000"
    else:
        url = "http://127.0.0.1:8000/health"

    window = webview.create_window(
        "Document Processing POC",
        url,
        width=1400,
        height=900,
        resizable=True,
        fullscreen=False,
    )
    webview.start(debug=False)
    return window


if __name__ == "__main__":
    main()
