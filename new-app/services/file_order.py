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


def matched_spec(filename: str) -> dict | None:
    name = _norm(filename)
    for spec in load_section_specs():
        if any(_norm(alias) and _norm(alias) in name for alias in _spec_aliases(spec)):
            return spec
    return None


def sop_rank(filename: str) -> int:
    """Lower rank = earlier in TEST23 combine order. Unknown files stay last."""
    name = _norm(filename)
    for index, spec in enumerate(load_section_specs()):
        if any(_norm(alias) and _norm(alias) in name for alias in _spec_aliases(spec)):
            return index
    return 1000 + len(name)


def should_split_pages(filename: str, pages: int) -> bool:
    if not filename.lower().endswith(".pdf") or pages <= 1:
        return False
    spec = matched_spec(filename)
    return bool(spec and spec.get("split_pages"))


def display_label(filename: str, page: int = 0, page_count: int = 1) -> str:
    """UI name after upload/split (packet outline titles, not the raw filename)."""
    spec = matched_spec(filename)
    if spec:
        base = str(spec.get("label") or spec.get("name") or filename)
        split_label = str(spec.get("split_label") or "")
        first_label = str(spec.get("split_first_label") or "")
        if page > 0 and page_count > 1 and split_label:
            if first_label:
                if page == 1:
                    return first_label
                return split_label.replace("{page}", str(page - 1))
            return split_label.replace("{page}", str(page))
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
