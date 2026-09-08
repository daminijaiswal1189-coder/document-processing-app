from __future__ import annotations

from pathlib import Path

import fitz

from config.settings import OUTPUT_DIR
from models.plan_profile import PlanProfile


def valuation_filename(profile: PlanProfile) -> str:
    """{PlanNumber}_{BeginningPlanYear}-Valuation.pdf (SRD §7)."""
    number = (profile.plan_number or "UNKNOWN").strip()
    year = (profile.beginning_plan_year or "UNKNOWN").strip()
    return f"{number}_{year}-Valuation.pdf"


def save_package(doc: fitz.Document, job_id: str, profile: PlanProfile) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    name = valuation_filename(profile)
    path = job_dir / name
    doc.save(path, garbage=3, deflate=True)
    return path
