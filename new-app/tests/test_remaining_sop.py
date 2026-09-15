import re
from pathlib import Path

from services.orchestrator import process_uploads
from services.package_builder import RECAP_BULLETS, build_remaining_sop_pdf
from services.pdf_extractor import extract_plan_profile
from services.plan_profile_service import finalize_profile
from services.rules_engine import evaluate


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _pdf_text(path: str) -> str:
    import fitz

    doc = fitz.open(path)
    try:
        return _flat("\n".join(page.get_text("text") or "" for page in doc))
    finally:
        doc.close()


def _bytes(doc) -> bytes:
    data = doc.tobytes()
    doc.close()
    return data


def _process(tmp_path, monkeypatch, doc, source_folder=None):
    import services.save_service as save_service

    monkeypatch.setattr(save_service, "OUTPUT_DIR", tmp_path)
    return process_uploads(
        [("remaining-sop.pdf", _bytes(doc))],
        source_folder=source_folder,
    )


def test_remaining_flags_and_rules():
    doc = build_remaining_sop_pdf()
    try:
        profile = finalize_profile(extract_plan_profile(doc))
        assert profile.variance_report is True
        assert profile.contributions_required is True
        assert profile.keep_excess_summary is True
        assert profile.hce_current is True
        assert profile.safe_harbor is False
        by_id = {item.rule_id: item for item in evaluate(profile)}
        assert by_id["H"].action == "keep"
        assert by_id["M"].action == "keep"
        assert by_id["ES"].action == "keep"
        assert by_id["Y1"].action == "remove"
        assert by_id["Y2"].action == "remove"
        assert by_id["Y3"].action == "keep"
        assert by_id["Y4"].action == "remove"
        assert by_id["Y8"].action == "keep"
    finally:
        doc.close()


def test_variance_contributions_excess_and_current_recap(tmp_path, monkeypatch):
    result = _process(tmp_path, monkeypatch, build_remaining_sop_pdf())
    text = _pdf_text(result.pdf_path)
    assert "IMMEDIATE ACTION REQUIRED - VARIANCE" in text
    assert "IMMEDIATE ACTION REQUIRED - CONTRIBUTIONS" in text
    assert "Excess Summary Report" in text
    assert "the actual amount the employee can defer" in text
    assert "prior year data" not in text
    assert "did not have any Highly Compensated Employees" not in text
    assert "Safe Harbor Plan" not in text
    assert "not administered by Mutual of America" in text
    assert "employer match contribution is calculated" in text
    assert result.email_subject.startswith("MOA | 777777 |")
    assert Path(result.email_path).is_file()
    assert Path(result.log_path).is_file()
    assert result.review and result.review.ssn_found is False


def test_no_variance_or_contributions_removes_those_pages(tmp_path, monkeypatch):
    doc = build_remaining_sop_pdf(
        variance="No Variance Report",
        contributions="No Contributions Required",
        g402="Pass",
        returns="No Returns Required",
    )
    result = _process(tmp_path, monkeypatch, doc)
    by_id = {item.rule_id: item for item in result.rule_decisions}
    assert by_id["H"].action == "remove"
    assert by_id["M"].action == "remove"
    assert by_id["ES"].action == "remove"
    text = _pdf_text(result.pdf_path)
    assert "IMMEDIATE ACTION REQUIRED - VARIANCE" not in text
    assert "IMMEDIATE ACTION REQUIRED - CONTRIBUTIONS" not in text
    assert "Excess Summary Report" not in text


def test_excess_summary_kept_for_partially_vested_adp(tmp_path, monkeypatch):
    doc = build_remaining_sop_pdf(
        adp="Fail",
        g402="Pass",
        s415="Pass",
        partially_vested=True,
        variance="No Variance Report",
        contributions="No Contributions Required",
    )
    result = _process(tmp_path, monkeypatch, doc)
    assert result.plan_profile.keep_excess_summary is True
    assert "Excess Summary Report" in _pdf_text(result.pdf_path)


def test_recap_no_hce_keeps_no_hce_bullet(tmp_path, monkeypatch):
    doc = build_remaining_sop_pdf(hce_current="No", hce_future="No")
    result = _process(tmp_path, monkeypatch, doc)
    text = _pdf_text(result.pdf_path)
    assert "did not have any Highly Compensated Employees" in text
    assert "prior year data" not in text
    assert "the actual amount the employee can defer" not in text


def test_recap_prior_keeps_prior_bullet(tmp_path, monkeypatch):
    doc = build_remaining_sop_pdf(method="PRIOR")
    result = _process(tmp_path, monkeypatch, doc)
    text = _pdf_text(result.pdf_path)
    assert "prior year data" in text
    assert "the actual amount the employee can defer" not in text


def test_recap_safe_harbor_keeps_sh_bullet(tmp_path, monkeypatch):
    doc = build_remaining_sop_pdf(safe_harbor="Yes")
    result = _process(tmp_path, monkeypatch, doc)
    text = _pdf_text(result.pdf_path)
    assert "Safe Harbor Plan" in text
    assert "the actual amount the employee can defer" not in text


def test_recap_top_heavy_and_catchup_and_match(tmp_path, monkeypatch):
    keep = _process(
        tmp_path,
        monkeypatch,
        build_remaining_sop_pdf(top_heavy="Yes", catchup_allowed="Yes", per_payroll="Yes"),
    )
    keep_text = _pdf_text(keep.pdf_path)
    assert "Based on the top heavy testing results" in keep_text
    assert "designed to allow participants who were age 50" in keep_text

    drop_result = _process(
        tmp_path,
        monkeypatch,
        build_remaining_sop_pdf(top_heavy="No", catchup_allowed="No", per_payroll="No"),
    )
    drop_text = _pdf_text(drop_result.pdf_path)
    assert "Based on the top heavy testing results" not in drop_text
    assert "designed to allow participants who were age 50" not in drop_text
    assert "employer match contribution is calculated" not in drop_text


def test_ssn_scan_flags_census_page(tmp_path, monkeypatch):
    result = _process(tmp_path, monkeypatch, build_remaining_sop_pdf(include_ssn=True))
    assert result.review.ssn_found is True
    assert result.review.ssn_pages
    item = next(i for i in result.review.items if i.code == "ssn_scan")
    assert item.passed is False


def test_saves_copy_into_testing_folder(tmp_path, monkeypatch):
    testing = tmp_path / "800643" / "Testing" / "2024 Testing"
    package = testing / "Valuation Package"
    package.mkdir(parents=True)
    result = _process(
        tmp_path / "jobs",
        monkeypatch,
        build_remaining_sop_pdf(),
        source_folder=str(package),
    )
    copy = testing / result.filename
    assert copy.is_file()
    assert result.saved_copy_path == str(copy)


def test_recap_templates_match_test23():
    blob = " ".join(RECAP_BULLETS)
    assert "did not have any Highly Compensated Employees" in blob
    assert "prior year data" in blob
    assert "Safe Harbor Plan" in blob
    assert "not administered by Mutual of America" in blob
