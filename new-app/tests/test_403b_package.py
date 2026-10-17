import json

import fitz

from models.plan_profile import DetectedSection, PlanProfile
from services.assembly_stops import _missing_report_reasons
from services.bookmark_service import add_bookmarks
from services.package_polish import exclude_brf_uploads, package_is_403b, rewrite_403b_adp_mentions
from services.pdf_modifier import apply_recap_bullets, fill_qnec_placeholders
from services.plan_config import paragraphs_for, plan_family, rules_for
from services.plan_profile_service import finalize_profile
from services.rules_engine import evaluate
from services.source_profile import parse_summary_text


def test_cover_plan_name_chooses_the_configuration():
    assert plan_family("RE: Michigan United Credit Union 401(k) Savings Plan") == "401k"
    assert plan_family("RE: GRACE MEDICAL HOME, INC. 403(B) PLAN") == "403b"


def test_403b_result_summary_passes_remove_every_failure_rule():
    overlay = parse_summary_text(
        """
        Compliance Testing Summary of Results
        Plan Year End: June 30, 2026
        EXAMPLE 403(B) PLAN
        800643
        410(b) Coverage Test
        Test: Pass
        402(g) Deferral Limits
        Test: Pass
        415(c) Annual Additions
        Test: Pass
        Average Contribution Percentage (ACP)
        Test: Pass
        """
    )
    profile = finalize_profile(
        PlanProfile(plan_type="403b", testing_method=None, **overlay)
    )
    by_id = {item.rule_id: item for item in evaluate(profile)}
    assert profile.acp_failed is False
    assert profile.fail_402g is False
    assert profile.fail_415 is False
    assert profile.returns_required is False
    assert profile.has_action_required is False
    for rule_id in ("A", "B", "C", "D", "E", "I", "J_ACP", "K", "L", "M"):
        assert by_id[rule_id].action == "remove"
    assert by_id["G"].action == "keep"


def test_selectable_403b_pass_package_keeps_only_no_action_and_information(tmp_path, monkeypatch):
    import services.save_service as save_service
    from services.orchestrator import process_uploads

    monkeypatch.setattr(save_service, "OUTPUT_DIR", tmp_path)

    def pdf(name: str, text: str) -> tuple[str, bytes]:
        doc = fitz.open()
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(40, 40, 570, 800), text, fontsize=9)
        data = doc.tobytes()
        doc.close()
        return name, data

    uploads = [
        pdf(
            "800643 2025 403b Cover Letter.pdf",
            "Mutual of America\nPlan Number: 800643\n"
            "RE: EXAMPLE COMPANY 403(B) PLAN\n"
            "We completed the review for the period ending 06/30/2026.",
        ),
        pdf(
            "2026 Result Summary.pdf",
            "Compliance Testing Summary of Results\nPlan Year End: June 30, 2026\n"
            "EXAMPLE COMPANY 403(B) PLAN\n800643\n"
            "410(b) Coverage Test\nTest: Pass\n"
            "402(g) Deferral Limits\nTest: Pass\n"
            "415(c) Annual Additions\nTest: Pass\n"
            "Average Contribution Percentage (ACP)\nTest: Pass",
        ),
        pdf(
            "Action Required.pdf",
            "Annual Valuation Report\n"
            "IMMEDIATE ACTION REQUIRED - COMPLIANCE TEST FAILURE\nRefunds required.\n"
            "IMMEDIATE ACTION REQUIRED - ACP TEST FAILURE\n"
            "Refunds required unless QNEC contributions will be made.\n"
            "IMMEDIATE ACTION REQUIRED - CONTRIBUTIONS\nContributions required.\n"
            "NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME\nNo action is required.",
        ),
        pdf(
            "ACP Prior Failure.pdf",
            "IMMEDIATE ACTION REQUIRED - ACP PRIOR METHOD TEST FAILURE\nRefunds required.",
        ),
        pdf(
            "ACP Failure letter.pdf",
            "SAMPLE/DRAFT Communication to Participant\n"
            "Actual Contribution Percentage (ACP)\nACP nondiscrimination testing failure.",
        ),
        pdf(
            "Excess Return Notice.pdf",
            "Failed Compliance Testing\nExcess Return Notice\nCurrent method testing:\nACP test is $1.00",
        ),
        pdf(
            "415(c) Failure Information.pdf",
            "Annual Additions (IRC 415) Test Failure Information\nNo details.",
        ),
        pdf(
            "402g Failure letter.pdf",
            "SAMPLE/DRAFT\n402(g) Deferral Limit\nThe limit has been exceeded.",
        ),
        pdf(
            "415 Failure letter.pdf",
            "Annual Additions (IRC 415) limit has been exceeded",
        ),
        pdf(
            "Important Information.pdf",
            "Important Information\n- Your plan is designed to allow participants who were age 50 or older.",
        ),
        pdf("2026HCEKey.pdf", "HCE/Key\nCurrent highly compensated employees."),
        pdf("2027HCE.pdf", "Future HCE\nFuture highly compensated employees."),
    ]
    result = process_uploads(uploads, auto_order=True)
    output = fitz.open(result.pdf_path)
    try:
        text = "\n".join(page.get_text("text") or "" for page in output)
    finally:
        output.close()

    assert result.filename == "800643_2025-Valuation.pdf"
    assert "NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME" in text, [
        (item.rule_id, item.action, item.reason) for item in result.rule_decisions
    ]
    assert "Important Information" in text
    assert "IMMEDIATE ACTION REQUIRED -" not in text
    assert "Failed Compliance Testing" not in text
    assert "SAMPLE/DRAFT" not in text
    assert "Test Failure Information" not in text
    assert "limit has been exceeded" not in text
    debug = json.loads(
        (tmp_path / result.job_id / "profile_debug.json").read_text(encoding="utf-8")
    )
    assert debug["plan_type"] == "403b"
    assert debug["acp_failed"] is False
    assert debug["fail_402g"] is False
    assert debug["fail_415"] is False
    assert debug["returns_required"] is False
    assert "No Action Message" in debug["selected_sections"]
    assert "ACP Failure Notice (CURRENT)" in debug["removed_sections"]
    assert any(
        item["rule_id"] == "I"
        and item["action"] == "remove"
        and item["source_matches"]
        for item in debug["before_edit_section_decisions"]
    )
    assert debug["field_sources"]["acp_failed"].startswith("Result Summary:")


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
