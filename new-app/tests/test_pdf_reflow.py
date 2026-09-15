import fitz

from models.review import RuleDecision
from services.pdf_modifier import apply_decisions


def _decisions(*pairs: tuple[str, str]) -> list[RuleDecision]:
    return [
        RuleDecision(rule_id=rule_id, section=rule_id, action=action, reason=action)
        for rule_id, action in pairs
    ]


def _spans(page: fitz.Page) -> list[dict]:
    found: list[dict] = []
    for block in page.get_text("dict").get("blocks") or []:
        if block.get("type") != 0:
            continue
        for line in block.get("lines") or []:
            found.extend(line.get("spans") or [])
    return found


def test_restack_moves_kept_text_up_and_keeps_color():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (54, 80),
        "IMMEDIATE ACTION REQUIRED - COMPLIANCE TEST FAILURE",
        fontsize=12,
        fontname="tiro",
        color=(1, 0, 0),
    )
    page.insert_text((54, 110), "Compliance refunds are required.", fontsize=11, fontname="tiro")
    page.insert_text(
        (54, 420),
        "NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME",
        fontsize=12,
        fontname="tiro",
        color=(0, 0.45, 0),
    )
    page.insert_text((54, 450), "No contribution refunds are required.", fontsize=11, fontname="tiro")
    apply_decisions(doc, _decisions(("A", "remove"), ("G", "keep")))
    page = doc[0]
    text = page.get_text("text") or ""
    assert "NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME" in text
    assert "COMPLIANCE TEST FAILURE" not in text
    words = page.get_text("words")
    assert words
    assert words[0][1] < 90
    kept = next(span for span in _spans(page) if "NO IMMEDIATE ACTION" in (span.get("text") or ""))
    assert kept["color"] != 0
    doc.close()


def test_restack_leaves_header_image_in_place():
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 30), False)
    pix.set_rect(pix.irect, (180, 0, 0))
    image_rect = fitz.Rect(500, 36, 560, 80)
    page.insert_image(image_rect, pixmap=pix)
    page.insert_text(
        (54, 200),
        "IMMEDIATE ACTION REQUIRED - COMPLIANCE TEST FAILURE",
        fontsize=12,
        fontname="helv",
        color=(1, 0, 0),
    )
    page.insert_text(
        (54, 480),
        "NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME",
        fontsize=12,
        fontname="helv",
        color=(0, 0.45, 0),
    )
    apply_decisions(doc, _decisions(("A", "remove"), ("G", "keep")))
    page = doc[0]
    assert page.get_images()
    xref = page.get_images()[0][0]
    rects = page.get_image_rects(xref)
    assert rects
    assert abs(rects[0].y0 - image_rect.y0) < 8
    assert "NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME" in (page.get_text("text") or "")
    assert "COMPLIANCE TEST FAILURE" not in (page.get_text("text") or "")
    doc.close()
