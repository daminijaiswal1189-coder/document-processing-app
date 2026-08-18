"""
Required text fragments for PDF validation (pdf_config).

PdfValidatorService normalizes document and required strings, then checks substring presence.
Edit these lists to match your real PDF template content.
"""

REQUIRED_HEADINGS: list[str] = [
    "Introduction",
    "Eligibility",
    "Summary",
]

REQUIRED_QUESTIONS: list[str] = [
    "What is the plan year?",
    "Who is eligible?",
]

REQUIRED_ANSWERS: list[str] = [
    "Yes",
    "No",
    "Not applicable",
]
