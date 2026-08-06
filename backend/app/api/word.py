"""
Word (.docx) validation HTTP API.

Same contract as PDF: extract text, check required phrases from word_config, PASS/FAIL.
"""

import logging
import time

from fastapi import APIRouter, HTTPException

from app.models.word import WordProcessRequest, WordValidationResponse
from app.services.word.word_validator import WordValidatorService
from app.utils.paths import UPLOADS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["word"])


@router.post("/process/word", response_model=WordValidationResponse)
def process_word(body: WordProcessRequest) -> WordValidationResponse:
    """
    Validate an uploaded Word document against required headings, questions, and answers.

    Args:
        body.filename: Stored .docx name under storage/uploads.
    """
    filename = body.filename.strip()
    if not filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files can be validated")

    source_path = UPLOADS_DIR / filename
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    try:
        started = time.perf_counter()
        result = WordValidatorService().validate_uploaded_file(source_path)
        processing_time_ms = (time.perf_counter() - started) * 1000
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Word validation failed for %s", filename)
        raise HTTPException(status_code=500, detail="Word validation failed") from exc

    status = result["status"]
    return WordValidationResponse(
        message="Word validation completed"
        if status == "PASS"
        else "Word validation failed — see missing items",
        status=status,
        filename=filename,
        missing_headings=result["missing_headings"],
        missing_questions=result["missing_questions"],
        missing_answers=result["missing_answers"],
        paragraph_count=int(result["paragraph_count"]),
        document_text_length=int(result["document_text_length"]),
        processing_time_ms=round(processing_time_ms, 2),
    )
