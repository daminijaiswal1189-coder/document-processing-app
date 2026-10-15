import fitz

from models.plan_profile import DetectedSection, PlanProfile
from services.bookmark_service import add_bookmarks, is_testing_only


def _page(doc: fitz.Document, text: str) -> None:
    doc.new_page().insert_text((72, 72), text, fontsize=11)


def _only_doc() -> fitz.Document:
    doc = fitz.open()
    _page(
        doc,
        "Cover Letter\nAs you requested, we completed the ADP/ACP Test for your qualified "
        "retirement plan.\nA copy of the ADP/ACP test is included in this Valuation Package.",
    )
    _page(doc, "Result Summary\n402(g) Deferral Limits\nTested: Pass\n410(b) Coverage Test\nTested: Pass")
    _page(doc, "IMMEDIATE ACTION REQUIRED - ADP/ACP TEST FAILURE\nContribution refunds are required.")
    _page(doc, "Failed Compliance Testing\nExcess Return Notice\nCurrent method testing")
    _page(doc, "HCE/Key\nHighly Compensated Employees")
    _page(doc, "Future HCE\nNext year")
    _page(doc, "ADP/ACP Tests\nTest results follow.")
    return doc


def test_adp_acp_only_package_uses_the_short_bookmark_list():
    doc = _only_doc()
    profile = PlanProfile(
        plan_type="401k",
        detected_sections=[
            DetectedSection(name="Cover Letter", page=1, matched_alias="Cover Letter"),
            DetectedSection(name="Test Summary", page=2, matched_alias="Result Summary"),
            DetectedSection(name="Action Required", page=3, matched_alias="Action Required"),
            DetectedSection(name="402(g)", page=2, matched_alias="402(g)"),
            DetectedSection(name="410(b)", page=2, matched_alias="410(b)"),
            DetectedSection(name="Failed Test Notice", page=4, matched_alias="Excess Return Notice"),
            DetectedSection(name="HCE/Key", page=5, matched_alias="HCE/Key"),
            DetectedSection(name="Future HCE", page=6, matched_alias="Future HCE"),
            DetectedSection(name="ADP/ACP", page=1, matched_alias="ADP/ACP"),
        ],
    )
    try:
        assert is_testing_only(doc) is True
        add_bookmarks(doc, profile, source_files=["valuation.pdf"])
        titles = [row[1] for row in doc.get_toc()]
        adp_page = next(row[2] for row in doc.get_toc() if row[1] == "ADP/ACP Tests")
    finally:
        doc.close()
    assert titles == ["Cover Letter", "Test Summary", "HCE/Key", "Future HCE", "ADP/ACP Tests"]
    assert adp_page == 7


def test_another_report_uses_the_full_bookmark_list():
    doc = _only_doc()
    _page(doc, "Contribution Analysis\nTotal contributions allocated to each employee.")
    profile = PlanProfile(
        plan_type="401k",
        detected_sections=[
            DetectedSection(name="Cover Letter", page=1, matched_alias="Cover Letter"),
            DetectedSection(name="Test Summary", page=2, matched_alias="Result Summary"),
            DetectedSection(name="HCE/Key", page=5, matched_alias="HCE/Key"),
            DetectedSection(name="ADP/ACP", page=7, matched_alias="ADP/ACP"),
            DetectedSection(name="Contribution Analysis", page=8, matched_alias="Contribution Analysis"),
        ],
    )
    try:
        assert is_testing_only(doc) is False
        add_bookmarks(doc, profile)
        titles = [row[1] for row in doc.get_toc()]
    finally:
        doc.close()
    assert "Contribution Analysis" in titles
    assert "HCE/Key" in titles


def test_acp_only_403b_bookmarks_use_hce_and_acp_test():
    doc = fitz.open()
    _page(doc, "Cover Letter\nAs you requested, we completed the ACP Test.")
    _page(doc, "Result Summary\nACP Test: Fail")
    _page(doc, "HCE/Key\nHighly Compensated Employees")
    _page(doc, "Future HCE\nNext year")
    _page(doc, "ACP Test\nTest results follow.")
    profile = PlanProfile(
        plan_type="403b",
        detected_sections=[
            DetectedSection(name="Cover Letter", page=1, matched_alias="Cover Letter"),
            DetectedSection(name="Test Summary", page=2, matched_alias="Result Summary"),
            DetectedSection(name="HCE/Key", page=3, matched_alias="HCE/Key"),
            DetectedSection(name="Future HCE", page=4, matched_alias="Future HCE"),
            DetectedSection(name="ADP/ACP", page=5, matched_alias="ACP Test"),
        ],
    )
    try:
        assert is_testing_only(doc) is True
        add_bookmarks(doc, profile)
        titles = [row[1] for row in doc.get_toc()]
    finally:
        doc.close()
    assert titles == ["Cover Letter", "Test Summary", "HCE", "Future HCE", "ACP Test"]
