"""Pydantic schemas for POST /process/excel request and response."""

from pydantic import BaseModel, Field


class ExcelProcessRequest(BaseModel):
    """Identifies which uploaded .xlsx to process (storage/uploads basename)."""

    filename: str = Field(..., description="Stored upload filename (UUID.xlsx or UUID.xls)")


class ExcelProcessDetails(BaseModel):
    """Outcome of ExcelProcessor.run — shown on the result page."""

    sheet_name: str
    new_column_index: int
    new_column_header: str
    rows_updated: int
    extract_sheet_name: str = Field(
        default="Name and SSN",
        description="Worksheet tab containing name and ssn columns",
    )
    name_ssn_rows: int = Field(
        default=0,
        description="Data rows copied to the name/ssn tab",
    )
    static_inplace_path: str | None = Field(
        default=None,
        description="Server path updated in place when static in-place processing ran",
    )
    static_inplace_updated: bool = Field(
        default=False,
        description="True when the configured static workbook was saved in place",
    )


class ExcelProcessResponse(BaseModel):
    """Full Excel API response including download link and timing."""

    message: str
    processed_filename: str
    download_url: str
    processing_time_ms: float = Field(..., description="Server-side processing duration in milliseconds")
    details: ExcelProcessDetails
