from models.plan_profile import PlanProfile
from services.plan_profile_service import finalize_profile
from services.rules_engine import evaluate
from services.save_service import valuation_filename


def test_beginning_year_is_start_year_not_end_year():
    profile = PlanProfile(plan_number="123456", plan_year_start="10/01/2017", plan_year_end="09/30/2018")
    finalize_profile(profile)
    assert profile.beginning_plan_year == "2017"
    assert valuation_filename(profile) == "123456_2017-Valuation.pdf"


def test_calendar_year_filename():
    profile = PlanProfile(plan_number="123456", plan_year_start="01/01/2024", plan_year_end="12/31/2024")
    finalize_profile(profile)
    assert valuation_filename(profile) == "123456_2024-Valuation.pdf"


def test_unknown_filename_when_extract_fails():
    profile = PlanProfile()
    finalize_profile(profile)
    assert valuation_filename(profile) == "UNKNOWN_UNKNOWN-Valuation.pdf"


def test_rule_f_keeps_top_heavy_at_60():
    profile = PlanProfile(top_heavy_percent=62.45, top_heavy=True)
    by_id = {d.rule_id: d for d in evaluate(profile)}
    assert by_id["F"].action == "keep"


def test_rule_f_removes_when_not_top_heavy():
    profile = PlanProfile(top_heavy_percent=40.0, top_heavy=False)
    by_id = {d.rule_id: d for d in evaluate(profile)}
    assert by_id["F"].action == "remove"


def test_rule_a_requires_failure_and_returns():
    profile = PlanProfile(testing_failed=True, returns_required=True)
    by_id = {d.rule_id: d for d in evaluate(profile)}
    assert by_id["A"].action == "keep"

    profile = PlanProfile(testing_failed=True, returns_required=False)
    by_id = {d.rule_id: d for d in evaluate(profile)}
    assert by_id["A"].action == "remove"


def test_total_qnec_sum():
    profile = PlanProfile(adp_qnec=100.0, acp_qnec=25.5)
    finalize_profile(profile)
    assert profile.total_qnec == 125.5
