"""
Persist incoming documents so process endpoints use a stable storage layout.

Flow (browser upload):
  POST /upload → save_uploaded_file → UUID filename in storage/uploads.

Flow (server path):
  POST /upload/path → register_local_path → copy allowed path → same storage layout.

Both return UploadResponse with ``filename`` used by /process/* endpoints.
"""

import logging
import shutil
from uuid import uuid4

from fastapi import UploadFile

from app.models.upload import UploadData, UploadResponse
from app.utils.file_type import detect_file_type, is_allowed_extension
from app.utils.path_security import resolve_allowed_document_path
from app.utils.paths import UPLOADS_DIR, ensure_uploads_dir

logger = logging.getLogger(__name__)


class UploadService:
    """
    Writes documents to storage/uploads and returns metadata for the frontend.

    Processing APIs never read arbitrary paths; they only read ``data.filename``
    under UPLOADS_DIR after upload or path registration.
    """

    def register_local_path(self, file_path: str) -> UploadResponse:
        """
        Copy a file from an authorized server path into storage/uploads.

        Args:
            file_path: Absolute or project-relative path (validated by path_security).

        Returns:
            Same shape as save_uploaded_file, plus source_path in UploadData.
        """
        source = resolve_allowed_document_path(file_path)

        if not is_allowed_extension(source.name):
            raise ValueError(
                f"Invalid file type. Allowed: .xlsx, .xls, .docx, .pdf (got {source.name})"
            )

        suffix = source.suffix.lower()
        stored_filename = f"{uuid4()}{suffix}"
        dest_path = UPLOADS_DIR / stored_filename

        ensure_uploads_dir()
        shutil.copy2(source, dest_path)

        document_type = detect_file_type(source.name)
        logger.info(
            "Registered local path %s as %s (%s)",
            source,
            stored_filename,
            document_type,
        )

        return UploadResponse(
            message="Ready for processing",
            status="success",
            code=200,
            error=None,
            data=UploadData(
                filename=stored_filename,
                document_type=document_type,
                file_path=str(dest_path),
                source_path=str(source),
            ),
        )

    async def save_uploaded_file(self, file: UploadFile) -> UploadResponse:
        """
        Save multipart upload body to storage/uploads with a UUID filename.

        Args:
            file: FastAPI UploadFile from POST /upload.

        Returns:
            UploadResponse including document_type for routing on the result page.
        """
        if not file.filename:
            raise ValueError("File name is required")

        if not is_allowed_extension(file.filename):
            raise ValueError(
                f"Invalid file type. Allowed: .xlsx, .xls, .docx, .pdf (got {file.filename})"
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
