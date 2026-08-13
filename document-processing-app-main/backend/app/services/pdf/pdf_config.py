"""
Required text fragments for PDF validation (pdf_config).

PdfValidatorService normalizes document and required strings, then checks substring presence.
Edit these lists to match your real PDF template content.
"""

REQUIRED_HEADINGS: list[str] = [
    "Excluded Employees",
    "Eligibility",
]

REQUIRED_QUESTIONS: list[str] = [
    "If your plan excludes Deemed 125 and/or fringe benefits (reimbursements or other expense allowances, moving expenses, deferred compensation and welfare benefits) for plan purposes, did any employee receive Deemed 125 and/or fringe benefits?:",
]

REQUIRED_ANSWERS: list[str] = [
    "Yes",
    "No",
]
