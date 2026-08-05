from pydantic import BaseModel, Field


class DocumentProcessRequest(BaseModel):
    filename: str = Field(..., description="Stored upload filename from POST /upload")


class PdfValidationResponse(BaseModel):
    message: str
    status: str = Field(..., description="PASS or FAIL")
    document_type: str = "pdf"
    filename: str
    missing_headings: list[str]
    missing_questions: list[str]
    missing_answers: list[str]
    page_text_length: int = Field(..., description="Characters extracted from the PDF")
