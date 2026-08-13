"""
FastAPI application entry point.

Flow:
  1. Configure logging (console + timestamped file under backend/logs/).
  2. Register HTTP routers: upload, excel, pdf, word, download.
  3. On startup, ensure storage and logs directories exist.
  4. Frontend calls these endpoints after the user uploads or registers a server path.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.download import router as download_router
from app.api.excel import router as excel_router
from app.api.pdf import router as pdf_router
from app.api.upload import router as upload_router
from app.api.word import router as word_router
from app.utils.logging_config import setup_logging
from app.utils.paths import ensure_logs_dir, ensure_processed_dir, ensure_uploads_dir

# Path to the active log file for this process (also printed on startup).
log_file = setup_logging()
logger = logging.getLogger(__name__)

# OpenAPI app instance served by uvicorn.
app = FastAPI(
    title="Document Validation & Excel Processing POC",
    version="0.1.0",
)

# Allow the Vite dev server to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(excel_router)
app.include_router(pdf_router)
app.include_router(word_router)
app.include_router(download_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe: returns ok when the API process is running."""
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    """
    Create required folders before handling traffic.

    Uploads land in storage/uploads; Excel output in storage/processed;
    logs in backend/logs.
    """
    ensure_uploads_dir()
    ensure_processed_dir()
    ensure_logs_dir()
    logger.info("Backend started")
    logger.info("Writing logs to %s", log_file)
