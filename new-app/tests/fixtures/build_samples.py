"""Generate labeled sample PDFs for Phase 1 extraction, rules, and assemble tests."""

from __future__ import annotations

from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent
ASSEMBLE_DIR = ROOT / "assemble-current-fail"

SECTIONS = [
    "Cover Letter",
    "Compliance Summary",
    "Action Required",
    "Variance",
    "Year End Recap",
    "Important Information",
    "Compliance Reports",
    "Contribution Analysis",
    "Future HCE",
    "ADP/ACP",
    "402(g)",
    "410(b)",
    "401(a)(4)",
    "415 Limit",
    "Top Heavy",
    "Census",
]


def _page(doc: fitz.Document, title: str, lines: list[str]) -> None:
    page = doc.new_page()
    text = title + "\n\n" + "\n".join(lines)
    page.insert_textbox(fitz.Rect(54, 54, 558, 738), text, fontsize=11, fontname="helv")


def _cover(plan: dict[str, str]) -> list[str]:
    return [
        "Mutual of America",
        f"Plan Number: {plan['number']}",
        f"Plan Name: {plan['name']}",
        f"Company Name: {plan['company']}",
        f"Address: {plan['address']}",
        f"Plan Type: {plan['plan_type']}",
        f"Plan Year: {plan['year_start']} - {plan['year_end']}",
    ]


def _pages_for(plan: dict[str, str], tests: dict[str, str]) -> list[tuple[str, list[str]]]:
    return [
        ("Cover Letter", _cover(plan)),
        (
            "Compliance Summary",
            [
                "Test Summary",
                f"Testing Method: {tests['method']}",
                f"{tests['method']} METHOD",
                f"Top Heavy Percent: {tests['top_heavy_percent']}",
                f"ADP Test: {tests['adp']}",
                f"ACP Test: {tests['acp']}",
                f"402(g) Test: {tests['g402']}",
                f"415 Test: {tests['s415']}",
                tests["returns"],
                tests["variance"],
                tests["timing"],
            ],
        ),
        (
            "Action Required",
            [
                tests["action_note"],
                tests["returns"],
                tests["timing"],
            ],
        ),
        ("Variance", [tests["variance"], "Year-end contribution variance detail."]),
        ("Year End Recap", ["Plan year recap for reviewer checklist."]),
        ("Important Information", ["Notices and sample letter placeholders."]),
        ("Compliance Reports", ["Index of compliance reports included in this package."]),
        (
            "Contribution Analysis",
            [
                f"ADP QNEC: ${tests['adp_qnec']}",
                f"ACP QNEC: ${tests['acp_qnec']}",
                f"Deferral Refund: ${tests['deferral_refund']}",
                f"Match Refund: ${tests['match_refund']}",
            ],
        ),
        ("Future HCE", ["Future highly compensated employee projection."]),
        (
            "ADP/ACP",
            [
                f"Testing Method: {tests['method']}",
                f"ADP Test: {tests['adp']}",
                f"ACP Test: {tests['acp']}",
                f"ADP QNEC: ${tests['adp_qnec']}",
                f"ACP QNEC: ${tests['acp_qnec']}",
            ],
        ),
        ("402(g)", [f"402(g) Test: {tests['g402']}", f"Deferral Refund: ${tests['deferral_refund']}"]),
        ("410(b)", ["410(b) coverage test results."]),
        ("401(a)(4)", ["401(a)(4) Test results."]),
        ("415 Limit", [f"415 Test: {tests['s415']}"]),
        (
            "Top Heavy",
            [
                f"Top Heavy Percent: {tests['top_heavy_percent']}",
                f"Match Refund: ${tests['match_refund']}",
            ],
        ),
        ("Census", ["Participant census extract for the plan year."]),
    ]


def _write_combined(path: Path, pages: list[tuple[str, list[str]]]) -> None:
    doc = fitz.open()
    for title, lines in pages:
        _page(doc, title, lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()


def _write_split(folder: Path, pages: list[tuple[str, list[str]]]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for index, (title, lines) in enumerate(pages, start=1):
        doc = fitz.open()
        _page(doc, title, lines)
        slug = title.lower().replace("/", "-").replace("(", "").replace(")", "").replace(" ", "-")
        doc.save(folder / f"{index:02d}_{slug}.pdf")
        doc.close()


def main() -> None:
    pass_plan = {
        "number": "111111",
        "name": "ABC Pass 401(k) Plan",
        "company": "ABC Pass Company",
        "address": "100 Main Street, New York, NY 10001",
        "plan_type": "401k",
        "year_start": "01/01/2024",
        "year_end": "12/31/2024",
    }
    pass_tests = {
        "method": "CURRENT",
        "top_heavy_percent": "42.10",
        "adp": "Pass",
        "acp": "Pass",
        "g402": "Pass",
        "s415": "Pass",
        "returns": "No Returns Required",
        "variance": "No Variance Report",
        "timing": "Correction Within 12 Months",
        "action_note": "No action required items.",
        "adp_qnec": "0.00",
        "acp_qnec": "0.00",
        "deferral_refund": "0.00",
        "match_refund": "0.00",
    }

    current_fail_plan = {
        "number": "222222",
        "name": "ABC Company 401(k)",
        "company": "ABC Company",
        "address": "200 Park Avenue, New York, NY 10166",
        "plan_type": "401k",
        "year_start": "01/01/2024",
        "year_end": "12/31/2024",
    }
    current_fail_tests = {
        "method": "CURRENT",
        "top_heavy_percent": "62.45",
        "adp": "Fail",
        "acp": "Pass",
        "g402": "Fail",
        "s415": "Fail",
        "returns": "Returns Required",
        "variance": "Variance Report",
        "timing": "After 12 Months",
        "action_note": "Action required: ADP, 402(g), 415, top heavy, and returns.",
        "adp_qnec": "1,250.00",
        "acp_qnec": "300.00",
        "deferral_refund": "450.00",
        "match_refund": "120.00",
    }

    prior_plan = {
        "number": "333333",
        "name": "Delta Manufacturing 401(k)",
        "company": "Delta Manufacturing Inc",
        "address": "50 River Road, Newark, NJ 07102",
        "plan_type": "401k",
        "year_start": "10/01/2017",
        "year_end": "09/30/2018",
    }
    prior_tests = {
        "method": "PRIOR",
        "top_heavy_percent": "45.00",
        "adp": "Pass",
        "acp": "Fail",
        "g402": "Pass",
        "s415": "Pass",
        "returns": "Returns Required",
        "variance": "No Variance Report",
        "timing": "After 12 Months",
        "action_note": "Action required: ACP failed and returns required.",
        "adp_qnec": "0.00",
        "acp_qnec": "875.50",
        "deferral_refund": "0.00",
        "match_refund": "200.00",
    }

    pass_pages = _pages_for(pass_plan, pass_tests)
    current_pages = _pages_for(current_fail_plan, current_fail_tests)
    prior_pages = _pages_for(prior_plan, prior_tests)

    _write_combined(ROOT / "01_pass_no_action.pdf", pass_pages)
    _write_combined(ROOT / "02_current_fail_qnec.pdf", current_pages)
    _write_combined(ROOT / "03_prior_fail_offcalendar.pdf", prior_pages)
    _write_split(ASSEMBLE_DIR, current_pages)
    print(f"Wrote sample PDFs under {ROOT}")


if __name__ == "__main__":
    main()
