import fitz

from models.plan_profile import DetectedSection, PlanProfile
from services.assembly_stops import _missing_report_reasons
from services.bookmark_service import add_bookmarks
from services.package_polish import exclude_brf_uploads, package_is_403b, rewrite_403b_adp_mentions
from services.pdf_modifier import apply_recap_bullets, fill_qnec_placeholders
from services.plan_config import paragraphs_for, plan_family, rules_for
from services.plan_profile_service import finalize_profile
from services.rules_engine import evaluate


def test_cover_plan_name_chooses_the_configuration():
    assert plan_family("RE: Michigan United Credit Union 401(k) Savings Plan") == "401k"
    assert plan_family("RE: GRACE MEDICAL HOME, INC. 403(B) PLAN") == "403b"


def test_401k_rules_stay_on_the_401k_configuration():
    profile = finalize_profile(
        PlanProfile(
            plan_type="401k",
            testing_method="PRIOR",
            adp_failed=True,
            acp_failed=False,
            returns_required=True,
        )
    )
    by_id = {item.rule_id: item for item in evaluate(profile)}
    assert profile.adp_failed is True
    assert by_id["B"].action == "keep"
    assert "Y10" not in by_id
    headings = [
        str(item.get("heading") or "")
        for item in paragraphs_for("401k").get("action_required_headings") or []
    ]
    assert "IMMEDIATE ACTION REQUIRED - ACP TEST FAILURE" not in headings
    assert "IMMEDIATE ACTION REQUIRED - ADP/ACP TEST FAILURE" in headings


def test_403b_uses_its_own_configuration():
    profile = finalize_profile(
        PlanProfile(
            plan_type="403b",
            testing_method="PRIOR",
            adp_failed=True,
            acp_failed=False,
            returns_required=True,
        )
    )
    by_id = {item.rule_id: item for item in evaluate(profile)}
    assert profile.adp_failed is False
    assert by_id["B"].action == "remove"
    assert by_id["Y10"].action == "keep"
    rule_ids = [str(item.get("id")) for item in rules_for("401k").get("rules") or []]
    assert "Y10" not in rule_ids
    headings = [
        str(item.get("heading") or "")
        for item in paragraphs_for("403b").get("action_required_headings") or []
    ]
    assert "IMMEDIATE ACTION REQUIRED - ACP TEST FAILURE" in headings
    assert "IMMEDIATE ACTION REQUIRED - ADP/ACP TEST FAILURE" not in headings


def test_403b_keeps_the_brf_report_file():
    uploads = [("BRF Test.pdf", b"%PDF"), ("Grace 403(b) Cover.pdf", b"%PDF")]
    assert package_is_403b(uploads) is True
    kept, notes = exclude_brf_uploads(uploads, keep_brf=True)
    assert [name for name, _data in kept] == ["BRF Test.pdf", "Grace 403(b) Cover.pdf"]
    assert notes == []


def test_403b_does_not_require_the_410b_report():
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Cover Letter", fontsize=11)
    try:
        missing_401 = " ".join(_missing_report_reasons(doc, PlanProfile(plan_type="401k"), ["cover.pdf"]))
        missing_403 = " ".join(_missing_report_reasons(doc, PlanProfile(plan_type="403b"), ["cover.pdf"]))
    finally:
        doc.close()
    assert "410(b) Test Report" in missing_401
    assert "410(b) Test Report" not in missing_403


def test_403b_bookmark_includes_the_brf_test():
    profile = PlanProfile(
        plan_type="403b",
        detected_sections=[DetectedSection(name="BRF", page=1, matched_alias="BRF")],
    )
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Benefits, Rights and Features\nBRF Test", fontsize=11)
    try:
        assert add_bookmarks(doc, profile) == 1
        assert doc.get_toc()[0][1] == "Benefits, Rights and Features test"
    finally:
        doc.close()


def test_403b_current_notice_uses_the_acp_qnec_only():
    profile = finalize_profile(
        PlanProfile(plan_type="403b", testing_method="CURRENT", acp_failed=True, acp_qnec=818.86, returns_required=True)
    )
    assert profile.adp_failed is False
    assert profile.total_qnec == 818.86
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (54, 72),
        "Failed Compliance Testing\nCurrent method testing: the ACP test is $X,XXX,XXX.XX.",
        fontsize=11,
    )
    try:
        fill_qnec_placeholders(doc, profile)
        text = doc[0].get_text("text") or ""
    finally:
        doc.close()
    assert "ACP test is $818.86" in text
    assert "ADP" not in text


def test_403b_prior_failure_does_not_keep_the_current_notice():
    profile = finalize_profile(
        PlanProfile(
            plan_type="403b",
            testing_method="PRIOR",
            acp_failed=True,
            returns_required=True,
            adp_failed=True,
        )
    )
    by_id = {item.rule_id: item for item in evaluate(profile)}
    assert by_id["B"].action == "keep"
    assert by_id["I"].action == "remove"
    assert by_id["J_ADP"].action == "remove"
    assert by_id["J_ACP"].action == "keep"


def test_403b_rewrites_adp_acp_wording_to_acp():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Review the ADP/ACP test results.", fontsize=12)
    page.insert_text((72, 96), "The ADP test failed.", fontsize=12)
    try:
        notes = rewrite_403b_adp_mentions(doc)
        text = doc[0].get_text("text") or ""
    finally:
        doc.close()
    assert notes
    assert "ADP" not in text
    assert "ACP" in text


def test_special_catchup_bullet_is_removed_when_it_does_not_apply():
    from models.review import RuleDecision

    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(
        fitz.Rect(54, 72, 540, 400),
        "Important Information\n"
        "- Your plan is designed to allow participants who were age 50 or older.\n"
        "- Participants with fifteen or more years of service may make a special catch-up contribution.\n",
        fontsize=11,
    )
    decisions = [
        RuleDecision(rule_id="Y6", section="catch-up", action="keep", reason=""),
        RuleDecision(rule_id="Y10", section="special", action="remove", reason=""),
    ]
    try:
        removed = apply_recap_bullets(doc, decisions, "403b")
        text = doc[0].get_text("text") or ""
    finally:
        doc.close()
    assert "Y10" in removed
    assert "fifteen or more years" not in text
    assert "age 50" in text
