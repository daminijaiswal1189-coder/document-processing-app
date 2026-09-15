from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

from models.plan_profile import PlanProfile


def email_subject(profile: PlanProfile) -> str:
    """TEST23 §P: subject MUST start with MOA, then plan number, name, PYE."""
    number = (profile.plan_number or "UNKNOWN").strip()
    name = (profile.plan_name or "UNKNOWN").strip()
    pye = (profile.plan_year_end or "UNKNOWN").strip()
    return f"MOA | {number} | {name} | PYE {pye}"


def write_draft(path: Path, profile: PlanProfile, filename: str) -> Path:
    """Write an Outlook-ready .eml the tester can open and send."""
    subject = email_subject(profile)
    message = EmailMessage()
    message["Subject"] = subject
    message["To"] = ""
    message.set_content(
        "The Valuation Package has been assembled and is ready for review.\n\n"
        f"File: {filename}\n"
        f"Plan: {profile.plan_number or 'UNKNOWN'}\n"
        f"Plan name: {profile.plan_name or 'UNKNOWN'}\n"
        f"PYE: {profile.plan_year_end or 'UNKNOWN'}\n"
    )
    path.write_bytes(message.as_bytes())
    return path
