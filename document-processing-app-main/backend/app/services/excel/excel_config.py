"""
Excel workbook processing for the POC.

Constants used by ExcelProcessor (column header text, row index, fill color).
Adjust these when the business rules for the POC column change.
"""

HEADER_ROW = 1
NEW_COLUMN_HEADER = "POC Status"
NEW_COLUMN_DEFAULT_VALUE = "Processed"

# New worksheet: copied Name / SSN columns from the active sheet.
EXTRACT_SHEET_NAME = "Name and SSN"
EXTRACT_TAB_NAME_HEADER = "name"
EXTRACT_TAB_SSN_HEADER = "ssn"

# Header text on the source sheet (row 1) used to locate columns.
SOURCE_NAME_HEADERS = ("name",)
SOURCE_SSN_HEADERS = ("ss#", "ssn", "social security", "social security number")

# Light red fill applied to cells whose value is FALSE or NA on processed rows.
FALSE_NA_FILL_RGB = "FFFFC7CE"

# When Excel is processed via upload, also apply transforms in-place on this workbook.
STATIC_INPLACE_EXCEL_PATH = (
    r"C:\Users\703389651\Desktop\Sample_testhelp\2024helpwc 000012.xlsx"
)
ENABLE_STATIC_INPLACE_ON_EXCEL_PROCESS = True
