"""
Remove temporary upload copies under storage/uploads after successful processing.

Processed Excel files under storage/processed are kept for repeat download.
"""

import logging

from app.utils.paths import UPLOADS_DIR

logger = logging.getLogger(__name__)

_UPLOAD_SUFFIXES = (".xlsx", ".xls", ".pdf", ".docx")


def _is_safe_basename(filename: str, allowed_suffixes: tuple[str, ...]) -> bool:
    if not filename or filename != filename.strip():
        return False
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in allowed_suffixes)


def delete_upload_file(filename: str) -> bool:
    """Delete one file from storage/uploads if it exists."""
    if not _is_safe_basename(filename, _UPLOAD_SUFFIXES):
        logger.warning("Refusing to delete upload with unsafe name: %r", filename)
        return False
    path = UPLOADS_DIR / filename
    if not path.is_file():
        return False
    path.unlink()
    logger.info("Removed upload from storage: %s", filename)
    return True


def cleanup_after_successful_process(upload_filename: str) -> None:
    """Remove upload copy from storage/uploads after automation completes."""
    delete_upload_file(upload_filename)
