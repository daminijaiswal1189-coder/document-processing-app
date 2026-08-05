from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.utils.paths import PROCESSED_DIR

router = APIRouter(tags=["download"])

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _is_safe_filename(filename: str) -> bool:
    if not filename or filename != filename.strip():
        return False
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    return filename.lower().endswith(".xlsx")


@router.get("/download/{filename}")
def download_processed_excel(filename: str) -> FileResponse:
    if not _is_safe_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = PROCESSED_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Processed file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=XLSX_MEDIA_TYPE,
    )
