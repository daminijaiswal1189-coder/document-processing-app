"""Pydantic schemas for Word validation (POST /process/word)."""

from pydantic import BaseModel, Field


class WordProcessRequest(BaseModel):
    """Identifies which uploaded .docx to validate."""

    filename: str = Field(..., description="Stored upload filename from POST /upload")


class WordValidationResponse(BaseModel):
    """Word validation outcome returned to the React result page."""

    message: str
    status: str = Field(..., description="PASS or FAIL")
    document_type: str = "word"
    filename: str
    missing_headings: list[str]
    missing_questions: list[str]
    missing_answers: list[str]
    found_headings: list[str]
    found_questions: list[str]
    found_answers: list[str]
    paragraph_count: int = Field(..., description="Number of paragraphs in the document")
    document_text_length: int = Field(
        ..., description="Characters extracted from the Word document"
    )
    processing_time_ms: float = Field(
        ..., description="Server-side validation duration in milliseconds"
    )
