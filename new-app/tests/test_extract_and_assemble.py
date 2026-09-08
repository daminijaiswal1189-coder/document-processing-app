import fitz

from services.orchestrator import process_uploads
from services.pdf_extractor import extract_plan_profile


def _cover_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "\n".join(
            [
                "Plan Number: 123456",
                "Plan Name: ABC Company 401(k)",
                "Company Name: ABC Company",
                "Address: New York",
                "Plan Year: 01/01/2024 - 12/31/2024",
                "Testing Method: CURRENT",
                "Top Heavy Percent: 62.45",
                "ADP Test: Fail",
                "Returns Required",
                "Cover Letter",
                "Census",
            ]
        ),
        fontsize=11,
    )
    data = doc.tobytes()
    doc.close()
    return data


def test_extract_cover_fields():
    doc = fitz.open(stream=_cover_pdf(), filetype="pdf")
    try:
        profile = extract_plan_profile(doc)
        assert profile.plan_number == "123456"
        assert profile.plan_name == "ABC Company 401(k)"
        assert profile.beginning_plan_year == "2024"
        assert profile.testing_method == "CURRENT"
        assert profile.top_heavy is True
    finally:
        doc.close()


def test_assemble_and_save_named_file(tmp_path, monkeypatch):
    import services.save_service as save_service

    monkeypatch.setattr(save_service, "OUTPUT_DIR", tmp_path)
    result = process_uploads([("cover.pdf", _cover_pdf())])
    assert result.filename == "123456_2024-Valuation.pdf"
    assert (tmp_path / result.job_id / result.filename).is_file()
