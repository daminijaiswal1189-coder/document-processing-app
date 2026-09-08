from __future__ import annotations

import fitz

from models.plan_profile import DetectedSection


def add_bookmarks(doc: fitz.Document, sections: list[DetectedSection]) -> None:
    """Phase 4: write TOC from remaining sections."""
    raise NotImplementedError("Bookmark generation is Phase 4")
