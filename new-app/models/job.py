from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from models.plan_profile import PlanProfile
from models.review import RuleDecision, ReviewResult


class JobResult(BaseModel):
    job_id: str
    filename: str
    pdf_path: str
    created_at: datetime
    plan_profile: PlanProfile
    review: ReviewResult | None = None
    rule_decisions: list[RuleDecision] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)
    download_url: str = ""
    preview_url: str = ""
    email_subject: str = ""
    email_path: str = ""
    log_path: str = ""
    saved_copy_path: str = ""
