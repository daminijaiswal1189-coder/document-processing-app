from __future__ import annotations

from models.plan_profile import PlanProfile
from models.review import ReviewResult, ValidationItem


def validate(profile: PlanProfile) -> ReviewResult:
    """Phase 2 stub: cover-field presence only. SSN and order come next."""
    items = [
        _present("cover_plan_number", "Plan Number", profile.plan_number),
        _present("cover_plan_name", "Plan Name", profile.plan_name),
        _present("cover_address", "Address", profile.company_address),
        _present("cover_plan_year_end", "Plan Year End", profile.plan_year_end),
        _present("top_heavy", "Top Heavy %", profile.top_heavy_percent),
    ]
    return ReviewResult(items=items, ssn_found=False, ssn_pages=[])


def _present(code: str, label: str, value: object) -> ValidationItem:
    ok = value is not None and value != ""
    return ValidationItem(
        code=code,
        label=label,
        passed=ok,
        detail="Extracted" if ok else "Not found — confirm on source PDF or update field patterns",
    )
