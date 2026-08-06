"""Pydantic schemas for upload endpoints (POST /upload and POST /upload/path)."""

from pydantic import BaseModel


class UploadData(BaseModel):
    """
    Core upload metadata returned to the frontend.

    ``filename`` is the key used by all /process/* endpoints.
    ``document_type`` drives which process API the result page calls.
    """

    filename: str
    document_type: str
    file_path: str
    source_path: str | None = None


class UploadResponse(BaseModel):
    """Standard envelope for successful upload or path registration."""

    message: str
    status: str
    code: int
    error: str | None
    data: UploadData
