from __future__ import annotations

import fitz

COVER_LINES = [
    "March 8, 2026",
    "",
    "Michigan United Credit Union",
    "RE: Michigan United Credit Union 401(k) Savings Plan",
    "",
    "We are pleased to provide you with our completed administrative review of your",
    "qualified retirement plan for the period ending 12/31/2025. This Valuation Report",
    "contains a recap of the finalized census data and results of the IRS required",
    "testing for the plan year.",
    "",
    "Plan Number: 900062",
    "",
    "Please take note of the testing results for this year and refer to the Action",
    "Required section of the Annual Valuation Report.",
]

PARAGRAPHS: list[tuple[str, str]] = [
    (
        "IMMEDIATE ACTION REQUIRED - COMPLIANCE TEST FAILURE",
        "Contribution refunds to participants are required to correct compliance testing failures. "
        "Review the Excess Summary report provided in this package for details and return any "
        "required documents to your local regional office representative.\n"
        "To help ensure returns are processed correctly, please also return Form W-4P documents "
        "for each affected participant.",
    ),
    (
        "IMMEDIATE ACTION REQUIRED - ACP TEST FAILURE",
        "Contribution refunds to participants are required to correct ADP/ACP testing failures. "
        "Review the Excess Summary report provided in this package for details and return any "
        "required documents to your local regional office representative.\n"
        "To help ensure returns are processed correctly, please also return Form W-4P documents "
        "for each affected participant.",
    ),
    (
        "IMMEDIATE ACTION REQUIRED - ADP/ACP TEST FAILURE",
        "Contribution refunds to participants are required to correct ADP/ACP testing failures. "
        "A Qualified Non-Elective Contribution (QNEC) may also be required. Review the Excess "
        "Summary report provided in this package for details and return any required documents "
        "to your local regional office representative.\n"
        "To help ensure returns are processed correctly, please also return Form W-4P documents "
        "for each affected participant.",
    ),
    (
        "IMMEDIATE ACTION REQUIRED - ACP CURRENT METHOD TEST FAILURE - AFTER 12-MONTHS",
        "The ADP/ACP test failure is being corrected more than 12 months after the plan year end. "
        "QNEC and refund amounts apply. Review the Excess Summary report in this package.",
    ),
    (
        "IMMEDIATE ACTION REQUIRED - ACP PRIOR METHOD TEST FAILURE - AFTER 12-MONTHS",
        "The ADP/ACP test failure is being corrected more than 12 months after the plan year end. "
        "Review the Excess Summary report in this package.",
    ),
    (
        "IMMEDIATE ACTION REQUIRED - TOP HEAVY",
        "The plan is top heavy. Review the Top Heavy report included in this package.",
    ),
    (
        "NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME",
        "No contribution refunds or other immediate corrections are required for this plan year.",
    ),
]


def build_valuation_with_action_paragraphs() -> fitz.Document:
    """Cover on page 1; TEST23 Action Required paragraphs on pages 2-4."""
    doc = fitz.open()
    _textbox(doc, "Cover Letter\n\n" + "\n".join(COVER_LINES))
    groups = [PARAGRAPHS[0:2], PARAGRAPHS[2:4], PARAGRAPHS[4:7]]
    for group in groups:
        blocks = ["Action Required", ""]
        for heading, body in group:
            blocks.extend([heading, "", body, ""])
        _textbox(doc, "\n".join(blocks))
    return doc


FAILURE_NOTICE = """Failed Compliance Testing
Excess Return Notice

For current-method testing: Instead of returning excess contribution an employer may make a Qualified Non-Elective Contribution (QNEC) to Non-highly compensated employees (NHCEs).
The amount of the QNEC that is required to pass the ADP/ACP test is $X,XXX,XXX.XX.
The ADP QNEC is $X,XXX,XXX.XX.
The ACP QNEC is $X,XXX,XXX.XX.
Please contact your local regional office representative if you choose an option for a breakdown per participant.

The corrective action necessary in the case of a failure of the ADP/ACP nondiscrimination test is to return Excess Contributions (Employee Deferral/Roth) and/or Excess Aggregate Contributions (Employer Match) to the appropriate Highly Compensated Employees. The actual amounts refunded have been adjusted to include any positive or negative earnings that are attributable to this excess contribution.

A 10% withholding tax will apply unless we receive a Form W-4P informing us that you either do not want any tax withheld or want an additional amount of tax withheld. You can obtain a copy of the W-4P at https://www.irs.gov/pub/irs-pdf/fw4p.pdf

Please note that the Employer is subject to a 10% excise tax on returns made after March 15. If the plan is on an Eligible Automatic Contribution Arrangement (EACA), the 10% excise tax applies to returns made after the applicable deadline.

ADP/ACP test is $X,XXX,XXX.XX
"""


def build_adp_acp_failure_notice_pdf(
    *,
    method: str = "CURRENT",
    adp: str = "Fail",
    acp: str = "Fail",
    returns: str = "Returns Required",
    adp_qnec: str | None = "142,540.41",
    acp_qnec: str | None = "42,814.34",
    include_notice: bool = True,
) -> fitz.Document:
    """TEST23 §C: cover + correction page + Excess Return Notice placeholders."""
    doc = fitz.open()
    cover = [
        "Cover Letter",
        "Plan Number: 444444",
        "Plan Name: Harbor Manufacturing 401(k) Plan",
        "Company Name: Harbor Manufacturing",
        "Address: 10 Harbor Way, Boston, MA 02110",
        "Plan Year: 01/01/2024 - 12/31/2024",
        f"Testing Method: {method}",
        f"ADP Test: {adp}",
        f"ACP Test: {acp}",
        returns,
        "Correction Within 12 Months",
    ]
    _textbox(doc, "\n".join(cover))
    correction = [
        "ADP/ACP",
        "Correction Page",
        f"Testing Method: {method}",
        f"ADP Test: {adp}",
        f"ACP Test: {acp}",
    ]
    if adp_qnec is not None:
        correction.append(f"ADP QNEC: ${adp_qnec}")
    if acp_qnec is not None:
        correction.append(f"ACP QNEC: ${acp_qnec}")
    _textbox(doc, "\n".join(correction))
    if include_notice:
        _textbox(doc, FAILURE_NOTICE)
    return doc


AFTER_12_CURRENT_NOTICE = """Failed Compliance Testing - After 12-months
Current method testing
Excess Return Notice

The ADP/ACP test failure is being corrected after 12 months of the plan year end.
The amount of the QNEC that is required to pass the ADP/ACP test is $X,XXX,XXX.XX.
The ADP QNEC is $X,XXX,XXX.XX.
The ACP QNEC is $X,XXX,XXX.XX.
ADP/ACP test is $X,XXX,XXX.XX
Deferral Contribution of $X,XXX,XXX.XX
Match Contribution of $X,XXX,XXX.XX
"""

AFTER_12_PRIOR_NOTICE = """Failed Compliance Testing - After 12-months
Prior method testing
Excess Return Notice

The ADP/ACP test failure is being corrected after 12 months of the plan year end.
Deferral Contribution of $X,XXX,XXX.XX
Match Contribution of $X,XXX,XXX.XX
"""


def build_after_12_failure_notice_pdf(
    *,
    method: str = "CURRENT",
    adp: str = "Fail",
    acp: str = "Fail",
    returns: str = "Returns Required",
    adp_qnec: str | None = "142,540.41",
    acp_qnec: str | None = "42,814.34",
    deferral: str | None = "17,571.00",
    match: str | None = "116.60",
    include_current_notice: bool = True,
    include_prior_notice: bool = True,
) -> fitz.Document:
    """TEST23 §C.2 / C.3: after-12-months Excess Return Notices plus correction page."""
    doc = fitz.open()
    cover = [
        "Cover Letter",
        "Plan Number: 555555",
        "Plan Name: Harbor Manufacturing 401(k) Plan",
        "Company Name: Harbor Manufacturing",
        "Address: 10 Harbor Way, Boston, MA 02110",
        "Plan Year: 01/01/2024 - 12/31/2024",
        f"Testing Method: {method}",
        f"ADP Test: {adp}",
        f"ACP Test: {acp}",
        returns,
        "After 12 Months",
    ]
    _textbox(doc, "\n".join(cover))
    correction = [
        "ADP/ACP",
        "Correction Page",
        f"Testing Method: {method}",
        f"ADP Test: {adp}",
        f"ACP Test: {acp}",
        "After 12 Months",
    ]
    if adp_qnec is not None:
        correction.append(f"ADP QNEC: ${adp_qnec}")
    if acp_qnec is not None:
        correction.append(f"ACP QNEC: ${acp_qnec}")
    if deferral is not None:
        correction.append(f"Deferral Refund: ${deferral}")
    if match is not None:
        correction.append(f"Match Refund: ${match}")
    _textbox(doc, "\n".join(correction))
    if include_current_notice:
        _textbox(doc, AFTER_12_CURRENT_NOTICE)
    if include_prior_notice:
        _textbox(doc, AFTER_12_PRIOR_NOTICE)
    return doc


VARIANCE_PARAGRAPH = (
    "IMMEDIATE ACTION REQUIRED - VARIANCE\n\n"
    "Please review the contribution variance included in this package and confirm the amounts "
    "before finalizing the Annual Valuation Report."
)

CONTRIBUTIONS_PARAGRAPH = (
    "IMMEDIATE ACTION REQUIRED - CONTRIBUTIONS\n\n"
    "A Contribution and/or adjustment is required. Please review the testing results, and "
    "contribution calculations to ensure they are based on accurate census data.\n"
    "If you need assistance or have questions, please contact your local regional office representative."
)

EXCESS_SUMMARY = (
    "Excess Summary Report\n\n"
    "This report lists excess amounts for affected participants who are not ADP/ACP-only, "
    "unless the ADP/ACP failure is for a partially vested participant."
)

RECAP_BULLETS = [
    "Your plan is not subject to ADP/ACP Nondiscrimination Testing as the plan did not have any Highly Compensated Employees for the plan year.",
    "This rate is determined using the 'prior year data' method. The actual amount an employee can defer is the lesser of that rate.",
    "Note: in addition, the actual amount the employee can defer cannot exceed the annual addition limit.",
    "The plan follows the rules and regulations of the Safe Harbor Plan. Catch-up contributions may still apply.",
    "Based on the definition of Highly Compensated Employee (HCE), the plan had Highly Compensated Employees for the plan year ending, however no employee will be considered highly compensated for the plan year beginning.",
    "Your plan is designed to allow participants who were age 50 or older to make catch-up contributions.",
    "Based on the top heavy testing results, your plan will be considered top heavy for the next plan year.",
    "The plan's employer match contribution is calculated on a participant's compensation earned for each payroll period.",
    "If you sponsor a qualified retirement plan not administered by Mutual of America, please provide your service provider a copy of this Valuation Report.",
]


def build_remaining_sop_pdf(
    *,
    method: str = "CURRENT",
    adp: str = "Pass",
    acp: str = "Pass",
    g402: str = "Fail",
    s415: str = "Pass",
    returns: str = "Returns Required",
    variance: str = "Variance Report",
    contributions: str = "Contributions Required",
    hce_current: str = "Yes",
    hce_future: str = "Yes",
    safe_harbor: str = "No",
    catchup_allowed: str = "Yes",
    per_payroll: str = "Yes",
    top_heavy: str = "No",
    partially_vested: bool = False,
    include_ssn: bool = False,
) -> fitz.Document:
    """TEST23 remaining items: variance, contributions, excess summary, recap, optional SSN."""
    doc = fitz.open()
    cover = [
        "Cover Letter",
        "Plan Number: 777777",
        "Plan Name: Harbor Manufacturing 401(k) Plan",
        "Company Name: Harbor Manufacturing",
        "Address: 10 Harbor Way, Boston, MA 02110",
        "Plan Year: 01/01/2024 - 12/31/2024",
        f"Testing Method: {method}",
        f"ADP Test: {adp}",
        f"ACP Test: {acp}",
        f"402(g) Test: {g402}",
        f"415 Test: {s415}",
        returns,
        variance,
        contributions,
        f"HCE Current Year: {hce_current}",
        f"HCE Future year: {hce_future}",
        f"Safe Harbor: {safe_harbor}",
        f"Catch-up allowed: {catchup_allowed}",
        f"Per Payroll Match: {per_payroll}",
        "Correction Within 12 Months",
    ]
    if top_heavy == "Yes":
        cover.append("Top Heavy Percent: 62.45%")
        cover.append("Plan is top heavy")
    else:
        cover.append("Top Heavy Percent: 8.85%")
        cover.append("Plan is not Top Heavy")
    if partially_vested:
        cover.append("Partially vested participant")
    _textbox(doc, "\n".join(cover))
    _textbox(doc, VARIANCE_PARAGRAPH)
    _textbox(doc, CONTRIBUTIONS_PARAGRAPH)
    _textbox(doc, EXCESS_SUMMARY)
    recap = ["Important Information", ""]
    recap.extend(f"- {item}" for item in RECAP_BULLETS)
    _textbox(doc, "\n".join(recap), fontsize=9)
    census = ["Census", "EMPLOYEE CENSUS", "Participant listing for the plan year."]
    if include_ssn:
        census.append("SSN 123-45-6789")
    _textbox(doc, "\n".join(census))
    return doc


def _textbox(doc: fitz.Document, text: str, fontsize: int = 11) -> None:
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(54, 54, 558, 738), text, fontsize=fontsize, fontname="helv")


SAMPLE_LETTER_ACP = """SAMPLE/DRAFT Communication to Participant
Actual Contribution Percentage (ACP)

This sample letter may be used to notify participants of ADP/ACP excess returns.
"""

SAMPLE_LETTER_ADP = """SAMPLE/DRAFT Communication to Participant
Average Deferral Percentage (ADP)

This sample letter may be used to notify participants of ADP/ACP excess returns.
"""

SAMPLE_LETTER_ADP_ACP = SAMPLE_LETTER_ACP

SAMPLE_LETTER_402G = """SAMPLE/DRAFT Communication to Participant
402(g) Deferral Limit

This sample letter may be used to notify participants that the 402(g) deferral limit has been exceeded.
"""

NOTICE_415 = """Annual Additions (IRC 415) Test Failure Information

The plan failed the IRC 415 annual additions test. Review the 415 Limit Test for affected participants.
"""

SAMPLE_LETTER_415 = """SAMPLE/DRAFT Communication to Participant
Annual Additions (IRC 415) limit has been exceeded

This sample letter may be used to notify participants of a 415 annual additions failure.
"""


def build_sample_letters_pdf(
    *,
    method: str = "CURRENT",
    adp: str = "Fail",
    acp: str = "Fail",
    g402: str = "Fail",
    s415: str = "Fail",
    returns: str = "Returns Required",
    after_deadline: bool = False,
    include_j: bool = True,
    include_j_adp: bool | None = None,
    include_j_acp: bool | None = None,
    include_k: bool = True,
    include_415_notice: bool = True,
    include_415_letter: bool = True,
) -> fitz.Document:
    """TEST23 sample letters (J/K) plus the 415 failure packet and letter (L)."""
    doc = fitz.open()
    cover = [
        "Cover Letter",
        "Plan Number: 666666",
        "Plan Name: Harbor Manufacturing 401(k) Plan",
        "Company Name: Harbor Manufacturing",
        "Address: 10 Harbor Way, Boston, MA 02110",
        "Plan Year: 01/01/2024 - 12/31/2024",
        f"Testing Method: {method}",
        f"ADP Test: {adp}",
        f"ACP Test: {acp}",
        f"402(g) Test: {g402}",
        f"415 Test: {s415}",
        returns,
        "Correction Within 12 Months",
    ]
    if after_deadline:
        cover.append("402(g) failure not processed by 4/15 deadline — noted on the 402(g) test.")
    _textbox(doc, "\n".join(cover))
    if include_j_adp is None:
        include_j_adp = include_j
    if include_j_acp is None:
        include_j_acp = include_j
    if include_j_adp:
        _textbox(doc, SAMPLE_LETTER_ADP)
    if include_j_acp:
        _textbox(doc, SAMPLE_LETTER_ACP)
    if include_k:
        _textbox(doc, SAMPLE_LETTER_402G)
    if include_415_notice:
        _textbox(doc, NOTICE_415)
    if include_415_letter:
        _textbox(doc, SAMPLE_LETTER_415)
    return doc
