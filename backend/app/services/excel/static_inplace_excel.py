"""
Apply Excel POC transforms directly on a fixed server-side workbook path.

Used when POST /process/excel runs: upload still produces a processed download copy,
and this module updates the configured OneDrive/local file in place.
"""

import logging
import os
import tempfile
from pathlib import Path

from app.services.excel.excel_config import (
    ENABLE_STATIC_INPLACE_ON_EXCEL_PROCESS,
    STATIC_INPLACE_EXCEL_PATH,
)
from app.services.excel.excel_processor import ExcelProcessor
from app.utils.path_security import resolve_allowed_document_path

logger = logging.getLogger(__name__)


def apply_changes_to_static_workbook() -> dict[str, str | int | bool] | None:
    """
    Load the configured static Excel path, run POC column / highlight / Name-SSN tab logic,
    and save back to the same file.

    Returns:
        Transform metadata from ExcelProcessor, plus ``inplace_path`` and ``inplace_updated``,
        or None when disabled or the configured path is missing.
    """
    if not ENABLE_STATIC_INPLACE_ON_EXCEL_PROCESS:
        logger.debug("Static in-place Excel update is disabled")
        return None

    try:
        target = resolve_allowed_document_path(STATIC_INPLACE_EXCEL_PATH)
    except ValueError as exc:
        logger.warning("Static in-place Excel path skipped: %s", exc)
        return None

    processor = ExcelProcessor()
    result = processor.process_inplace(target)
    return {
        **result,
        "inplace_path": str(target),
        "inplace_updated": True,
    }
