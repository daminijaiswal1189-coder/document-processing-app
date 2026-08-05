import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class PdfReaderService:
    def extract_text(self, file_path: Path) -> str:
        if not file_path.is_file():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        try:
            import fitz  # PyMuPDF
        except ImportError:
            fitz = None

        if fitz is not None:
            parts: list[str] = []
            with fitz.open(file_path) as document:
                logger.info("Reading PDF %s (%s pages)", file_path.name, document.page_count)
                for page in document:
                    parts.append(page.get_text())
            return "\n".join(parts)

        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "No PDF library available. Install pymupdf or pypdf."
            ) from exc

        logger.info("Reading PDF with pypdf: %s", file_path.name)
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    @staticmethod
    def normalize(text: str) -> str:
        collapsed = re.sub(r"\s+", " ", text or "").strip().lower()
        return collapsed
