import fitz

from services.pdf_extractor import extract_plan_profile
from services.review_service import validate

# TEST23 §B sample from the Soboba cover letter (selectable PDF text).
_COVER_LINES = [
    "March 8, 2022",
    "",
    "Soboba Band of Luiseno Indians DBA Soboba Casino Resort",
    "PO Box 81717",
    "San Jacinto, CA 92581",
    "",
    "RE: Soboba Casino Operations 401(k) Plan",
    "",
    "We are pleased to provide you with our completed administrative review of your",
    "qualified retirement plan for the period ending 12/31/2021. This Valuation Report",
    "contains a recap of the finalized census data and results of the IRS required",
    "testing for the plan year.",
    "",
    "Please take note of the testing results for this year and refer to the Action",
    "Required section of the Annual Valuation Report to determine if any items require",
    "your immediate attention.",
    "",
    "If you have questions, please let us know.",
]


def _soboba_cover_pdf() -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "\n".join(_COVER_LINES), fontsize=11)
    return doc


def test_review_extracts_company_address_plan_and_pye_from_cover_letter():
    doc = _soboba_cover_pdf()
    try:
        profile = extract_plan_profile(doc)
        review = validate(profile)
        by_code = {item.code: item for item in review.items}

        assert profile.company_name == "Soboba Band of Luiseno Indians DBA Soboba Casino Resort"
        assert profile.company_address == "PO Box 81717, San Jacinto, CA 92581"
        assert profile.plan_name == "Soboba Casino Operations 401(k) Plan"
        assert profile.plan_year_end == "12/31/2021"

        assert by_code["cover_company"].passed is True
        assert by_code["cover_address"].passed is True
        assert by_code["cover_plan_name"].passed is True
        assert by_code["cover_plan_year_end"].passed is True
        assert by_code["cover_company"].detail == profile.company_name
        assert by_code["cover_address"].detail == profile.company_address
        assert by_code["cover_plan_name"].detail == profile.plan_name
        assert by_code["cover_plan_year_end"].detail == profile.plan_year_end
    finally:
        doc.close()


def test_review_fails_cover_fields_when_letter_block_is_missing():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Annual Valuation Report\nNo cover letter header.", fontsize=11)
    try:
        profile = extract_plan_profile(doc)
        review = validate(profile)
        by_code = {item.code: item for item in review.items}
        assert profile.company_name is None
        assert profile.company_address is None
        assert profile.plan_name is None
        assert profile.plan_year_end is None
        assert by_code["cover_company"].passed is False
        assert by_code["cover_address"].passed is False
        assert by_code["cover_plan_name"].passed is False
        assert by_code["cover_plan_year_end"].passed is False
    finally:
        doc.close()
