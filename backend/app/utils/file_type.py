from pathlib import Path

ALLOWED_EXTENSIONS = {".xlsx", ".docx", ".pdf"}

EXTENSION_TO_TYPE = {
    ".xlsx": "excel",
    ".docx": "word",
    ".pdf": "pdf",
}


def detect_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return EXTENSION_TO_TYPE.get(ext, "unknown")


def is_allowed_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS
