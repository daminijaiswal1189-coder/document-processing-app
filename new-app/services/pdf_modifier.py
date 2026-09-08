from __future__ import annotations

from models.review import RuleDecision


def apply_decisions(_pdf_bytes: bytes, decisions: list[RuleDecision]) -> bytes:
    """Phase 4: remove/keep sections in the PDF. Not implemented yet."""
    raise NotImplementedError("PDF modification is Phase 4")
