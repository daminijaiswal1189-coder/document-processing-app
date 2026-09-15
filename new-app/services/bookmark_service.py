from __future__ import annotations

import fitz
import yaml

from config.settings import CONFIG_DIR
from models.plan_profile import PlanProfile


def add_bookmarks(doc: fitz.Document, profile: PlanProfile) -> int:
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
            if is_403b:
                title = "ACP Test"
            else:
                title = "ADP/ACP Tests"
        if title in seen:
            continue
        page = max(1, min(section.page, doc.page_count))
        toc.append([1, title, page])
        seen.add(title)
    if toc:
        doc.set_toc(toc)
    return len(toc)


def _bookmark_map() -> dict[str, str]:
    data = yaml.safe_load((CONFIG_DIR / "sections.yaml").read_text(encoding="utf-8")) or {}
    raw = data.get("bookmarks") or {}
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    return {str(item): str(item) for item in raw}
