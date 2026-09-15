from __future__ import annotations

import re

import fitz
import yaml

from config.settings import CONFIG_DIR
from models.plan_profile import PlanProfile

_ADP_FILE = re.compile(r"\badp\s*test\b")
_ACP_FILE = re.compile(r"\bacp\s*test\b")
_BOTH_FILE = re.compile(r"\badp\s*acp\b|\badpacp\b")
_ADP_HEADING = re.compile(r"(?im)^\s*ADP\s+Tests?\s*$")
_ACP_HEADING = re.compile(r"(?im)^\s*ACP\s+Tests?\s*$")
_BOTH_HEADING = re.compile(r"(?im)^\s*ADP\s*/\s*ACP\s+Tests?\s*$")


def add_bookmarks(
    doc: fitz.Document,
    profile: PlanProfile,
    source_files: list[str] | None = None,
) -> int:
    """Write SOP §O bookmarks for detected sections (TEST23.docx)."""
    titles = _bookmark_map()
    is_403b = "403" in (profile.plan_type or "").lower()
    toc: list[list] = []
    seen: set[str] = set()
    for section in profile.detected_sections:
        title = titles.get(section.name)
        if not title:
            continue
        if section.name == "HCE/Key":
            title = "HCE" if is_403b else "HCE/Key"
        if section.name == "ADP/ACP":
            title = adp_acp_bookmark_title(profile, doc, source_files)
        if title in seen:
            continue
        page = max(1, min(section.page, doc.page_count))
        toc.append([1, title, page])
        seen.add(title)
    if toc:
        doc.set_toc(toc)
    return len(toc)


def adp_acp_bookmark_title(
    profile: PlanProfile,
    doc: fitz.Document | None = None,
    source_files: list[str] | None = None,
) -> str:
    """TEST23 §O: ADP Test, ACP Test, or ADP/ACP Tests from what is in the package."""
    if "403" in (profile.plan_type or "").lower():
        return "ACP Test"
    has_adp, has_acp = _adp_acp_present(source_files or [], doc)
    if has_adp and not has_acp:
        return "ADP Test"
    if has_acp and not has_adp:
        return "ACP Test"
    return "ADP/ACP Tests"


def _adp_acp_present(source_files: list[str], doc: fitz.Document | None) -> tuple[bool, bool]:
    blob = " ".join(_file_tokens(name) for name in source_files)
    has_adp = bool(_ADP_FILE.search(blob) or _BOTH_FILE.search(blob))
    has_acp = bool(_ACP_FILE.search(blob) or _BOTH_FILE.search(blob))
    if doc is not None:
        page_text = "\n".join((page.get_text("text") or "") for page in doc)
        if _BOTH_HEADING.search(page_text):
            has_adp = True
            has_acp = True
        if _ADP_HEADING.search(page_text):
            has_adp = True
        if _ACP_HEADING.search(page_text):
            has_acp = True
    return has_adp, has_acp


def _file_tokens(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower())


def _bookmark_map() -> dict[str, str]:
    data = yaml.safe_load((CONFIG_DIR / "sections.yaml").read_text(encoding="utf-8")) or {}
    raw = data.get("bookmarks") or {}
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    return {str(item): str(item) for item in raw}
