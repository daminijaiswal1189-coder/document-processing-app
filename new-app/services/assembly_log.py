"""Val Assembly Log in the column layout of logs-updation.xlsx.

Tester-owned columns (FIS, related plans, MEP, safe harbor) are left blank.
Failed Comp Limit is always N/A for MOA.
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz
from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.worksheet.datavalidation import DataValidation

from models.plan_profile import PlanProfile
from services.source_profile import parse_summary_text

_HEADERS = [
    "Omni Plan Number",
    "Plan Name",
    "Are there HCE on the Future HCE Report",
    "Are there HCE Hce/Key report (Current Year HCE)",
    "Did you complete any Allocations (Annual / Varaince or Both)",
    "Failed ADP/ACP P/F/N/A",
    "Failed 402g/457 Def Limit",
    "Failed 410b",
    "Failed ABP",
    "Failed 414s",
    "Failed 401a4",
    "Failed 415",
    "Top Heavy",
    "Failed BRF",
    "Failed Comp Limit",
    "Was FIS instructed to Proceed without Document, Amendment, Against document coding",
    "",
    "Are there any Related Plans",
    "Is this a MEP Plan",
    "Is this plan Safe Harbor",
]
_SUMMARY = re.compile(r"result summary|testing summary of results|test summary", re.I)
_PERSON = re.compile(r"(?m)^[A-Z][A-Za-z' .-]+,\s+[A-Z]")
_NONE = re.compile(r"\bno\s+hce\b|there are no hce|0\s+hce", re.I)


def append_row(
    log_path: Path,
    profile: PlanProfile,
    filename: str,
    job_id: str,
    doc: fitz.Document | None = None,
) -> Path:
    """Append one assembled plan using the logs-updation.xlsx columns."""
    del filename, job_id
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.is_file():
        book = load_workbook(log_path)
        sheet = book.active
        if sheet.cell(1, 1).value != _HEADERS[0]:
            book.remove(sheet)
            sheet = book.create_sheet("Val Assembly Log", 0)
            _write_headers(sheet)
    else:
        book = Workbook()
        sheet = book.active
        sheet.title = "Val Assembly Log"
        _write_headers(sheet)
    values, note = build_log_row(profile, doc)
    row = _next_data_row(sheet)
    for col, value in enumerate(values, start=1):
        sheet.cell(row, col, value)
    if note:
        sheet.cell(row, 5).comment = Comment(note, "MOA")
    book.save(log_path)
    return log_path


def build_log_row(profile: PlanProfile, doc: fitz.Document | None = None) -> tuple[list[str], str]:
    summary = _summary_text(doc)
    parsed = parse_summary_text(summary) if summary else {}
    number = str(parsed.get("plan_number") or profile.plan_number or "")
    name = str(parsed.get("plan_name") or profile.plan_name or "")
    allocation, allocation_note = _allocation(profile)
    values = [
        number,
        name,
        _hce_answer(profile.hce_future, _report_text(doc, r"future\s+hce")),
        _hce_answer(profile.hce_current, _report_text(doc, r"hce\s*/?\s*key", skip=r"future\s+hce")),
        allocation,
        _adp_status(profile, summary),
        _flag_status(profile.fail_402g, summary, r"402\s*\(?\s*g\s*\)?|457", _has_section(profile, "402(g)")),
        _test_status(profile, summary, "410(b)", r"410\s*\(?\s*b\s*\)?"),
        _test_status(profile, summary, "Average Benefit Percentage Test", r"average benefit|ABPT|\bABP\b"),
        _test_status(profile, summary, "414(s)", r"414\s*\(\s*s\s*\)"),
        _test_status(profile, summary, "401(a)(4)", r"401\s*\(\s*a\s*\)\s*\(\s*4\s*\)"),
        _flag_status(profile.fail_415, summary, r"415(?:\s*\(\s*c\s*\))?|Annual Additions", _has_section(profile, "415")),
        _top_heavy(profile, summary),
        _test_status(profile, summary, "BRF", r"benefits,?\s+rights|\bBRF\b"),
        "N/A",
        "",
        "",
        "",
        "",
        "",
    ]
    return values, allocation_note


def _write_headers(sheet) -> None:
    for col, header in enumerate(_HEADERS, start=1):
        sheet.cell(1, col, header)
    sheet.cell(2, 5, "Allocation Completed")
    _add_lists(sheet)


def _add_lists(sheet) -> None:
    lists = (
        ("C3:D500", '"Yes,No"'),
        ("E3:E500", '"Variance,Annual,Annual-Var"'),
        ("F3:L500", '"P,F,N/A"'),
        ("M3:M500", '"Yes,No"'),
        ("N3:O500", '"P,F,N/A"'),
    )
    for cells, formula in lists:
        rule = DataValidation(type="list", formula1=formula, allow_blank=True)
        rule.add(cells)
        sheet.add_data_validation(rule)


def _next_data_row(sheet) -> int:
    if (sheet.max_row or 1) < 3:
        return 3
    return sheet.max_row + 1


def _allocation(profile: PlanProfile) -> tuple[str, str]:
    notes = profile.assembly_notes or ""
    low = notes.lower()
    both = re.search(r"annual allocation and true-?up both", low)
    annual_only = re.search(r"annual allocation", low) and not re.search(r"true-?up", low)
    true_up = re.search(r"true-?up", low)
    if both:
        return "Annual-Var", ""
    if annual_only:
        return "Annual", ""
    if true_up and not re.search(r"(?<!no )variance", low):
        return "Variance", "0.00 variance"
    if profile.contributions_required is True:
        return "Variance", ""
    return "", ""


def _hce_answer(flag: bool | None, report_text: str) -> str:
    has_person = bool(_PERSON.search(report_text or ""))
    if flag is True or has_person:
        return "Yes"
    if flag is False or _NONE.search(report_text or ""):
        return "No"
    return ""


def _adp_status(profile: PlanProfile, summary: str) -> str:
    adp = _result_near(summary, r"Average Deferral Percentage|\bADP\b")
    acp = _result_near(summary, r"Average Contribution Percentage|\bACP\b")
    if profile.adp_failed or profile.acp_failed or adp == "fail" or acp == "fail":
        return "F"
    present = _has_section(profile, "ADP/ACP") or adp is not None or acp is not None
    if adp == "pass" or acp == "pass" or profile.adp_failed is False or profile.acp_failed is False:
        return "P"
    return "N/A" if not present else ""


def _flag_status(flag: bool | None, summary: str, pattern: str, present: bool) -> str:
    result = _result_near(summary, pattern)
    if flag is True or result == "fail":
        return "F"
    if flag is False or result == "pass":
        return "P"
    return "N/A" if not present and result is None else ""


def _test_status(profile: PlanProfile, summary: str, section: str, pattern: str) -> str:
    result = _result_near(summary, pattern)
    present = _has_section(profile, section) or result is not None
    if result == "fail":
        return "F"
    if result == "pass":
        return "P"
    return "N/A" if not present else ""


def _top_heavy(profile: PlanProfile, summary: str) -> str:
    if re.search(r"plan is not top heavy", summary or "", re.I):
        return "No"
    if re.search(r"plan is top heavy", summary or "", re.I):
        return "Yes"
    if profile.top_heavy is True:
        return "Yes"
    if profile.top_heavy is False:
        return "No"
    return ""


def _has_section(profile: PlanProfile, name: str) -> bool:
    return any(section.name == name for section in profile.detected_sections)


def _result_near(text: str, pattern: str) -> str | None:
    match = re.search(r"(?:" + pattern + r").{0,80}?\b(Pass|Fail)\b", text or "", re.I | re.S)
    if not match:
        return None
    return match.group(1).lower()


def _summary_text(doc: fitz.Document | None) -> str:
    if doc is None:
        return ""
    parts = [page.get_text("text") or "" for page in doc if _SUMMARY.search(page.get_text("text") or "")]
    return "\n".join(parts)


def _report_text(doc: fitz.Document | None, pattern: str, skip: str | None = None) -> str:
    if doc is None:
        return ""
    compiled = re.compile(pattern, re.I)
    skipped = re.compile(skip, re.I) if skip else None
    parts: list[str] = []
    for page in doc:
        text = page.get_text("text") or ""
        if _SUMMARY.search(text) or (skipped and skipped.search(text)):
            continue
        if compiled.search(text):
            parts.append(text)
    return "\n".join(parts)
