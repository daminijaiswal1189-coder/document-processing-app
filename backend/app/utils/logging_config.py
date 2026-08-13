"""
Configure application-wide logging.

Flow:
  - Each app load creates backend/logs/backend_YYYY-MM-DD_HH-MM-SS.log.
  - INFO logs go to that file and to stderr (uvicorn terminal).
  - On reload, the previous file handler is closed and a new log file is opened.
"""

import logging
from datetime import datetime
from pathlib import Path

from app.utils.paths import LOGS_DIR

# Shared format for file and console handlers.
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging() -> Path:
    """
    Attach file + console handlers to the root logger.

    Returns:
        Path to the log file created for this process/reload cycle.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOGS_DIR / f"backend_{stamp}.log"

    formatter = logging.Formatter(_LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Replace file handler so each reload gets a fresh log file.
    for handler in list(root.handlers):
        if isinstance(handler, logging.FileHandler):
            root.removeHandler(handler)
            handler.close()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

    return log_path
