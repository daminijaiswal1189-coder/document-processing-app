"""
HTTP routes for ingesting documents before processing.

POST /upload       — multipart file from browser.
POST /upload/path  — copy from a path on the server (see path_security).
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.local_path import LocalPathUploadRequest
from app.models.upload import UploadResponse
from app.services.upload_service import UploadService

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    """
    Accept a single file upload and store it under storage/uploads.

    The response ``data.filename`` is passed to /process/excel|pdf|word on the result page.
    """
    try:
        return await UploadService().save_uploaded_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload/path", response_model=UploadResponse)
def upload_from_local_path(body: LocalPathUploadRequest) -> UploadResponse:
    """
    Register a document that already exists on the server filesystem.

    Copies into storage/uploads so downstream processing matches the upload flow.
    """
    try:
        return UploadService().register_local_path(body.file_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
