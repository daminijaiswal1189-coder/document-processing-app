from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import fitz
import yaml

from config.field_patterns import COVER_PATTERNS, FAIL_FLAGS, TEST_PATTERNS
from config.settings import CONFIG_DIR
from models.plan_profile import DetectedSection, PlanProfile

_NEXT_LABEL = re.compile(
    r"^(Plan\s*(Name|Number|Year|Type)|Company|Employer|Address|Sponsor)\b",
    re.I,
)


def extract_plan_profile(doc: fitz.Document) -> PlanProfile:
    cover_text = _pages_text(doc, 0, min(3, doc.page_count))
    full_text = _pages_text(doc, 0, doc.page_count)
    warnings: list[str] = []

    plan_number = _first_match(cover_text, COVER_PATTERNS["plan_number"])
    plan_name = _clean_line(_first_match(cover_text, COVER_PATTERNS["plan_name"]))
    company_name = _clean_line(_first_match(cover_text, COVER_PATTERNS["company_name"]))
    company_address = _clean_line(_first_match(cover_text, COVER_PATTERNS["company_address"]))

    year_start, year_end = _plan_year(cover_text or full_text)
    method = _testing_method(full_text)
    top_heavy_percent = _money_or_percent(full_text, TEST_PATTERNS["top_heavy_percent"])

    flags = {name: _flag_present(full_text, patterns) for name, patterns in FAIL_FLAGS.items()}
    testing_failed = _or_bools(flags.get("adp_failed"), flags.get("acp_failed"), flags.get("fail_402g"), flags.get("fail_415"))

    adp_qnec = _money_or_percent(full_text, TEST_PATTERNS["adp_qnec"])
    acp_qnec = _money_or_percent(full_text, TEST_PATTERNS["acp_qnec"])
    deferral_refund = _money_or_percent(full_text, TEST_PATTERNS["deferral_refund"])
    match_refund = _money_or_percent(full_text, TEST_PATTERNS["match_refund"])
    total_qnec = _sum_optional(adp_qnec, acp_qnec)

    if not plan_number:
        warnings.append("Plan number was not found on the cover pages. Filename will use UNKNOWN.")
    if not year_start and not year_end:
        warnings.append("Plan year was not found. Filename will use UNKNOWN for the year.")

    top_heavy = None
    if top_heavy_percent is not None:
        top_heavy = top_heavy_percent >= 60

    profile = PlanProfile(
        plan_number=plan_number,
        plan_name=plan_name,
        company_name=company_name,
        company_address=company_address,
        plan_year_start=year_start,
        plan_year_end=year_end,
        beginning_plan_year=_beginning_year(year_start),
        testing_method=method,
        top_heavy_percent=top_heavy_percent,
        top_heavy=top_heavy,
        adp_failed=flags.get("adp_failed"),
        acp_failed=flags.get("acp_failed"),
        testing_failed=testing_failed,
        returns_required=flags.get("returns_required"),
        fail_402g=flags.get("fail_402g"),
        fail_415=flags.get("fail_415"),
        variance_report=flags.get("variance_report"),
        after_12_months=flags.get("after_12_months"),
        adp_qnec=adp_qnec,
        acp_qnec=acp_qnec,
        deferral_refund=deferral_refund,
        match_refund=match_refund,
        total_qnec=total_qnec,
        has_action_required=None,
        detected_sections=_detect_sections(doc),
        extraction_warnings=warnings,
        source_page_count=doc.page_count,
    )
    return profile


def beginning_plan_year(start_date: str) -> str | None:
    """SRD §7: use the beginning plan year only."""
    return _beginning_year(start_date)


def _pages_text(doc: fitz.Document, start: int, end: int) -> str:
    parts: list[str] = []
    for index in range(start, end):
        parts.append(doc[index].get_text("text") or "")
    return "\n".join(parts)


def _first_match(text: str, patterns: list[str]) -> str | None:
    if not text:
        return None
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _clean_line(value: str | None) -> str | None:
    if not value:
        return None
    line = value.splitlines()[0].strip()
    line = re.sub(r"\s{2,}", " ", line)
    if _NEXT_LABEL.match(line):
        return None
    return line or None


def _plan_year(text: str) -> tuple[str | None, str | None]:
    for pattern in COVER_PATTERNS["plan_year"]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        if match.lastindex and match.lastindex >= 2:
            return _format_date(match.group(1)), _format_date(match.group(2))
        end = _format_date(match.group(1))
        return None, end
    return None, None


def _format_date(raw: str) -> str | None:
    raw = (raw or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%m/%d/%Y")
        except ValueError:
            continue
    return raw or None


def _beginning_year(start_date: str | None) -> str | None:
    if not start_date:
        return None
    try:
        return str(datetime.strptime(start_date, "%m/%d/%Y").year)
    except ValueError:
        match = re.search(r"(19|20)\d{2}", start_date)
        return match.group(0) if match else None


def _testing_method(text: str) -> str | None:
    for pattern in TEST_PATTERNS["testing_method"]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def _money_or_percent(text: str, patterns: list[str]) -> float | None:
    raw = _first_match(text, patterns)
    if raw is None:
        return None
    cleaned = raw.replace(",", "").replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _flag_present(text: str, patterns: list[str]) -> bool | None:
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            return True
    return None


def _or_bools(*values: bool | None) -> bool | None:
    known = [v for v in values if v is not None]
    if not known:
        return None
    return any(known)


def _sum_optional(*values: float | None) -> float | None:
    known = [v for v in values if v is not None]
    if not known:
        return None
    return round(sum(known), 2)


def _load_sections() -> list[dict[str, Any]]:
    path = CONFIG_DIR / "sections.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("expected_order") or [])


def _detect_sections(doc: fitz.Document) -> list[DetectedSection]:
    found: list[DetectedSection] = []
    seen: set[str] = set()
    specs = _load_sections()
    for page_index, page in enumerate(doc):
        text = page.get_text("text") or ""
        for spec in specs:
            name = spec["name"]
            if name in seen:
                continue
            for alias in spec.get("aliases") or [name]:
                if re.search(rf"\b{re.escape(alias)}\b", text, flags=re.IGNORECASE):
                    found.append(DetectedSection(name=name, page=page_index + 1, matched_alias=alias))
                    seen.add(name)
                    break
    return found
