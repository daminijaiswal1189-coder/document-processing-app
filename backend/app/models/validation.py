"""Pydantic schemas for PDF validation (POST /process/pdf)."""

from pydantic import BaseModel, Field


class DocumentProcessRequest(BaseModel):
    """Shared request shape: stored upload basename for PDF (and legacy reuse)."""

    filename: str = Field(..., description="Stored upload filename from POST /upload")


class PdfValidationResponse(BaseModel):
    """PDF validation outcome returned to the React result page."""

    message: str
    status: str = Field(..., description="PASS or FAIL")
    document_type: str = "pdf"
    filename: str
    missing_headings: list[str]
    missing_questions: list[str]
    missing_answers: list[str]
    page_text_length: int = Field(..., description="Characters extracted from the PDF")
    processing_time_ms: float = Field(..., description="Server-side validation duration in milliseconds")
