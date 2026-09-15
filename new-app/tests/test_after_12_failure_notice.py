import re

import fitz

from services.orchestrator import process_uploads
from services.package_builder import (
    AFTER_12_CURRENT_NOTICE,
    AFTER_12_PRIOR_NOTICE,
    build_after_12_failure_notice_pdf,
)
from services.pdf_extractor import extract_plan_profile
from services.plan_profile_service import finalize_profile
from services.rules_engine import evaluate


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _pdf_text(path: str) -> str:
    doc = fitz.open(path)
    try:
        return _flat("\n".join(page.get_text("text") or "" for page in doc))
    finally:
        doc.close()


def _bytes(doc: fitz.Document) -> bytes:
    data = doc.tobytes()
    doc.close()
    return data


def _process(tmp_path, monkeypatch, doc):
    import services.save_service as save_service

    monkeypatch.setattr(save_service, "OUTPUT_DIR", tmp_path)
    return process_uploads([("after-12-notice.pdf", _bytes(doc))])


def test_after_12_current_extracts_qnec_and_refunds():
    doc = build_after_12_failure_notice_pdf(method="CURRENT")
    try:
        profile = finalize_profile(extract_plan_profile(doc))
        assert profile.testing_method == "CURRENT"
        assert profile.after_12_months is True
        assert profile.adp_qnec == 142540.41
        assert profile.acp_qnec == 42814.34
        assert profile.total_qnec == 185354.75
        assert profile.deferral_refund == 17571.0
        assert profile.match_refund == 116.6
        by_id = {item.rule_id: item for item in evaluate(profile)}
        assert by_id["D"].action == "keep"
        assert by_id["E"].action == "remove"
        assert by_id["I"].action == "remove"
    finally:
        doc.close()


def test_c2_current_keeps_notice_and_fills_qnec_and_refunds(tmp_path, monkeypatch):
    result = _process(tmp_path, monkeypatch, build_after_12_failure_notice_pdf(method="CURRENT"))
    by_id = {item.rule_id: item for item in result.rule_decisions}
    assert by_id["D"].action == "keep"
    assert by_id["E"].action == "remove"
    assert by_id["I"].action == "remove"
    text = _pdf_text(result.pdf_path)
    assert "Current method testing" in text
    assert "Prior method testing" not in text
    assert "ADP/ACP test is $185,354.75" in text
    assert "The ADP QNEC is $142,540.41" in text
    assert "The ACP QNEC is $42,814.34" in text
    assert "Deferral Contribution of $17,571.00" in text
    assert "Match Contribution of $116.60" in text
    assert "$X,XXX,XXX.XX" not in text


def test_c2_adp_only_drops_acp_qnec_line(tmp_path, monkeypatch):
    doc = build_after_12_failure_notice_pdf(method="CURRENT", acp="Pass", acp_qnec=None)
    result = _process(tmp_path, monkeypatch, doc)
    text = _pdf_text(result.pdf_path)
    assert "The ADP QNEC is $142,540.41" in text
    assert "The ACP QNEC is" not in text
    assert "ADP/ACP test is $142,540.41" in text


def test_c3_prior_keeps_notice_and_fills_refunds_only(tmp_path, monkeypatch):
    result = _process(tmp_path, monkeypatch, build_after_12_failure_notice_pdf(method="PRIOR"))
    by_id = {item.rule_id: item for item in result.rule_decisions}
    assert result.plan_profile.testing_method == "PRIOR"
    assert by_id["E"].action == "keep"
    assert by_id["D"].action == "remove"
    assert by_id["I"].action == "remove"
    text = _pdf_text(result.pdf_path)
    assert "Prior method testing" in text
    assert "Current method testing" not in text
    assert "Deferral Contribution of $17,571.00" in text
    assert "Match Contribution of $116.60" in text
    assert "The ADP QNEC is" not in text
    assert "The ACP QNEC is" not in text


def test_c3_prior_drops_missing_match_refund_line(tmp_path, monkeypatch):
    doc = build_after_12_failure_notice_pdf(method="PRIOR", match=None)
    result = _process(tmp_path, monkeypatch, doc)
    text = _pdf_text(result.pdf_path)
    assert "Deferral Contribution of $17,571.00" in text
    assert "Match Contribution of" not in text


def test_not_after_12_does_not_keep_c2_or_c3():
    from models.plan_profile import PlanProfile

    profile = finalize_profile(
        PlanProfile(
            testing_method="CURRENT",
            adp_failed=True,
            returns_required=True,
            after_12_months=False,
        )
    )
    by_id = {item.rule_id: item for item in evaluate(profile)}
    assert by_id["D"].action == "remove"
    assert by_id["E"].action == "remove"
    assert by_id["I"].action == "keep"


def test_after_12_templates_match_test23():
    assert "Current method testing" in AFTER_12_CURRENT_NOTICE
    assert "ADP/ACP test is $X,XXX,XXX.XX" in AFTER_12_CURRENT_NOTICE
    assert "Deferral Contribution of $X,XXX,XXX.XX" in AFTER_12_CURRENT_NOTICE
    assert "Prior method testing" in AFTER_12_PRIOR_NOTICE
    assert "ADP QNEC" not in AFTER_12_PRIOR_NOTICE
