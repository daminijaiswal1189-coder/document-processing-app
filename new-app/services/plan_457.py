"""457 Important Information edits that a 401(k) package does not use."""

from __future__ import annotations

import re

import fitz

_OVERVIEW = re.compile(r"administrative reports", re.I)
_ANALYSIS = re.compile(r"contribution analysis", re.I)
_BLURB = re.compile(r"a summary of total contributions", re.I)


def remove_contribution_overview(doc: fitz.Document) -> list[str]:
    """Drop the Contribution Analysis description when that report is not in the package."""
    if _has_contribution_report(doc):
        return []
    notes: list[str] = []
    drop: list[int] = []
    for page in doc:
        original = page.get_text("text") or ""
        if not _OVERVIEW.search(original) or not _ANALYSIS.search(original):
            continue
        updated = _without_analysis_section(original)
        if updated == original.strip():
            continue
        if not updated or updated.lower() in {"administrative reports"}:
            drop.append(page.number)
        else:
            page.add_redact_annot(page.rect, fill=(1, 1, 1), text="")
            page.apply_redactions()
            page.insert_textbox(fitz.Rect(54, 54, 558, 738), updated, fontsize=11, fontname="helv")
        notes.append("Removed the Contribution Analysis description. That report is not in the package.")
    for number in reversed(drop):
        doc.delete_page(number)
    return notes


def _has_contribution_report(doc: fitz.Document) -> bool:
    for page in doc:
        text = page.get_text("text") or ""
        if not _ANALYSIS.search(text):
            continue
        if _OVERVIEW.search(text) and _BLURB.search(text):
            continue
        return True
    return False


def _without_analysis_section(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    skipping = False
    for line in lines:
        if _ANALYSIS.search(line):
            skipping = True
            continue
        if skipping:
            if not line.strip():
                skipping = False
            continue
        kept.append(line)
    return "\n".join(kept).strip()
