import logging
from pathlib import Path

from app.services.pdf.pdf_config import (
    REQUIRED_ANSWERS,
    REQUIRED_HEADINGS,
    REQUIRED_QUESTIONS,
)
from app.services.pdf.pdf_reader import PdfReaderService

logger = logging.getLogger(__name__)


class PdfValidatorService:
    def __init__(self) -> None:
        self._reader = PdfReaderService()

    def validate_uploaded_file(self, file_path: Path) -> dict:
        raw_text = self._reader.extract_text(file_path)
        normalized = self._reader.normalize(raw_text)

        missing_headings = self._find_missing(REQUIRED_HEADINGS, normalized)
        missing_questions = self._find_missing(REQUIRED_QUESTIONS, normalized)
        missing_answers = self._find_missing(REQUIRED_ANSWERS, normalized)

        passed = not (missing_headings or missing_questions or missing_answers)
        status = "PASS" if passed else "FAIL"

        logger.info(
            "PDF validation %s for %s (missing: h=%s q=%s a=%s)",
            status,
            file_path.name,
            len(missing_headings),
            len(missing_questions),
            len(missing_answers),
        )

        return {
            "status": status,
            "missing_headings": missing_headings,
            "missing_questions": missing_questions,
            "missing_answers": missing_answers,
            "page_text_length": len(raw_text),
        }

    def _find_missing(self, required: list[str], normalized_document: str) -> list[str]:
        missing: list[str] = []
        for item in required:
            if not item or not item.strip():
                continue
            needle = self._reader.normalize(item)
            if needle not in normalized_document:
                missing.append(item)
        return missing
