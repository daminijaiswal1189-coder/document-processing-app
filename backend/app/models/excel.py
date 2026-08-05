from pydantic import BaseModel, Field


class ExcelProcessRequest(BaseModel):
    filename: str = Field(..., description="Stored upload filename (UUID.xlsx)")


class ExcelProcessDetails(BaseModel):
    sheet_name: str
    entry_column_index: int
    new_column_index: int
    new_column_header: str
    rows_updated: int


class ExcelProcessResponse(BaseModel):
    message: str
    processed_filename: str
    download_url: str
    details: ExcelProcessDetails
