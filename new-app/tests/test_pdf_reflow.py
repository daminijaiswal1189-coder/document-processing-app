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


def test_shared_adp_acp_heading_removes_only_the_prior_block():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((54, 80), "IMMEDIATE ACTION REQUIRED - ADP/ACP TEST FAILURE", fontsize=11)
    page.insert_text((54, 100), "Contribution refunds are required. Review the Correction Method summary.", fontsize=11)
    page.insert_text((54, 180), "IMMEDIATE ACTION REQUIRED - ADP/ACP TEST FAILURE", fontsize=11)
    page.insert_text((54, 200), "Refunds are required unless QNEC contributions will be made.", fontsize=11)
    page.insert_text((54, 280), "NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME", fontsize=11)
    apply_decisions(doc, _decisions(("B", "remove"), ("C", "keep"), ("G", "keep")))
    text = doc[0].get_text("text") or ""
    assert "Review the Correction Method summary" not in text
    assert "unless QNEC contributions will be made" in text
    assert "NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME" in text
    doc.close()


def test_after_12_month_headings_are_removed():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (54, 80),
        "IMMEDIATE ACTION REQUIRED - ADP/ACP PRIOR METHOD TEST FAILURE - AFTER 12-MONTHS",
        fontsize=9,
    )
    page.insert_text((54, 110), "Prior method after 12 months stays only when that rule matches.", fontsize=10)
    page.insert_text(
        (54, 160),
        "IMMEDIATE ACTION REQUIRED - ADP/ACP CURRENT METHOD TEST FAILURE - AFTER 12-MONTHS",
        fontsize=9,
    )
    page.insert_text((54, 190), "Current method after 12 months.", fontsize=10)
    page.insert_text((54, 240), "NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME", fontsize=11)
    apply_decisions(doc, _decisions(("D", "remove"), ("E", "remove"), ("G", "keep")))
    text = doc[0].get_text("text") or ""
    assert "AFTER 12-MONTHS" not in text
    assert "NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME" in text
    doc.close()


def test_variance_client_copy_keeps_contributions_paragraph(tmp_path, monkeypatch):
    import services.save_service as save_service
    from services.orchestrator import process_uploads
    from services.package_polish import has_variance_client_copy

    variance = fitz.open()
    variance_page = variance.new_page()
    variance_page.insert_text((72, 72), "Variance Report\nPlan Number 111111\nSample Plan", fontsize=11)
    empty = fitz.open()
    empty.new_page()
    try:
        assert has_variance_client_copy(["2025MaVar.pdf"], empty)
        assert has_variance_client_copy(["cover.pdf"], variance)
        assert not has_variance_client_copy(["cover.pdf"], empty)
    finally:
        empty.close()

    monkeypatch.setattr(save_service, "OUTPUT_DIR", tmp_path)
    cover = fitz.open()
    cover_page = cover.new_page()
    cover_page.insert_text(
        (54, 72),
        "Cover Letter\nMarch 8, 2026\nMichigan United Credit Union\n"
        "RE: Michigan United Credit Union 401(k) Savings Plan\n"
        "We are pleased to provide you with our completed administrative review of your\n"
        "qualified retirement plan for the period ending 12/31/2025.\n"
        "Plan Number: 900062\n\n"
        "IMMEDIATE ACTION REQUIRED - CONTRIBUTIONS\n"
        "A Contribution and/or adjustment is required.\n",
        fontsize=11,
    )
    try:
        result = process_uploads(
            [
                ("01_cover.pdf", cover.tobytes()),
                ("2025MaVar.pdf", variance.tobytes()),
            ]
        )
    finally:
        cover.close()
        variance.close()
    by_id = {item.rule_id: item for item in result.rule_decisions}
    assert result.plan_profile.contributions_required is True
    assert by_id["M"].action == "keep"
    saved = fitz.open(result.pdf_path)
    try:
        text = "\n".join(page.get_text("text") or "" for page in saved)
        assert "A Contribution and/or adjustment is required" in text
    finally:
        saved.close()


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
