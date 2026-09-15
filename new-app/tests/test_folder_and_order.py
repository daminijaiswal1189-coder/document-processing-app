from pathlib import Path

from services.file_order import order_uploads, sop_rank
from services.folder_loader import load_pdfs_from_folder
from services.orchestrator import process_uploads

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_sop_rank_cover_before_census():
    assert sop_rank("01_cover-letter.pdf") < sop_rank("16_census.pdf")
    assert sop_rank("10_adp-acp.pdf") < sop_rank("11_402g.pdf")


def test_order_uploads_follows_sop_not_filename_sort():
    uploads = [
        ("16_census.pdf", b"%PDF"),
        ("01_cover-letter.pdf", b"%PDF"),
        ("08_contribution-analysis.pdf", b"%PDF"),
    ]
    ordered = [name for name, _ in order_uploads(uploads)]
    assert ordered == ["01_cover-letter.pdf", "08_contribution-analysis.pdf", "16_census.pdf"]


def test_load_folder_and_process(tmp_path, monkeypatch):
    folder = FIXTURES / "assemble-current-fail"
    uploads, warnings = load_pdfs_from_folder(str(folder))
    assert len(uploads) == 16
    assert any("Loaded 16" in item for item in warnings)

    import services.save_service as save_service

    monkeypatch.setattr(save_service, "OUTPUT_DIR", tmp_path)
    result = process_uploads(uploads, auto_order=True, extra_warnings=warnings)
    assert result.filename == "222222_2024-Valuation.pdf"
    assert result.source_files[0].lower().startswith("01_cover")
    assert result.source_files[-1].lower().startswith("16_census")
