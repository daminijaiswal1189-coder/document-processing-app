from __future__ import annotations

from pathlib import Path

import yaml

from config.settings import CONFIG_DIR


def load_section_specs() -> list[dict]:
    data = yaml.safe_load((CONFIG_DIR / "sections.yaml").read_text(encoding="utf-8")) or {}
    return list(data.get("expected_order") or [])


def _norm(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _spec_aliases(spec: dict) -> list[str]:
    return [str(spec.get("name") or "")] + [str(a) for a in (spec.get("aliases") or [])]


def _best_section(filename: str) -> tuple[int, dict] | None:
    """Longest keyword match wins so SHMaVar is not treated as MaVar, 401a4 is not 401k, etc."""
    name = _norm(filename)
    best: tuple[int, int, dict] | None = None
    for index, spec in enumerate(load_section_specs()):
        for alias in _spec_aliases(spec):
            token = _norm(alias)
            if not token or token not in name:
                continue
            score = (len(token), -index)
            if best is None or score > (best[0], best[1]):
                best = (len(token), -index, spec)
    if not best:
        return None
    _, neg_index, spec = best
    return -neg_index, spec


def matched_spec(filename: str) -> dict | None:
    found = _best_section(filename)
    return found[1] if found else None


def sop_rank(filename: str) -> int:
    """Lower rank = earlier in TEST23 combine order. Unknown files stay last."""
    found = _best_section(filename)
    if found:
        return found[0]
    return 1000 + len(_norm(filename))


def should_split_pages(filename: str, pages: int) -> bool:
    if not filename.lower().endswith(".pdf") or pages <= 1:
        return False
    spec = matched_spec(filename)
    return bool(spec and spec.get("split_pages"))


COVER_PACKET_PAGE_LABELS = [
    "Cover Letter",
    "Action required page 1",
    "Action required page 2",
    "Action required page 3",
    "ADP/ACP Failure excess page after 12 months (Current year Testing Method)",
    "ADP/ACP Failure excess page after 12 months (Prior year Testing Method)",
    "ADP/ACP Failure excess page Current year",
    "415 Failure information",
    "ADP/ACP Failure letter",
    "402g Failure letter",
    "415 Failure letter",
    "Year End Recap",
    "Compliance Report 1",
    "Compliance Report 2",
    "Compliance Report 3",
]


def display_label(filename: str, page: int = 0, page_count: int = 1) -> str:
    """UI name after upload/split (packet outline titles, not the raw filename)."""
    spec = matched_spec(filename)
    if spec:
        base = str(spec.get("label") or spec.get("name") or filename)
        page_labels = [str(item) for item in (spec.get("split_page_labels") or []) if str(item).strip()]
        if spec.get("split_pages") and not page_labels:
            page_labels = list(COVER_PACKET_PAGE_LABELS)
        if page > 0 and page_count > 1 and page_labels:
            if page <= len(page_labels):
                return page_labels[page - 1]
            return f"{base} page {page}"
        return base
    if page > 0 and page_count > 1:
        return f"{filename} (page {page} of {page_count})"
    return filename


def list_file_meta(name: str, size: int, pages: int) -> dict:
    split = should_split_pages(name, pages)
    labels = (
        [display_label(name, page=page, page_count=pages) for page in range(1, pages + 1)]
        if split
        else [display_label(name)]
    )
    return {
        "name": name,
        "size": size,
        "pages": pages,
        "split": split,
        "rank": sop_rank(name),
        "label": labels[0],
        "labels": labels,
    }


def order_uploads(uploads: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    return sorted(uploads, key=lambda item: (sop_rank(item[0]), item[0].lower()))
