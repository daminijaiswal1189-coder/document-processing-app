import fitz

from models.plan_profile import PlanProfile
from models.review import RuleDecision
from services.midyear import apply_letter, order_uploads, package_is_midyear, read_letter_facts, reorder_pages
from services.package_polish import remove_disallowed_wording
from services.pdf_modifier import apply_recap_bullets
from services.plan_457 import remove_contribution_overview
from services.plan_config import plan_family
from services.plan_profile_service import finalize_profile
from services.rules_engine import evaluate
from services.save_service import valuation_filename
from services.source_profile import parse_excel


def _page(doc: fitz.Document, text: str) -> None:
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(54, 54, 540, 760), text, fontsize=11, fontname="helv")


def test_plan_name_still_chooses_401k_and_403b():
    assert plan_family("RE: Michigan United Credit Union 401(k) Savings Plan") == "401k"
    assert plan_family("RE: GRACE MEDICAL HOME, INC. 403(B) PLAN") == "403b"
    assert plan_family("RE: CITY HOSPITAL 457 PLAN") == "457"


def test_457_non_governmental_removes_catchup_and_unused_forfeiture_lines():
    profile = finalize_profile(
        PlanProfile(plan_type="457", non_governmental=True, plan_year_end="12/31/2025")
    )
    assert profile.catchup_disallowed is True
    assert profile.forfeitures_reallocated is False
    by_id = {item.rule_id: item for item in evaluate(profile)}
    assert by_id["Y6"].action == "remove"
    assert by_id["Y11"].action == "remove"
    assert by_id["Y12"].action == "remove"
    assert by_id["Y13"].action == "remove"
    assert "Y12" not in {item.rule_id for item in evaluate(PlanProfile(plan_type="401k"))}


def test_457_keeps_a_forfeiture_line_only_when_the_log_says_so():
    profile = finalize_profile(PlanProfile(plan_type="457", forfeitures_reallocated=True, no_forfeitures=True))
    by_id = {item.rule_id: item for item in evaluate(profile)}
    assert by_id["Y12"].action == "keep"
    assert by_id["Y13"].action == "keep"
    doc = fitz.open()
    _page(
        doc,
        "Important Information\n\n"
        "- The reallocation of forfeitures is in the process of being completed.\n\n"
        "- There were no forfeitures available to reallocate for the 2020 plan year.\n\n"
        "- Your plan is designed to allow participants who were age 50 or older.\n",
    )
    decisions = [
        RuleDecision(rule_id="Y6", section="catch-up", action="keep", reason=""),
        RuleDecision(rule_id="Y12", section="forfeiture", action="keep", reason=""),
        RuleDecision(rule_id="Y13", section="none", action="remove", reason=""),
    ]
    try:
        removed = apply_recap_bullets(doc, decisions, "457")
        text = doc[0].get_text("text") or ""
    finally:
        doc.close()
    assert "Y13" in removed
    assert "no forfeitures" not in text
    assert "reallocation of forfeitures" in text


def test_457_excel_yes_marks_the_plan_non_governmental():
    from openpyxl import Workbook
    import io

    book = Workbook()
    sheet = book.active
    sheet["A1"] = "Plan Type"
    sheet["A2"] = "457"
    sheet["A6"] = "If this is a 457 Plan is it a Non-Governmental plan? (Yes/No)"
    sheet["B6"] = "Yes"
    sheet["A7"] = "Forfeitures reallocated? (yes/no)"
    sheet["B7"] = "Yes"
    buffer = io.BytesIO()
    book.save(buffer)
    overlay = parse_excel(buffer.getvalue())
    assert overlay["plan_type"] == "457"
    assert overlay["non_governmental"] is True
    assert overlay["forfeitures_reallocated"] is True


def test_457_keeps_soc_and_drops_the_analysis_blurb_without_the_report():
    doc = fitz.open()
    _page(doc, "Statement of Contribution\nParticipant deposits for the year.")
    _page(
        doc,
        "Administrative Reports\n\n"
        "CONTRIBUTION ANALYSIS\n"
        "A summary of total contributions allocated to each employee by contribution source.\n",
    )
    try:
        notes = remove_disallowed_wording(doc, keep_soc=True)
        overview = remove_contribution_overview(doc)
        text = "\n".join(page.get_text("text") or "" for page in doc)
    finally:
        doc.close()
    assert notes == []
    assert overview
    assert "Statement of Contribution" in text
    assert "CONTRIBUTION ANALYSIS" not in text.upper()


def test_midyear_filename_order_and_letter():
    profile = PlanProfile(
        plan_number="900062",
        beginning_plan_year="2025",
        midyear=True,
        midyear_failed=True,
        testing_method="CURRENT",
        hce_max_deferral=8.5,
    )
    assert valuation_filename(profile) == "900062_MidYearTesting_2_2025_2025-Mid-Year-ADP-Test.pdf"
    assert valuation_filename(PlanProfile(plan_number="900062", beginning_plan_year="2025")) == (
        "900062_2025-Valuation.pdf"
    )
    ordered = order_uploads(
        [
            ("ADP Detail.pdf", b"d"),
            ("Mid-Year Letter.pdf", b"l"),
            ("ADP Summary.pdf", b"s"),
        ]
    )
    assert [name for name, _data in ordered] == ["Mid-Year Letter.pdf", "ADP Summary.pdf", "ADP Detail.pdf"]

    doc = fitz.open()
    _page(doc, "ADP Detail\nADP test Fail\nThe maximum deferral percentage for the HCEs is 8.50%.")
    letter = doc.new_page()
    letter.insert_text(
        (54, 72),
        "\n".join(
            [
                "March 1, 2026",
                "We have completed a mid-year ADP/ACP test for the plan year ending 12/31/2025.",
                "The result of this mid-year analysis is attached. It is within the range allowed.",
                "The result of this mid-year analysis is attached. It exceeds the range allowed.",
                "The maximum deferral percentage for the HCEs is <xx.xx%>.",
                "As an alternative to reducing the HCEs deferrals, the employer may contribute enough money.",
                "Please remember that this is merely a projection based on the current situation.",
                "Thank you for allowing us to serve you.",
                "CUNA Mutual Retirement Solutions",
            ]
        ),
        fontsize=11,
    )
    _page(doc, "ADP Summary\nADP test Fail")
    try:
        assert package_is_midyear([("Mid-Year Letter.pdf", b"")]) is True
        reorder_pages(doc)
        facts = read_letter_facts(doc)
        assert facts["midyear_failed"] is True
        assert facts["plan_year_end"] == "12/31/2025"
        assert facts["hce_max_deferral"] == 8.5
        apply_letter(doc, profile)
        letter = doc[0].get_text("text") or ""
    finally:
        doc.close()
    assert "within the range allowed" not in letter
    assert "exceeds the range allowed" in letter
    assert "8.50%" in letter
    assert "alternative to reducing" in letter
    assert "merely a projection" in letter
    assert "CUNA Mutual" in letter
