"""
Excel processing HTTP API.

Flow:
  Client sends stored upload filename → read from UPLOADS_DIR → ExcelProcessor →
  write processed_<filename> to PROCESSED_DIR → return download_url and details.
"""

import logging
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.excel import ExcelProcessDetails, ExcelProcessRequest, ExcelProcessResponse
from app.services.excel.excel_processor import ExcelProcessor
from app.services.excel.static_inplace_excel import apply_changes_to_static_workbook
from app.services.storage_cleanup import cleanup_after_successful_process
from app.utils.paths import PROCESSED_DIR, UPLOADS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["excel"])


def _processed_filename(upload_filename: str) -> str:
    """Processed downloads are always .xlsx (including when upload was legacy .xls)."""
    stem = Path(upload_filename).stem
    return f"processed_{stem}.xlsx"


_EXCEL_UPLOAD_SUFFIXES = (".xlsx", ".xls")


@router.post("/process/excel", response_model=ExcelProcessResponse)
def process_excel(body: ExcelProcessRequest) -> ExcelProcessResponse:
    """
    Process an uploaded .xlsx or legacy .xls: add POC Status column; output is .xlsx.

    Args:
        body.filename: UUID-based name from UploadResponse.data.filename.

    Returns:
        Download URL and processing metrics for the frontend result page.
    """
    filename = body.filename.strip()
    lower = filename.lower()
    if not lower.endswith(_EXCEL_UPLOAD_SUFFIXES):
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx and .xls files can be processed",
        )

    source_path = UPLOADS_DIR / filename
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    output_name = _processed_filename(filename)
    output_path = PROCESSED_DIR / output_name

    try:
        started = time.perf_counter()
        result = ExcelProcessor().process(source_path, output_path)
        inplace = apply_changes_to_static_workbook()
        processing_time_ms = (time.perf_counter() - started) * 1000
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Excel processing failed for %s", filename)
        raise HTTPException(status_code=500, detail="Excel processing failed") from exc

    cleanup_after_successful_process(filename)

    message = "Excel processed successfully"
    if inplace and inplace.get("inplace_updated"):
        message = (
            "Excel processed successfully; static workbook updated in place at "
            f"{inplace.get('inplace_path')}"
        )

    return ExcelProcessResponse(
        message=message,
        processed_filename=output_name,
        download_url=f"/download/{output_name}",
        processing_time_ms=round(processing_time_ms, 2),
        details=ExcelProcessDetails(
            sheet_name=str(result["sheet_name"]),
            new_column_index=int(result["new_column_index"]),
            new_column_header=str(result["new_column_header"]),
            rows_updated=int(result["rows_updated"]),
            extract_sheet_name=str(result.get("extract_sheet_name", "Name and SSN")),
            name_ssn_rows=int(result.get("name_ssn_rows", 0)),
            static_inplace_path=(
                str(inplace["inplace_path"]) if inplace and inplace.get("inplace_path") else None
            ),
            static_inplace_updated=bool(inplace and inplace.get("inplace_updated")),
        ),
    )
