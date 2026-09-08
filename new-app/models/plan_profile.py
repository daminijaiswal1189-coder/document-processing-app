from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DetectedSection(BaseModel):
    name: str
    page: int
    matched_alias: str


class PlanProfile(BaseModel):
    """Single object used by every business rule (SRD §6)."""

    plan_number: str | None = None
    plan_name: str | None = None
    company_name: str | None = None
    company_address: str | None = None
    plan_type: str | None = None
    plan_year_start: str | None = None
    plan_year_end: str | None = None
    beginning_plan_year: str | None = None
    testing_method: str | None = None
    top_heavy_percent: float | None = None
    top_heavy: bool | None = None
    adp_failed: bool | None = None
    acp_failed: bool | None = None
    testing_failed: bool | None = None
    returns_required: bool | None = None
    fail_402g: bool | None = None
    fail_415: bool | None = None
    variance_report: bool | None = None
    after_12_months: bool | None = None
    adp_qnec: float | None = None
    acp_qnec: float | None = None
    deferral_refund: float | None = None
    match_refund: float | None = None
    total_qnec: float | None = None
    has_action_required: bool | None = None
    action_required_items: list[str] = Field(default_factory=list)
    detected_sections: list[DetectedSection] = Field(default_factory=list)
    extraction_warnings: list[str] = Field(default_factory=list)
    source_page_count: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)
