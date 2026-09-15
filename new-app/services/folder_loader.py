from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from config.settings import MAX_FILE_BYTES, MAX_FILES


def load_pdfs_from_folder(raw_path: str) -> tuple[list[tuple[str, bytes]], list[str]]:
    """Read PDFs and the Val Assembly Excel from a Valuation Package folder."""
    path = Path(raw_path.strip()).expanduser()
    try:
        path = path.resolve()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid folder path: {exc}") from exc
    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Folder not found: {raw_path}")

    skipped: list[str] = []
    source_paths: list[Path] = []
    for item in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_file() or item.name.startswith("~$") or item.name.startswith("."):
            continue
        if item.suffix.lower() in {".pdf", ".xlsx", ".xls"}:
            source_paths.append(item)
        else:
            skipped.append(item.name)

    pdf_paths = [item for item in source_paths if item.suffix.lower() == ".pdf"]
    if not pdf_paths:
        raise HTTPException(status_code=400, detail=f"No PDF files in folder: {path}")
    if len(pdf_paths) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} PDF files")

    uploads: list[tuple[str, bytes]] = []
    for pdf in source_paths:
        data = pdf.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"{pdf.name} exceeds {MAX_FILE_BYTES // (1024 * 1024)} MB limit",
            )
        if not data:
            raise HTTPException(status_code=400, detail=f"{pdf.name} is empty")
        uploads.append((pdf.name, data))

    warnings = [
        f"Skipped non-PDF (convert to PDF before combine): {name}" for name in skipped
    ]
    warnings.append(f"Loaded {len(uploads)} PDF(s) from {path}")
    return uploads, warnings
