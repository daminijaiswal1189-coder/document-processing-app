"""
Filesystem locations used by the POC backend.

All paths are derived from BACKEND_ROOT (the backend/ directory) so the app
works regardless of the current working directory when uvicorn starts.
"""

from pathlib import Path

# backend/ — parent of the app/ package.
BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Incoming copies of user files (upload or register-from-path).
UPLOADS_DIR = BACKEND_ROOT / "storage" / "uploads"

# Excel outputs written by ExcelProcessor (downloaded via GET /download/...).
PROCESSED_DIR = BACKEND_ROOT / "storage" / "processed"

# Timestamped log files from setup_logging().
LOGS_DIR = BACKEND_ROOT / "logs"


def ensure_uploads_dir() -> None:
    """Create storage/uploads if missing (called at startup and before save)."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_processed_dir() -> None:
    """Create storage/processed if missing (called at startup and before Excel save)."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def ensure_logs_dir() -> None:
    """Create backend/logs if missing (called at startup)."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
