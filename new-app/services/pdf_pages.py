from __future__ import annotations

from pathlib import Path

import fitz


def pdf_page_count(data: bytes) -> int:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        return max(1, int(doc.page_count or 1))
    finally:
        doc.close()


def pdf_page_count_path(path: Path) -> int:
    if path.suffix.lower() != ".pdf":
        return 1
    try:
        doc = fitz.open(path)
        try:
            return max(1, int(doc.page_count or 1))
        finally:
            doc.close()
    except Exception:
        return 1


def extract_pdf_page(data: bytes, page: int) -> bytes:
    """Return a one-page PDF. page is 1-based."""
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        index = page - 1
        if index < 0 or index >= doc.page_count:
            raise ValueError(f"page {page} is not in this PDF ({doc.page_count} pages)")
        out = fitz.open()
        out.insert_pdf(doc, from_page=index, to_page=index)
        return out.tobytes()
    finally:
        doc.close()


def paged_filename(name: str, page: int) -> str:
    path = Path(name)
    return f"{path.stem}_p{page:02d}{path.suffix}"


def expand_uploads_by_page(
    uploads: list[tuple[str, bytes]],
    names: list[str],
    pages: list[int],
) -> tuple[list[tuple[str, bytes]], list[str]]:
    """Build the merge list from UI rows. page <= 0 means the whole file."""
    by_name = {name: data for name, data in uploads}
    ordered: list[tuple[str, bytes]] = []
    warnings: list[str] = []
    whole_used: set[str] = set()
    for index, name in enumerate(names):
        if not name:
            continue
        data = by_name.get(name)
        if data is None:
            warnings.append(f"Not in folder or upload (skipped): {name}")
            continue
        page = pages[index] if index < len(pages) else 0
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 0
        if not name.lower().endswith(".pdf") or page <= 0:
            if name in whole_used:
                continue
            whole_used.add(name)
            ordered.append((name, data))
            continue
        try:
            ordered.append((paged_filename(name, page), extract_pdf_page(data, page)))
        except Exception as exc:
            warnings.append(f"Could not use {name} page {page}: {exc}")
    return ordered, warnings
