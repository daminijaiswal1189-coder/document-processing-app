from __future__ import annotations

from pathlib import Path

import yaml

from config.settings import CONFIG_DIR


def load_section_specs() -> list[dict]:
    data = yaml.safe_load((CONFIG_DIR / "sections.yaml").read_text(encoding="utf-8")) or {}
    return list(data.get("expected_order") or [])


def _norm(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _aliases_for(section_name: str) -> list[str]:
    for spec in load_section_specs():
        if str(spec.get("name") or "") == section_name:
            return [str(spec.get("name") or "")] + [str(a) for a in (spec.get("aliases") or [])]
    return []


def is_cover_letter_name(filename: str) -> bool:
    """True when the file is the Cover Letter / Cover Page (the only PDF we split by page)."""
    name = _norm(filename)
    aliases = _aliases_for("Cover Letter") or ["Cover Letter", "Cover Page"]
    return any(_norm(alias) and _norm(alias) in name for alias in aliases)


def should_split_pages(filename: str, pages: int) -> bool:
    return filename.lower().endswith(".pdf") and pages > 1 and is_cover_letter_name(filename)


def sop_rank(filename: str) -> int:
    """Lower rank = earlier in TEST23 combine order. Unknown files stay last."""
    name = _norm(filename)
    for index, spec in enumerate(load_section_specs()):
        aliases = [str(spec.get("name") or "")] + [str(a) for a in (spec.get("aliases") or [])]
        if any(_norm(alias) and _norm(alias) in name for alias in aliases):
            return index
    return 1000 + len(name)


def order_uploads(uploads: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    return sorted(uploads, key=lambda item: (sop_rank(item[0]), item[0].lower()))
