from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

from models.plan_profile import PlanProfile


def email_subject(profile: PlanProfile) -> str:
    """Subject starts with MOA, then plan number, name, and PYE.

    Rework and Rush come from the valuation package Excel. Yes on either one
    is named in the subject. Both Yes is Rush Rework.
    """
    number = (profile.plan_number or "UNKNOWN").strip()
    name = (profile.plan_name or "UNKNOWN").strip()
    pye = (profile.plan_year_end or "UNKNOWN").strip()
    tail = f"{number} - {name} - PYE {pye}"
    rush = profile.rush is True
    rework = profile.rework is True
    if rush and rework:
        prefix = "MOA - Rush Rework"
    elif rush:
        prefix = "MOA - Rush"
    elif rework:
        prefix = "MOA - Rework"
    else:
        prefix = "MOA"
    return f"{prefix} - {tail}"


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
