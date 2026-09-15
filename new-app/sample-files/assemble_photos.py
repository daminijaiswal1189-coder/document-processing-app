"""Convert sample-files photos into SOP-named PDFs and assemble a valuation package."""

from __future__ import annotations

from pathlib import Path

import fitz

from services.orchestrator import process_uploads

ROOT = Path(__file__).resolve().parent
PREVIEW = ROOT / "_preview"
PDF_DIR = ROOT / "pdf"

PAGES = [
    ("20260909_195051.jpg", "01_cover-letter.pdf"),
    ("20260909_195331.jpg", "02_action-required.pdf"),
    ("20260909_195340.jpg", "03_action-required-continued.pdf"),
    ("20260909_195348.jpg", "04_action-required-after-12-months.pdf"),
    ("20260909_195401.jpg", "05_failed-test-notice-current-after-12.pdf"),
    ("20260909_195410.jpg", "06_failed-test-notice-prior-after-12.pdf"),
    ("20260909_195421.jpg", "07_failed-test-notice-current.pdf"),
    ("20260909_195452.jpg", "08_415-limit.pdf"),
    ("20260909_195504.jpg", "09_sample-letter-acp.pdf"),
    ("20260909_195520.jpg", "10_sample-letter-402g.pdf"),
    ("20260909_195529.jpg", "11_sample-letter-415.pdf"),
    ("20260909_195540.jpg", "12_year-end-recap.pdf"),
    ("20260909_195558.jpg", "13_compliance-reports.pdf"),
    ("20260909_195605.jpg", "14_410b-414s-brf.pdf"),
    ("20260909_195611.jpg", "15_administrative-reports.pdf"),
]


def image_to_pdf(image_path: Path, pdf_path: Path) -> None:
    img = fitz.open(image_path)
    try:
        page_img = img[0]
        rect = page_img.rect
        doc = fitz.open()
        page = doc.new_page(width=rect.width, height=rect.height)
        page.insert_image(page.rect, filename=str(image_path))
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(pdf_path, deflate=True)
        doc.close()
    finally:
        img.close()


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    uploads: list[tuple[str, bytes]] = []
    for image_name, pdf_name in PAGES:
        image_path = PREVIEW / image_name
        if not image_path.is_file():
            raise SystemExit(f"Missing preview image: {image_path}")
        pdf_path = PDF_DIR / pdf_name
        image_to_pdf(image_path, pdf_path)
        uploads.append((pdf_name, pdf_path.read_bytes()))
        print("wrote", pdf_path.name)

    result = process_uploads(uploads, auto_order=True)
    print("assembled", result.filename)
    print("path", result.pdf_path)
    print("pages", result.plan_profile.source_page_count)
    print("plan_number", result.plan_profile.plan_number)
    print("warnings:")
    for warning in result.warnings:
        print(" -", warning)


if __name__ == "__main__":
    main()
