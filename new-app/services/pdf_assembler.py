from __future__ import annotations

from fastapi import HTTPException
import fitz

from config.settings import MAX_FILE_BYTES, MAX_FILES


def merge_pdfs(uploads: list[tuple[str, bytes]]) -> fitz.Document:
    """Merge PDFs in list order. Each item is (filename, bytes)."""
    if len(uploads) < 1:
        raise HTTPException(status_code=400, detail="Upload at least one PDF")
    if len(uploads) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} PDF files")

    combined = fitz.open()
    try:
        for name, data in uploads:
            if len(data) > MAX_FILE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"{name} exceeds {MAX_FILE_BYTES // (1024 * 1024)} MB limit",
                )
            if not data:
                raise HTTPException(status_code=400, detail=f"{name} is empty")
            source = fitz.open(stream=data, filetype="pdf")
            try:
                if source.page_count < 1:
                    raise HTTPException(status_code=400, detail=f"{name} has no pages")
                if source.is_encrypted:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{name} is encrypted and cannot be assembled",
                    )
                combined.insert_pdf(source)
            finally:
                source.close()
    except HTTPException:
        combined.close()
        raise
    except Exception:
        combined.close()
        raise
    return combined
