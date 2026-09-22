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


def test_list_folder_files_returns_names():
    from services.folder_loader import list_folder_files

    folder = FIXTURES / "assemble-current-fail"
    listed = list_folder_files(str(folder))
    names = [item["name"] for item in listed["files"]]
    assert len(names) == 16
    assert names[0].lower().startswith("01_cover")
    assert names[-1].lower().startswith("16_census")


def test_expand_multipage_pdf_as_separate_rows(tmp_path):
    import fitz

    from services.folder_loader import list_folder_files
    from services.pdf_pages import expand_uploads_by_page, pdf_page_count

    folder = tmp_path / "pkg"
    folder.mkdir()
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Cover page 1", fontsize=12)
    doc.new_page().insert_text((72, 72), "Cover page 2", fontsize=12)
    pdf = folder / "Cover Letter.pdf"
    doc.save(pdf)
    data = pdf.read_bytes()
    doc.close()
    assert pdf_page_count(data) == 2
    listed = list_folder_files(str(folder))
    assert listed["files"][0]["pages"] == 2
    assert listed["files"][0]["split"] is True
    assert any("each page is listed" in w for w in listed["warnings"])
    ordered, warnings = expand_uploads_by_page(
        [("Cover Letter.pdf", data)],
        ["Cover Letter.pdf", "Cover Letter.pdf"],
        [2, 1],
    )
    assert warnings == []
    assert ordered[0][0] == "Cover Letter_p02.pdf"
    assert ordered[1][0] == "Cover Letter_p01.pdf"
    page1 = fitz.open(stream=ordered[1][1], filetype="pdf")
    page2 = fitz.open(stream=ordered[0][1], filetype="pdf")
    try:
        assert page1.page_count == 1
        assert "page 1" in (page1[0].get_text("text") or "")
        assert "page 2" in (page2[0].get_text("text") or "")
    finally:
        page1.close()
        page2.close()


def test_non_cover_multipage_pdf_is_not_split(tmp_path):
    import fitz

    from services.file_order import should_split_pages
    from services.folder_loader import list_folder_files

    folder = tmp_path / "pkg"
    folder.mkdir()
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    pdf = folder / "16_census.pdf"
    doc.save(pdf)
    doc.close()
    listed = list_folder_files(str(folder))
    assert listed["files"][0]["pages"] == 2
    assert listed["files"][0]["split"] is False
    assert should_split_pages("16_census.pdf", 2) is False
    assert should_split_pages("Cover Page.pdf", 2) is True
    assert not any("each page is listed" in w for w in listed["warnings"])


def test_apply_file_order_keeps_ui_sequence():
    from services.folder_loader import apply_file_order

    uploads = [
        ("01_cover-letter.pdf", b"a"),
        ("10_adp-acp.pdf", b"b"),
        ("16_census.pdf", b"c"),
    ]
    ordered, warnings = apply_file_order(uploads, ["16_census.pdf", "01_cover-letter.pdf"])
    assert [name for name, _ in ordered] == ["16_census.pdf", "01_cover-letter.pdf"]
    assert warnings == []


def test_process_folder_uses_file_order(tmp_path, monkeypatch):
    import services.save_service as save_service
    from services.folder_loader import apply_file_order

    monkeypatch.setattr(save_service, "OUTPUT_DIR", tmp_path)
    folder = FIXTURES / "assemble-current-fail"
    uploads, warnings = load_pdfs_from_folder(str(folder))
    names = [name for name, _ in uploads]
    reversed_names = list(reversed(names))
    ordered, _ = apply_file_order(uploads, reversed_names)
    result = process_uploads(ordered, auto_order=False, extra_warnings=warnings)
    assert result.source_files[0] == reversed_names[0]


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
