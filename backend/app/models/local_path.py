"""Request body for POST /upload/path."""

from pydantic import BaseModel, Field


class LocalPathUploadRequest(BaseModel):
    """Server filesystem path to copy into storage/uploads."""

    file_path: str = Field(
        ...,
        description="Absolute or project-relative path on the server (e.g. samples/file.xlsx)",
    )
