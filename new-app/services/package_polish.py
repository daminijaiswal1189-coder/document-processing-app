"""Client updates from the revised valuation-package instructions.

Drops a BRF report, reorders pages inside ADP/ACP, 410(b), and component
benefit tests, removes wording MOA packages do not use, and adds the
checks those instructions ask the reviewer to make.
"""

from __future__ import annotations

import re
from datetime import datetime

import fitz

from models.plan_profile import PlanProfile
from models.review import ValidationItem
from services.file_order import matched_spec

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_LETTER_DATE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2}),\s+(20\d{2})\b",
    re.I,
)
_SUMMARY = re.compile(
    r"result summary|test summary|testing summary of results|416\s+top heavy",
    re.I,
)
_BRF_REPORT = re.compile(r"benefits,?\s+rights and features|\bBRF\s+Test\b", re.I)
_KEEP_PAGE = re.compile(
    r"result summary|test summary|testing summary|action required|cover letter|year end recap",
    re.I,
)
_SOC_PAGE = re.compile(r"statement of contribution", re.I)
_DISALLOWED_LINE = re.compile(
    r"escalat|form\s+5500|5500\s+wording|audited\s+wording|statement of contribution|\bSOC\b",
    re.I,
)
_COMPLIANCE = re.compile(
    r"compliance and administrative|overview and descriptions|compliance report",
    re.I,
)
_EXCESS = re.compile(r"excess return|failure notice|failed compliance|qnec", re.I)
_VARIANCE = re.compile(r"variance", re.I)
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_BAD_ZERO = re.compile(r"(?<!\d)\$?\s*(0(?:\.0+)?)(?!\d)")
_NAME_LINE = re.compile(r"^[A-Za-z][A-Za-z' .-]+,\s+[A-Za-z]")
_PASS_FAIL = (
    ("401(a)(4)", r"401\s*\(\s*a\s*\)\s*\(\s*4\s*\)"),
    ("414(s)", r"414\s*\(\s*s\s*\)"),
    ("402(g)", r"402\s*\(?\s*g\s*\)?"),
    ("415", r"415(?:\s*\(\s*c\s*\))?|Annual Additions"),
    ("ADP", r"Average Deferral Percentage|\bADP\b"),
    ("ACP", r"Average Contribution Percentage|\bACP\b"),
    ("410(b)", r"410\s*\(?\s*b\s*\)?"),
)


def hce_max_percent(nhce: float) -> float:
    """Prior-year HCE maximum from the NHCE actual deferral percentage."""
    if nhce < 2:
        return round(nhce * 2, 2)
    if nhce < 8:
        return round(nhce + 2, 2)
    return round(nhce * 1.25, 2)


def cover_date_text(when: datetime | None = None) -> str:
    when = when or datetime.now()
    return f"{_MONTHS[when.month - 1]} {when.day}, {when.year}"


_VARIANCE_SECTIONS = {"Variance", "PS Variance", "SHNE Variance"}


def has_variance_client_copy(filenames: list[str], doc: fitz.Document) -> bool:
    """A variance client copy in the folder keeps the contributions paragraph."""
    for name in filenames:
        spec = matched_spec(name)
        if spec and spec.get("name") in _VARIANCE_SECTIONS:
            return True
    for page in doc:
        text = page.get_text("text") or ""
        if re.search(r"action required", text, re.I):
            continue
        if re.search(r"(?<!no )variance report|\bps\s*variance\b|\bshne\s*variance\b", text, re.I):
            return True
    return False


def exclude_brf_uploads(
    uploads: list[tuple[str, bytes]],
) -> tuple[list[tuple[str, bytes]], list[str]]:
    """A BRF result stays on the Result Summary. The BRF report file does not."""
    kept: list[tuple[str, bytes]] = []
    notes: list[str] = []
    for name, data in uploads:
        spec = matched_spec(name)
        if spec and spec.get("name") == "BRF":
            notes.append(f"Left out BRF report {name}. The Result Summary line is enough.")
            continue
        kept.append((name, data))
    return kept, notes


def reorder_inner_pages(doc: fitz.Document) -> list[str]:
    """Put inner report pages in the order the instructions list."""
    kinds = [_page_kind(page.get_text("text") or "") for page in doc]
    order = list(range(doc.page_count))
    changed: list[str] = []
    index = 0
    while index < len(kinds):
        family = kinds[index][0] if kinds[index] else None
        if not family:
            index += 1
            continue
        end = index + 1
        while end < len(kinds) and kinds[end] and kinds[end][0] == family:
            end += 1
        block = order[index:end]
        ranked = sorted(block, key=lambda page_index: (kinds[page_index][1], page_index))
        if ranked != block:
            order[index:end] = ranked
            changed.append(family)
        index = end
    if order != list(range(doc.page_count)):
        doc.select(order)
    if not changed:
        return []
    return ["Reordered inner pages for " + ", ".join(dict.fromkeys(changed)) + "."]


def remove_disallowed_wording(doc: fitz.Document) -> list[str]:
    """MOA packages do not include audited, SOC, 5500, or escalation wording."""
    removed: list[str] = []
    drop: list[int] = []
    for page in doc:
        text = page.get_text("text") or ""
        if _SOC_PAGE.search(text) and not _KEEP_PAGE.search(text):
            drop.append(page.number)
            if "Statement of Contribution" not in removed:
                removed.append("Statement of Contribution")
            continue
        if _redact_matching_lines(page):
            if "Disallowed wording" not in removed:
                removed.append("Disallowed wording")
    for number in reversed(drop):
        doc.delete_page(number)
    if not removed:
        return []
    return ["Removed " + ", ".join(removed) + "."]


def drop_brf_pages(doc: fitz.Document) -> list[str]:
    drop = [page.number for page in doc if _is_brf_report(page.get_text("text") or "")]
    for number in reversed(drop):
        doc.delete_page(number)
    if not drop:
        return []
    return [f"Removed {len(drop)} BRF report page(s). The Result Summary line is enough."]


def package_checks(doc: fitz.Document, profile: PlanProfile) -> list[ValidationItem]:
    items = [
        _cover_date_check(doc),
        _compliance_check(doc),
        _brf_check(doc),
    ]
    items.extend(_result_summary_checks(doc))
    items.extend(_variance_checks(doc, profile))
    items.extend(_identity_checks(doc, profile))
    return items


def _page_kind(text: str) -> tuple[str, int] | None:
    head = _head(text)
    if not head or _KEEP_PAGE.search(head):
        return None
    abpt = _abpt_rank(head)
    if abpt is not None:
        return ("Average Benefit Percentage", abpt)
    if re.search(r"410\s*\(?b\)?", head, re.I):
        rank = _ranked(
            head,
            ((r"excludable", 1), (r"includable", 2), (r"\bdetail\b", 0), (r"\bsummary\b", 3)),
        )
        if rank is not None:
            return ("410(b)", rank)
    if re.search(r"\bADP\b|\bACP\b", head, re.I):
        rank = _ranked(
            head,
            ((r"correction", 3), (r"excluded", 2), (r"\bdetail\b", 1), (r"\bsummary\b", 0)),
        )
        if rank is not None:
            return ("ADP/ACP", rank)
    return None


def _abpt_rank(head: str) -> int | None:
    order = (
        (r"401\s*a\s*1|401a1", 1),
        (r"gateway", 2),
        (r"overall\s+comp", 3),
        (r"rate\s+group", 4),
        (r"sum\s+comp", 5),
        (r"average benefit percentage", 0),
    )
    return _ranked(head, order)


def _ranked(head: str, pairs: tuple[tuple[str, int], ...]) -> int | None:
    for pattern, rank in pairs:
        if re.search(pattern, head, re.I):
            return rank
    return None


def _head(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines[:4])


def _is_brf_report(text: str) -> bool:
    if _KEEP_PAGE.search(text):
        return False
    return bool(_BRF_REPORT.search(_head(text)))


def _redact_matching_lines(page: fitz.Page) -> bool:
    boxes: list[fitz.Rect] = []
    for block in page.get_text("dict").get("blocks") or []:
        if block.get("type") != 0:
            continue
        for line in block.get("lines") or []:
            line_text = "".join(span.get("text") or "" for span in line.get("spans") or [])
            if _DISALLOWED_LINE.search(line_text):
                boxes.append(fitz.Rect(line["bbox"]))
    if not boxes:
        return False
    for box in boxes:
        page.add_redact_annot(box, fill=(1, 1, 1))
    page.apply_redactions()
    return True


def _cover_date_check(doc: fitz.Document) -> ValidationItem:
    today = cover_date_text()
    if not doc.page_count:
        return ValidationItem(
            code="cover_date_today",
            label="Cover date is today",
            passed=False,
            detail="Cover page is missing.",
        )
    text = doc[0].get_text("text") or ""
    match = _LETTER_DATE.search(text)
    if not match:
        return ValidationItem(
            code="cover_date_today",
            label="Cover date is today",
            passed=False,
            detail=f"No cover letter date found. It should be {today}.",
        )
    found = f"{match.group(1).title()} {int(match.group(2))}, {match.group(3)}"
    if found.lower() == today.lower():
        return ValidationItem(
            code="cover_date_today",
            label="Cover date is today",
            passed=True,
            detail=found,
        )
    return ValidationItem(
        code="cover_date_today",
        label="Cover date is today",
        passed=False,
        detail=f"Cover date is {found}. It should be {today}.",
    )


def _compliance_check(doc: fitz.Document) -> ValidationItem:
    count = sum(1 for page in doc if _COMPLIANCE.search(page.get_text("text") or ""))
    return ValidationItem(
        code="compliance_three_pages",
        label="Compliance reports (3 pages)",
        passed=count == 3,
        detail="3 Compliance and Administrative Report pages are in the package."
        if count == 3
        else f"Found {count} compliance report page(s). The package should include 3.",
    )


def _brf_check(doc: fitz.Document) -> ValidationItem:
    left = [page.number + 1 for page in doc if _is_brf_report(page.get_text("text") or "")]
    return ValidationItem(
        code="brf_report_omitted",
        label="BRF report omitted",
        passed=not left,
        detail="No BRF report is in the package."
        if not left
        else "BRF report still present on page(s) " + ", ".join(str(page) for page in left),
    )


def _result_summary_checks(doc: fitz.Document) -> list[ValidationItem]:
    summary = "\n".join(
        page.get_text("text") or "" for page in doc if _SUMMARY.search(page.get_text("text") or "")
    )
    if not summary.strip():
        return [
            ValidationItem(
                code="result_summary",
                label="Result Summary vs test reports",
                passed=False,
                detail="Result Summary was not found, so pass/fail and top heavy were not compared.",
            )
        ]
    items = [_top_heavy_check(doc, summary)]
    items.extend(_pass_fail_checks(doc, summary))
    return items


def _top_heavy_check(doc: fitz.Document, summary: str) -> ValidationItem:
    shown = re.search(r"top\s*heavy[\s\S]{0,80}?(\d+(?:\.\d+)?)\s*%", summary, re.I)
    if not shown:
        return ValidationItem(
            code="top_heavy_summary",
            label="Top heavy on Result Summary",
            passed=False,
            detail="Top heavy percent was not found on the Result Summary.",
        )
    token = shown.group(1)
    percent = float(token)
    problems: list[str] = []
    if percent == 0 and token != "0.00":
        problems.append(f"{token}% should be shown as 0.00%")
    expects_top_heavy = percent > 60
    says_not = bool(re.search(r"plan is not top heavy", summary, re.I))
    says_is = bool(re.search(r"plan is top heavy", summary, re.I)) and not says_not
    if expects_top_heavy and not says_is:
        problems.append("percent is over 60%, so the line should say Plan is Top Heavy")
    if not expects_top_heavy and not says_not:
        problems.append("percent is 60% or less, so the line should say Plan is not Top Heavy")
    report = _report_percent(doc, r"top\s*heavy")
    if report is not None and abs(report - percent) > 0.01:
        problems.append(f"Result Summary shows {percent:g}% and the Top Heavy report shows {report:g}%")
    return ValidationItem(
        code="top_heavy_summary",
        label="Top heavy on Result Summary",
        passed=not problems,
        detail="; ".join(problems) if problems else f"Top heavy {token}% matches the report.",
    )


def _pass_fail_checks(doc: fitz.Document, summary: str) -> list[ValidationItem]:
    items: list[ValidationItem] = []
    for label, pattern in _PASS_FAIL:
        summary_result = _result_near(summary, pattern)
        report_result = None
        for page in doc:
            text = page.get_text("text") or ""
            if _SUMMARY.search(text):
                continue
            report_result = _result_near(text, pattern)
            if report_result:
                break
        if summary_result is None and report_result is None:
            continue
        problems: list[str] = []
        if summary_result and report_result and summary_result != report_result:
            problems.append(f"Result Summary says {summary_result}, the report says {report_result}")
        if label == "410(b)" and summary_result == "fail" and not re.search(
            r"average benefit", summary + "\n".join(page.get_text("text") or "" for page in doc), re.I
        ):
            problems.append("410(b) failed and the ABPT wording was not found")
        if not summary_result and report_result:
            problems.append(f"report says {report_result}, Result Summary has no matching line")
        items.append(
            ValidationItem(
                code=f"summary_{label}",
                label=f"{label} on Result Summary",
                passed=not problems,
                detail="; ".join(problems) if problems else f"{label} agrees ({summary_result or report_result}).",
            )
        )
    if not items:
        items.append(
            ValidationItem(
                code="result_summary",
                label="Result Summary vs test reports",
                passed=False,
                detail="Result Summary did not include pass/fail lines to compare.",
            )
        )
    return items


def _result_near(text: str, pattern: str) -> str | None:
    match = re.search(r"(?:" + pattern + r").{0,80}?\b(Pass|Fail)\b", text, re.I | re.S)
    if not match:
        return None
    return match.group(1).lower()


def _report_percent(doc: fitz.Document, label: str) -> float | None:
    for page in doc:
        text = page.get_text("text") or ""
        if _SUMMARY.search(text):
            continue
        match = re.search(label + r"[\s\S]{0,80}?(\d+(?:\.\d+)?)\s*%", text, re.I)
        if match:
            return float(match.group(1))
    return None


def _variance_checks(doc: fitz.Document, profile: PlanProfile) -> list[ValidationItem]:
    pages = [
        page
        for page in doc
        if _VARIANCE.search(page.get_text("text") or "") and not re.search(r"action required", page.get_text("text") or "", re.I)
    ]
    if not pages:
        return [
            ValidationItem(
                code="variance_client",
                label="Client variance report",
                passed=True,
                detail="No client variance report in this package.",
            )
        ]
    problems: list[str] = []
    for page in pages:
        text = page.get_text("text") or ""
        number = page.number + 1
        if _SSN.search(text):
            problems.append(f"page {number} has a Social Security number")
        if _bad_zero(text):
            problems.append(f"page {number} has a zero that is not 0.00")
        if _mixed_font(page):
            problems.append(f"page {number} uses more than one font size")
        if _cut_off(page):
            problems.append(f"page {number} has text at the page edge")
        names = [line.strip() for line in text.splitlines() if _NAME_LINE.match(line.strip())]
        ordered = sorted(names, key=str.lower)
        if len(names) >= 2 and names != ordered:
            problems.append(f"page {number} names are not alphabetical")
        for label, value in (
            ("plan number", profile.plan_number),
            ("plan name", profile.plan_name),
            ("plan year end", profile.plan_year_end),
        ):
            if value and value.lower() not in text.lower():
                problems.append(f"page {number} is missing the {label}")
    return [
        ValidationItem(
            code="variance_client",
            label="Client variance report",
            passed=not problems,
            detail="; ".join(problems) if problems else "Variance pages have plan identity, 0.00 zeroes, one font size, and alphabetical names.",
        )
    ]


def _bad_zero(text: str) -> bool:
    for match in _BAD_ZERO.finditer(text):
        token = match.group(1)
        if token != "0.00":
            return True
    return False


def _mixed_font(page: fitz.Page) -> bool:
    sizes: set[float] = set()
    for block in page.get_text("dict").get("blocks") or []:
        if block.get("type") != 0:
            continue
        for line in block.get("lines") or []:
            for span in line.get("spans") or []:
                size = round(float(span.get("size") or 0), 1)
                if size >= 8:
                    sizes.add(size)
    return len(sizes) > 1


def _cut_off(page: fitz.Page) -> bool:
    limit = page.rect.x1 - 4
    for block in page.get_text("dict").get("blocks") or []:
        if block.get("type") != 0:
            continue
        for line in block.get("lines") or []:
            for span in line.get("spans") or []:
                if float(span["bbox"][2]) >= limit and (span.get("text") or "").strip():
                    return True
    return False


def _plan_year_present(text: str, plan_year_end: str) -> bool:
    """Accept 12/31/2025 and the notice header 'December 31, 2025'."""
    if plan_year_end in text:
        return True
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", plan_year_end.strip())
    if not match:
        return False
    month = int(match.group(1))
    if not 1 <= month <= 12:
        return False
    written = f"{_MONTHS[month - 1]} {int(match.group(2))}, {match.group(3)}"
    return written.lower() in text.lower()


def _identity_checks(doc: fitz.Document, profile: PlanProfile) -> list[ValidationItem]:
    if not profile.plan_number and not profile.plan_name:
        return [
            ValidationItem(
                code="report_identity",
                label="Plan identity on reports",
                passed=False,
                detail="Plan number and plan name were not read, so each report could not be checked.",
            )
        ]
    missing: list[str] = []
    for page in doc:
        if page.number == 0:
            continue
        text = page.get_text("text") or ""
        if len(text.strip()) < 20:
            continue
        head = _head(text)
        is_excess = bool(_EXCESS.search(text))
        is_report = bool(
            re.search(
                r"contribution analysis|future hce|\bHCE\b|ADP|ACP|402|410|401|average benefit|414|415|top heavy|census|variance|test summary",
                head,
                re.I,
            )
        )
        if not is_excess and not is_report:
            continue
        gaps: list[str] = []
        if profile.plan_number and profile.plan_number not in text:
            gaps.append("plan number")
        if profile.plan_name and profile.plan_name.lower() not in text.lower():
            gaps.append("plan name")
        if is_excess and profile.plan_year_end and not _plan_year_present(text, profile.plan_year_end):
            gaps.append("plan year end")
        if gaps:
            missing.append(f"page {page.number + 1} missing " + ", ".join(gaps))
    return [
        ValidationItem(
            code="report_identity",
            label="Plan identity on reports",
            passed=not missing,
            detail="Plan number and plan name appear on each report."
            if not missing
            else "; ".join(missing[:8]),
        )
    ]
