"""
Apply Excel POC transforms directly on a fixed server-side workbook path.

Used when POST /process/excel runs: upload still produces a processed download copy,
and this module optionally updates the configured OneDrive/local file in place.

Failures here (missing file, permission denied, locked file) are logged and must
not fail the uploaded-workbook processing response.
"""

import logging

from app.services.excel.excel_config import (
    ENABLE_STATIC_INPLACE_ON_EXCEL_PROCESS,
    STATIC_INPLACE_EXCEL_PATH,
)
from app.services.excel.excel_processor import ExcelProcessor
from app.utils.path_security import resolve_allowed_document_path

logger = logging.getLogger(__name__)


def apply_changes_to_static_workbook() -> dict[str, str | int | bool] | None:
    """
    Load the configured static Excel path, run POC transforms, and save in place.

    Returns:
        Metadata with ``inplace_updated`` True on success; dict with
        ``inplace_updated`` False and ``inplace_error`` on failure; or None when disabled.
    """
    if not ENABLE_STATIC_INPLACE_ON_EXCEL_PROCESS:
        logger.debug("Static in-place Excel update is disabled")
        return None

    try:
        target = resolve_allowed_document_path(STATIC_INPLACE_EXCEL_PATH)
    except ValueError as exc:
        logger.warning("Static in-place Excel path skipped: %s", exc)
        return {
            "inplace_path": STATIC_INPLACE_EXCEL_PATH,
            "inplace_updated": False,
            "inplace_error": str(exc),
        }

    try:
        result = ExcelProcessor().process_inplace(target)
        return {
            **result,
            "inplace_path": str(target),
            "inplace_updated": True,
        }
    except PermissionError as exc:
        logger.warning(
            "Static in-place Excel update skipped (permission denied): %s — %s",
            target,
            exc,
        )
        return {
            "inplace_path": str(target),
            "inplace_updated": False,
            "inplace_error": f"Permission denied: {exc}",
        }
    except OSError as exc:
        logger.warning(
            "Static in-place Excel update skipped (OS error): %s — %s",
            target,
            exc,
        )
        return {
            "inplace_path": str(target),
            "inplace_updated": False,
            "inplace_error": f"OS error: {exc}",
        }
    except Exception as exc:
        logger.exception(
            "Static in-place Excel update failed; uploaded workbook result is unaffected: %s",
            target,
        )
        return {
            "inplace_path": str(target),
            "inplace_updated": False,
            "inplace_error": str(exc),
        }
