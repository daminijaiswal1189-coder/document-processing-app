from pathlib import Path

import fitz

from services.logo_check import inspect_cover_stamp
from services.pdf_extractor import extract_plan_profile
from services.review_service import validate

_STAMP = Path(__file__).parent / "fixtures" / "moa-company-stamp.png"


def _write_any_image(path: Path) -> None:
    """Create a small non-MOA PNG (green block) so we test image placement, not brand colors."""
    helper = fitz.open()
    page = helper.new_page(width=80, height=40)
    page.draw_rect(page.rect, color=(0.2, 0.7, 0.3), fill=(0.2, 0.7, 0.3))
    pix = page.get_pixmap()
    pix.save(path)
    helper.close()


def _cover(*, text: bool, logo: bool) -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 200), "Mutual of America Financial Group", fontsize=12)
    if logo:
        width = page.rect.width
        page.draw_rect(fitz.Rect(width - 180, 36, width - 120, 90), color=(0.78, 0.12, 0.18), fill=(0.78, 0.12, 0.18))
        page.draw_rect(fitz.Rect(width - 118, 36, width - 58, 90), color=(0.10, 0.22, 0.40), fill=(0.10, 0.22, 0.40))
    return doc


def test_stamp_pass_when_text_and_upper_right_mark():
    doc = _cover(text=True, logo=True)
    try:
        result = inspect_cover_stamp(doc[0])
        assert result["moa_logo_found"] is True
        profile = extract_plan_profile(doc)
        review = validate(profile)
        stamp = next(item for item in review.items if item.code == "cover_moa")
        assert stamp.passed is True
    finally:
        doc.close()


def test_stamp_fails_when_only_wording():
    doc = _cover(text=True, logo=False)
    try:
        result = inspect_cover_stamp(doc[0])
        assert result["mentions_moa"] is True
        assert result["moa_logo_found"] is False
    finally:
        doc.close()


def test_review_passes_when_cover_has_wording_and_any_upper_right_image(tmp_path):
    image = tmp_path / "any-image.png"
    _write_any_image(image)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 220), "Mutual of America Financial Group", fontsize=12)
    width = page.rect.width
    page.insert_image(fitz.Rect(width - 170, 20, width - 20, 95), filename=str(image))
    try:
        profile = extract_plan_profile(doc)
        review = validate(profile)
        stamp = next(item for item in review.items if item.code == "cover_moa")
        assert profile.mentions_moa is True
        assert profile.moa_logo_found is True
        assert stamp.passed is True
        assert "image in upper-right" in (stamp.detail or "")
    finally:
        doc.close()


def test_review_fails_when_image_is_not_in_upper_right(tmp_path):
    image = tmp_path / "any-image.png"
    _write_any_image(image)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 80), "Mutual of America Financial Group", fontsize=12)
    page.insert_image(fitz.Rect(40, 620, 160, 700), filename=str(image))
    try:
        profile = extract_plan_profile(doc)
        review = validate(profile)
        stamp = next(item for item in review.items if item.code == "cover_moa")
        assert profile.mentions_moa is True
        assert stamp.passed is False
    finally:
        doc.close()


def test_stamp_fails_on_blank_cover():
    doc = _cover(text=False, logo=False)
    try:
        result = inspect_cover_stamp(doc[0])
        assert result["moa_logo_found"] is False
        assert result["mentions_moa"] is False
    finally:
        doc.close()


def _cover_with_company_stamp(rect: fitz.Rect) -> fitz.Document:
    assert _STAMP.exists(), f"Missing TEST23 company stamp fixture: {_STAMP}"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_image(rect, filename=str(_STAMP))
    return doc


def test_review_passes_with_real_moa_stamp_upper_right():
    """TEST23 §A: company stamp on the upper right of the cover letter."""
    doc = fitz.open()
    page = doc.new_page()
    width = page.rect.width
    page.insert_image(fitz.Rect(width - 280, 18, width - 24, 92), filename=str(_STAMP))
    try:
        profile = extract_plan_profile(doc)
        review = validate(profile)
        stamp = next(item for item in review.items if item.code == "cover_moa")
        assert profile.moa_logo_found is True
        assert stamp.passed is True
        assert "image in upper-right" in (stamp.detail or "")
        assert "red and navy" in (stamp.detail or "")
    finally:
        doc.close()


def test_review_fails_when_real_moa_stamp_is_not_upper_right():
    doc = _cover_with_company_stamp(fitz.Rect(36, 680, 260, 760))
    try:
        profile = extract_plan_profile(doc)
        review = validate(profile)
        stamp = next(item for item in review.items if item.code == "cover_moa")
        assert profile.moa_logo_found is False
        assert stamp.passed is False
    finally:
        doc.close()
