import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.excel import ExcelProcessDetails, ExcelProcessRequest, ExcelProcessResponse
from app.services.excel.excel_processor import ExcelProcessor
from app.utils.paths import PROCESSED_DIR, UPLOADS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["excel"])


def _processed_filename(upload_filename: str) -> str:
    return f"processed_{upload_filename}"


@router.post("/process/excel", response_model=ExcelProcessResponse)
def process_excel(body: ExcelProcessRequest) -> ExcelProcessResponse:
    filename = body.filename.strip()
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files can be processed")

    source_path = UPLOADS_DIR / filename
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    output_name = _processed_filename(filename)
    output_path = PROCESSED_DIR / output_name

    try:
        result = ExcelProcessor().process(source_path, output_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Excel processing failed for %s", filename)
        raise HTTPException(status_code=500, detail="Excel processing failed") from exc

    return ExcelProcessResponse(
        message="Excel processed successfully",
        processed_filename=output_name,
        download_url=f"/download/{output_name}",
        details=ExcelProcessDetails(
            sheet_name=str(result["sheet_name"]),
            entry_column_index=int(result["entry_column_index"]),
            new_column_index=int(result["new_column_index"]),
            new_column_header=str(result["new_column_header"]),
            rows_updated=int(result["rows_updated"]),
        ),
    )
