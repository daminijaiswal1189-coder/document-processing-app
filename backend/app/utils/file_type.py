"""
Map file extensions to document types returned to the frontend.

Used after upload/path registration so the UI knows whether to call
/process/excel, /process/pdf, or /process/word.
"""

from pathlib import Path

# Extensions accepted by POST /upload and POST /upload/path.
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".docx", ".pdf"}

# Values stored in UploadData.document_type and used by the React result page.
EXTENSION_TO_TYPE = {
    ".xlsx": "excel",
    ".xls": "excel",
    ".docx": "word",
    ".pdf": "pdf",
}


def detect_file_type(filename: str) -> str:
    """
    Return logical document type for a filename.

    Falls back to ``unknown`` if the extension is not in EXTENSION_TO_TYPE.
    """
    ext = Path(filename).suffix.lower()
    return EXTENSION_TO_TYPE.get(ext, "unknown")


def is_allowed_extension(filename: str) -> bool:
    """True when the filename ends with an allowed POC extension."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS
