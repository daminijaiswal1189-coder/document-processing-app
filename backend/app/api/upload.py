from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.upload import UploadResponse
from app.services.upload_service import UploadService

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    try:
        return await UploadService().save_uploaded_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
