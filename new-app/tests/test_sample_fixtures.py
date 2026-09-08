from pathlib import Path

import fitz
import pytest

from services.orchestrator import process_uploads
from services.pdf_extractor import extract_plan_profile
from services.plan_profile_service import finalize_profile
from services.rules_engine import evaluate

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _open(name: str) -> fitz.Document:
    path = FIXTURES / name
    if not path.is_file():
        pytest.skip(f"missing fixture {path}")
    return fitz.open(path)


def test_pass_package_fills_profile_and_rule_g():
    doc = _open("01_pass_no_action.pdf")
    try:
        profile = finalize_profile(extract_plan_profile(doc))
    finally:
        doc.close()
    assert profile.plan_number == "111111"
    assert profile.plan_name == "ABC Pass 401(k) Plan"
    assert profile.company_name == "ABC Pass Company"
    assert profile.company_address
    assert profile.plan_type == "401k"
    assert profile.plan_year_start == "01/01/2024"
    assert profile.beginning_plan_year == "2024"
    assert profile.testing_method == "CURRENT"
    assert profile.top_heavy is False
    assert profile.adp_failed is False
    assert profile.acp_failed is False
    assert profile.fail_402g is False
    assert profile.fail_415 is False
    assert profile.testing_failed is False
    assert profile.returns_required is False
    assert profile.has_action_required is False
    assert len(profile.detected_sections) >= 14
    by_id = {d.rule_id: d for d in evaluate(profile)}
    assert by_id["G"].action == "keep"
    assert by_id["A"].action == "remove"
    assert by_id["F"].action == "remove"


def test_current_fail_package_rules_a_c_d_f():
    doc = _open("02_current_fail_qnec.pdf")
    try:
        profile = finalize_profile(extract_plan_profile(doc))
    finally:
        doc.close()
    assert profile.plan_number == "222222"
    assert profile.testing_method == "CURRENT"
    assert profile.top_heavy is True
    assert profile.adp_failed is True
    assert profile.fail_402g is True
    assert profile.fail_415 is True
    assert profile.returns_required is True
    assert profile.after_12_months is True
    assert profile.total_qnec == 1550.0
    assert profile.deferral_refund == 450.0
    by_id = {d.rule_id: d for d in evaluate(profile)}
    assert by_id["A"].action == "keep"
    assert by_id["C"].action == "keep"
    assert by_id["B"].action == "remove"
    assert by_id["D"].action == "keep"
    assert by_id["F"].action == "keep"
    assert by_id["G"].action == "remove"


def test_prior_offcalendar_filename_year_2017():
    doc = _open("03_prior_fail_offcalendar.pdf")
    try:
        profile = finalize_profile(extract_plan_profile(doc))
    finally:
        doc.close()
    assert profile.plan_number == "333333"
    assert profile.beginning_plan_year == "2017"
    assert profile.testing_method == "PRIOR"
    assert profile.acp_failed is True
    assert profile.adp_failed is False
    assert profile.top_heavy is False
    by_id = {d.rule_id: d for d in evaluate(profile)}
    assert by_id["B"].action == "keep"
    assert by_id["C"].action == "remove"
    assert by_id["E"].action == "keep"
    assert by_id["F"].action == "remove"


def test_assemble_split_current_fail_named_file(tmp_path, monkeypatch):
    folder = FIXTURES / "assemble-current-fail"
    files = sorted(folder.glob("*.pdf"))
    if len(files) < 2:
        pytest.skip("split assemble fixtures not generated")
    import services.save_service as save_service

    monkeypatch.setattr(save_service, "OUTPUT_DIR", tmp_path)
    uploads = [(path.name, path.read_bytes()) for path in files]
    result = process_uploads(uploads)
    assert result.filename == "222222_2024-Valuation.pdf"
    assert result.plan_profile.source_page_count == 16
