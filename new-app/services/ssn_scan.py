from __future__ import annotations

import re

import fitz

# TEST23 / SRD: flag XXX-XX-XXXX and skip EIN (XX-XXXXXXX) and bare 6-digit plan numbers.
_SSN = re.compile(r"\b(\d{3}-\d{2}-\d{4})\b")
_EIN = re.compile(r"\b\d{2}-\d{7}\b")


def scan_ssns(doc: fitz.Document) -> list[int]:
    """Return 1-based page numbers that contain a Social Security Number."""
    pages: list[int] = []
    for page in doc:
        text = page.get_text("text") or ""
        for match in _SSN.finditer(text):
            start = max(0, match.start() - 3)
            window = text[start : match.end() + 1]
            if _EIN.search(window):
                continue
            pages.append(page.number + 1)
            break
    return pages
