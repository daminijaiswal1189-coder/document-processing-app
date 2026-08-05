import logging

from fastapi import APIRouter, HTTPException

from app.models.validation import DocumentProcessRequest, PdfValidationResponse
from app.services.pdf.pdf_validator import PdfValidatorService
from app.utils.paths import UPLOADS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pdf"])


@router.post("/process/pdf", response_model=PdfValidationResponse)
def process_pdf(body: DocumentProcessRequest) -> PdfValidationResponse:
    filename = body.filename.strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files can be validated")

    source_path = UPLOADS_DIR / filename
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    try:
        result = PdfValidatorService().validate_uploaded_file(source_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("PDF validation failed for %s", filename)
        raise HTTPException(status_code=500, detail="PDF validation failed") from exc

    status = result["status"]
    return PdfValidationResponse(
        message="PDF validation completed"
        if status == "PASS"
        else "PDF validation failed — see missing items",
        status=status,
        filename=filename,
        missing_headings=result["missing_headings"],
        missing_questions=result["missing_questions"],
        missing_answers=result["missing_answers"],
        page_text_length=int(result["page_text_length"]),
    )
