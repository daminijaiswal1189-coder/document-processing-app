"""
Word (.docx) content validation against configurable required strings.

Mirrors PdfValidatorService: extract → normalize → find missing → PASS/FAIL.
"""

import logging
from pathlib import Path

from app.services.word.word_config import (
    REQUIRED_ANSWERS,
    REQUIRED_HEADINGS,
    REQUIRED_QUESTIONS,
)
from app.services.word.word_reader import WordReaderService

logger = logging.getLogger(__name__)


class WordValidatorService:
    """Orchestrates Word reading and required-content checks for POST /process/word."""

    def __init__(self) -> None:
        self._reader = WordReaderService()

    def validate_uploaded_file(self, file_path: Path) -> dict:
        """
        Validate one .docx on disk.

        Returns:
            Dict with status, missing_* lists, paragraph_count, document_text_length.
        """
        raw_text, paragraph_count = self._reader.extract_text(file_path)
        normalized = self._reader.normalize(raw_text)

        missing_headings = self._find_missing(REQUIRED_HEADINGS, normalized)
        missing_questions = self._find_missing(REQUIRED_QUESTIONS, normalized)
        missing_answers = self._find_missing(REQUIRED_ANSWERS, normalized)

        passed = not (missing_headings or missing_questions or missing_answers)
        status = "PASS" if passed else "FAIL"

        logger.info(
            "Word validation %s for %s (missing: h=%s q=%s a=%s)",
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
            "paragraph_count": paragraph_count,
            "document_text_length": len(raw_text),
        }

    def _find_missing(self, required: list[str], normalized_document: str) -> list[str]:
        """Return required strings absent from the normalized document text."""
        missing: list[str] = []
        for item in required:
            if not item or not item.strip():
                continue
            needle = self._reader.normalize(item)
            if needle not in normalized_document:
                missing.append(item)
        return missing
