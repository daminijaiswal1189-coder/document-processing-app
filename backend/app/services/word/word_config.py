"""
Required text fragments for Word validation (word_config).

Same matching rules as PDF: normalized substring search via WordValidatorService.
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
