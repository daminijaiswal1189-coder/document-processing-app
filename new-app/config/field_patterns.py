"""Regex patterns for cover-page and test-summary extraction. Tune when sample PDFs arrive."""

COVER_PATTERNS: dict[str, list[str]] = {
    "plan_number": [
        r"Plan\s*(?:No\.?|Number|#)\s*[:#]?\s*(\d{3,10})",
        r"\bPlan\s+(\d{5,10})\b",
    ],
    "plan_name": [
        r"Plan\s*Name\s*[:#]?\s*(.+)",
    ],
    "company_name": [
        r"Company\s*Name\s*[:#]?\s*(.+)",
        r"Employer\s*Name\s*[:#]?\s*(.+)",
        r"Sponsor\s*[:#]?\s*(.+)",
    ],
    "company_address": [
        r"(?:Company\s*)?Address\s*[:#]?\s*(.+)",
    ],
    "plan_year": [
        r"Plan\s*Year\s*[:#]?\s*(\d{1,2}/\d{1,2}/\d{4})\s*[-–to]+\s*(\d{1,2}/\d{1,2}/\d{4})",
        r"Plan\s*Year\s*Ending\s*[:#]?\s*(\d{1,2}/\d{1,2}/\d{4})",
        r"PYE\s*[:#]?\s*(\d{1,2}/\d{1,2}/\d{4})",
        r"(\d{1,2}/\d{1,2}/\d{4})\s*[-–]\s*(\d{1,2}/\d{1,2}/\d{4})",
    ],
}

TEST_PATTERNS: dict[str, list[str]] = {
    "testing_method": [
        r"\b(CURRENT|PRIOR)\s+METHOD\b",
        r"Testing\s*Method\s*[:#]?\s*(CURRENT|PRIOR)",
        r"\b(CURRENT|PRIOR)\b",
    ],
    "top_heavy_percent": [
        r"Top\s*Heavy\s*(?:Percent(?:age)?|Ratio)?\s*[:#]?\s*(\d+(?:\.\d+)?)\s*%?",
        r"Top-Heavy\s*[:#]?\s*(\d+(?:\.\d+)?)\s*%",
    ],
    "adp_qnec": [
        r"ADP\s*QNEC\s*[:#]?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
    ],
    "acp_qnec": [
        r"ACP\s*QNEC\s*[:#]?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
    ],
    "deferral_refund": [
        r"Deferral\s*Refund\s*[:#]?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
    ],
    "match_refund": [
        r"Match(?:ing)?\s*Refund\s*[:#]?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
    ],
}

FAIL_FLAGS: dict[str, list[str]] = {
    "adp_failed": [r"\bADP\b.{0,80}\bFAIL", r"ADP\s+Test\s*:\s*Fail"],
    "acp_failed": [r"\bACP\b.{0,80}\bFAIL", r"ACP\s+Test\s*:\s*Fail"],
    "fail_402g": [r"402\s*\(?g\)?.{0,80}\bFAIL", r"\bFail(?:ed)?\s+402"],
    "fail_415": [r"\b415\b.{0,80}\bFAIL", r"\bFail(?:ed)?\s+415"],
    "returns_required": [r"Returns?\s+Required", r"Refunds?\s+Required"],
    "variance_report": [r"\bVariance\s+Report\b"],
    "after_12_months": [r"After\s+12\s+Months", r"more than 12 months"],
}
