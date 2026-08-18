"""
Excel workbook processing for the POC.

Constants used by ExcelProcessor (column header text, row index, fill color).
On 32-bit Python (common on older Windows), openpyxl is memory-bound (~2GB process
limit), so expensive extras are disabled by default unless overridden via env.
"""

import os
import struct

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

# Light red fill applied to FALSE / NA — only in this one column (header match, case-insensitive).
FALSE_NA_COLUMN_HEADERS = ("match_dob",)
FALSE_NA_FILL_RGB = "FFFFC7CE"

# When Excel is processed via upload, also apply transforms in-place on this workbook.
STATIC_INPLACE_EXCEL_PATH = (
    "/Users/daminijaiswal/Documents/OneDrive_1_11-3-2025/2026helpwc 000006.xlsx"
)

_IS_32BIT = struct.calcsize("P") * 8 == 32


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# Second full-ish pass (data_only) to read formula caches — costly on 32-bit; off by default there.
LOAD_FALSE_NA_DATA_ONLY_CACHE = _env_bool(
    "POC_LOAD_FALSE_NA_CACHE",
    default=not _IS_32BIT,
)

# In-place static path doubles Excel work; off by default on 32-bit.
ENABLE_STATIC_INPLACE_ON_EXCEL_PROCESS = _env_bool(
    "POC_ENABLE_STATIC_INPLACE",
    default=not _IS_32BIT,
)

IS_32BIT_PYTHON = _IS_32BIT
