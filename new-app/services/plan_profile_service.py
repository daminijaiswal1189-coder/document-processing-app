from __future__ import annotations

from datetime import datetime

from models.plan_profile import PlanProfile
from services.pdf_extractor import beginning_plan_year


def finalize_profile(profile: PlanProfile) -> PlanProfile:
    """Normalize derived fields after extraction."""
    if profile.plan_year_start is None and profile.plan_year_end:
        try:
            end = datetime.strptime(profile.plan_year_end, "%m/%d/%Y")
            if end.month == 12 and end.day == 31:
                profile.plan_year_start = f"01/01/{end.year}"
        except ValueError:
            pass
    if profile.beginning_plan_year is None and profile.plan_year_start:
        profile.beginning_plan_year = beginning_plan_year(profile.plan_year_start)

    if profile.top_heavy is None and profile.top_heavy_percent is not None:
        profile.top_heavy = profile.top_heavy_percent >= 60

    if profile.testing_failed is None:
        known = [profile.adp_failed, profile.acp_failed, profile.fail_402g, profile.fail_415]
        if any(v is True for v in known):
            profile.testing_failed = True
        elif all(v is False for v in known):
            profile.testing_failed = False

    if profile.total_qnec is None:
        parts = [v for v in (profile.adp_qnec, profile.acp_qnec) if v is not None]
        if parts:
            profile.total_qnec = round(sum(parts), 2)

    if profile.returns_already_processed or profile.adp_reclassified:
        profile.returns_required = False

    outstanding = profile.returns_required is True and profile.adp_reclassified is not True
    action_items: list[str] = []
    if outstanding and (profile.fail_402g or profile.fail_415):
        action_items.append("Compliance returns required")
    if outstanding and (profile.adp_failed or profile.acp_failed):
        action_items.append("ADP/ACP returns required")
    if profile.top_heavy:
        action_items.append("Top heavy")
    if profile.variance_report:
        action_items.append("Variance report")
    if profile.contributions_required:
        action_items.append("Contributions")
    if profile.after_12_months and (profile.adp_failed or profile.acp_failed):
        action_items.append("After 12 months")
    profile.keep_excess_summary = bool(
        profile.fail_402g
        or profile.fail_415
        or (profile.partially_vested and (profile.adp_failed or profile.acp_failed))
    )
    profile.action_required_items = action_items
    if action_items:
        profile.has_action_required = True
    elif any(
        v is False
        for v in (
            profile.adp_failed,
            profile.acp_failed,
            profile.fail_402g,
            profile.fail_415,
            profile.top_heavy,
            profile.returns_required,
        )
    ):
        profile.has_action_required = False
    return profile
