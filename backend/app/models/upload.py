from pydantic import BaseModel


class UploadData(BaseModel):
    filename: str
    document_type: str
    file_path: str


class UploadResponse(BaseModel):
    message: str
    status: str
    code: int
    error: str | None
    data: UploadData
