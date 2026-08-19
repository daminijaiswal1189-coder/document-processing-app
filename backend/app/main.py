"""
FastAPI application entry point.

Flow:
  1. Configure logging (console + timestamped file under backend/logs/).
  2. Register HTTP routers: upload, excel, pdf, word, download.
  3. On startup, ensure storage and logs directories exist.
  4. Optionally serve the React production build (frontend/dist) for desktop / single-port use.
"""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.download import router as download_router
from app.api.excel import router as excel_router
from app.api.pdf import router as pdf_router
from app.api.upload import router as upload_router
from app.api.word import router as word_router
from app.utils.logging_config import setup_logging
from app.utils.paths import BACKEND_ROOT, ensure_logs_dir, ensure_processed_dir, ensure_uploads_dir

log_file = setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Document Validation & Excel Processing POC",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        # Desktop UI static server (pywebview launcher)
        "http://127.0.0.1:17890",
        "http://localhost:17890",
    ],
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(excel_router)
app.include_router(pdf_router)
app.include_router(word_router)
app.include_router(download_router)

# React production build (desktop / single-port). Dev can still use Vite on :5173.
# In a PyInstaller build the Python package can be loaded from the embedded
# archive, so ``__file__`` is not a reliable way to locate bundled assets.
# PyInstaller exposes their extracted directory through ``_MEIPASS``.
_BUNDLED_ROOT = getattr(sys, "_MEIPASS", None)
FRONTEND_DIST = (
    Path(_BUNDLED_ROOT) / "frontend" / "dist"
    if _BUNDLED_ROOT
    else BACKEND_ROOT.parent / "frontend" / "dist"
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe: returns ok when the API process is running."""
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    """Create required folders before handling traffic."""
    ensure_uploads_dir()
    ensure_processed_dir()
    ensure_logs_dir()
    logger.info("Backend started")
    logger.info("Writing logs to %s", log_file)
    if FRONTEND_DIST.is_dir():
        logger.info("Serving frontend from %s", FRONTEND_DIST)
    else:
        logger.warning(
            "frontend/dist not found — run 'npm run build' in frontend/ for desktop UI"
        )


def _mount_frontend() -> None:
    if not FRONTEND_DIST.is_dir():
        return
    assets = FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

    @app.get("/")
    def frontend_index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}")
    def frontend_spa(full_path: str) -> FileResponse:
        """SPA fallback for client routes such as /result (GET only)."""
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


_mount_frontend()
