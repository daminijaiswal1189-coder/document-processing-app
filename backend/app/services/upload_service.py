import logging
from uuid import uuid4

from fastapi import UploadFile

from app.models.upload import UploadData, UploadResponse
from app.utils.file_type import detect_file_type, is_allowed_extension
from app.utils.paths import UPLOADS_DIR, ensure_uploads_dir

logger = logging.getLogger(__name__)


class UploadService:
    async def save_uploaded_file(self, file: UploadFile) -> UploadResponse:
        if not file.filename:
            raise ValueError("File name is required")

        if not is_allowed_extension(file.filename):
            raise ValueError(
                f"Invalid file type. Allowed: .xlsx, .docx, .pdf (got {file.filename})"
            )

        suffix = file.filename[file.filename.rfind(".") :].lower()
        stored_filename = f"{uuid4()}{suffix}"
        full_path = UPLOADS_DIR / stored_filename

        content = await file.read()
        if not content:
            raise ValueError("File is empty")

        ensure_uploads_dir()
        full_path.write_bytes(content)

        document_type = detect_file_type(file.filename)
        logger.info(
            "Uploaded %s as %s (%s)", file.filename, stored_filename, document_type
        )

        return UploadResponse(
            message="Ready for processing",
            status="success",
            code=200,
            error=None,
            data=UploadData(
                filename=stored_filename,
                document_type=document_type,
                file_path=str(full_path),
            ),
        )
