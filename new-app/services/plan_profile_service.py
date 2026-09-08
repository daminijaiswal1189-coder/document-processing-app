from __future__ import annotations

from models.plan_profile import PlanProfile
from services.pdf_extractor import beginning_plan_year


def finalize_profile(profile: PlanProfile) -> PlanProfile:
    """Normalize derived fields after extraction."""
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

    action_items: list[str] = []
    if profile.adp_failed:
        action_items.append("ADP failed")
    if profile.acp_failed:
        action_items.append("ACP failed")
    if profile.fail_402g:
        action_items.append("402(g) failed")
    if profile.fail_415:
        action_items.append("415 failed")
    if profile.top_heavy:
        action_items.append("Top heavy")
    if profile.returns_required:
        action_items.append("Returns required")
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
