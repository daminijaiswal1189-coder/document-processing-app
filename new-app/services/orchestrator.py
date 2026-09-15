from __future__ import annotations

import uuid
from datetime import datetime, timezone

import fitz

from models.job import JobResult
from models.review import ValidationItem
from services import (
    assembly_log,
    bookmark_service,
    file_order,
    outlook_service,
    pdf_assembler,
    pdf_extractor,
    pdf_modifier,
    plan_profile_service,
    review_service,
    rules_engine,
    save_service,
    source_profile,
    ssn_scan,
)


def process_uploads(
    uploads: list[tuple[str, bytes]],
    *,
    auto_order: bool = True,
    extra_warnings: list[str] | None = None,
    source_folder: str | None = None,
) -> JobResult:
    """
    TEST23 pipeline:
    assemble valuation PDFs → overlay Excel + summary pass/fail → keep/remove
    Action Required paragraphs → bookmarks → save named PDF.
    """
    job_id = uuid.uuid4().hex[:12]
    warnings = list(extra_warnings or [])
    pdfs, excels = _split_uploads(uploads)
    valuation, summary_texts = _split_summaries(pdfs)
    ordered = file_order.order_uploads(valuation) if auto_order else list(valuation)
    doc = pdf_assembler.merge_pdfs(ordered)
    email_path = ""
    log_file = ""
    saved_copy = ""
    subject = ""
    try:
        profile = pdf_extractor.extract_plan_profile(doc)
        overlays: list[dict] = []
        for name, data in excels:
            overlays.append(source_profile.parse_excel(data))
            warnings.append(f"Read Val Assembly Excel: {name}")
        for name, text in summary_texts:
            overlays.append(source_profile.parse_summary_text(text))
            warnings.append(f"Read Compliance Testing Summary: {name}")
        if not summary_texts:
            merged_text = "\n".join((page.get_text("text") or "") for page in doc)
            parsed = source_profile.parse_summary_text(merged_text)
            if parsed.get("adp_failed") is not None or parsed.get("fail_402g") is not None:
                overlays.append(parsed)
        profile = source_profile.merge_overlays(profile, overlays, warnings)
        profile = plan_profile_service.finalize_profile(profile)
        review = review_service.validate(profile, doc=doc)
        decisions = rules_engine.evaluate(profile)
        removed = pdf_modifier.apply_decisions(doc, decisions)
        recap_removed = pdf_modifier.apply_recap_bullets(doc, decisions)
        filled = pdf_modifier.fill_qnec_placeholders(doc, profile)
        bookmark_count = bookmark_service.add_bookmarks(
            doc,
            profile,
            source_files=[name for name, _data in ordered],
        )
        ssn_pages = ssn_scan.scan_ssns(doc)
        review.ssn_found = bool(ssn_pages)
        review.ssn_pages = ssn_pages
        review.items.append(
            ValidationItem(
                code="ssn_scan",
                label="SSN scan",
                passed=not ssn_pages,
                detail="No SSNs found"
                if not ssn_pages
                else "SSN found on page(s) " + ", ".join(str(page) for page in ssn_pages),
            )
        )
        dest = save_service.testing_folder_from_source(source_folder)
        path = save_service.save_package(doc, job_id, profile, dest_dir=dest)
        if dest:
            saved_copy = str(dest / path.name)
            warnings.append(f"Also saved to {saved_copy}")
        eml = outlook_service.write_draft(path.parent / f"{path.stem}.eml", profile, path.name)
        email_path = str(eml)
        log_file = str(
            assembly_log.append_row(save_service.OUTPUT_DIR / "ValAssemblyLog.xlsx", profile, path.name, job_id)
        )
        subject = outlook_service.email_subject(profile)
    finally:
        doc.close()

    warnings.extend(profile.extraction_warnings)
    if auto_order:
        warnings.append("Files were ordered using the TEST23 combine sequence.")
    if removed:
        warnings.append("Removed Action Required paragraph(s): " + ", ".join(removed))
    if recap_removed:
        warnings.append("Removed Year End Recap bullet(s): " + ", ".join(recap_removed))
    if filled:
        warnings.append("Filled Excess Return Notice QNEC amounts: " + ", ".join(filled))
    if subject:
        warnings.append("Outlook draft subject: " + subject)
    kept = [item.rule_id for item in decisions if item.action == "keep"]
    if kept:
        warnings.append("Retained Action Required paragraph(s): " + ", ".join(kept))
    if bookmark_count:
        warnings.append(f"Added {bookmark_count} SOP bookmark(s).")
    if any(d.skipped for d in decisions):
        warnings.append("Some rules were skipped because extraction did not fill required fields.")

    return JobResult(
        job_id=job_id,
        filename=path.name,
        pdf_path=str(path),
        created_at=datetime.now(timezone.utc),
        plan_profile=profile,
        review=review,
        rule_decisions=decisions,
        warnings=warnings,
        source_files=[name for name, _data in ordered] + [name for name, _data in excels] + [name for name, _text in summary_texts],
        download_url=f"/api/jobs/{job_id}/pdf",
        email_subject=subject,
        email_path=email_path,
        log_path=log_file,
        saved_copy_path=saved_copy,
    )


def _split_uploads(uploads: list[tuple[str, bytes]]) -> tuple[list[tuple[str, bytes]], list[tuple[str, bytes]]]:
    pdfs: list[tuple[str, bytes]] = []
    excels: list[tuple[str, bytes]] = []
    for name, data in uploads:
        lower = name.lower()
        if lower.endswith((".xlsx", ".xls")):
            excels.append((name, data))
        elif lower.endswith(".pdf"):
            pdfs.append((name, data))
    return pdfs, excels


def _split_summaries(pdfs: list[tuple[str, bytes]]) -> tuple[list[tuple[str, bytes]], list[tuple[str, str]]]:
    valuation: list[tuple[str, bytes]] = []
    summaries: list[tuple[str, str]] = []
    for name, data in pdfs:
        text = _pdf_text(data)
        if "compliance testing summary of results" in text.lower():
            summaries.append((name, text))
        else:
            valuation.append((name, data))
    return valuation, summaries


def _pdf_text(data: bytes) -> str:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        return "\n".join((page.get_text("text") or "") for page in doc)
    finally:
        doc.close()
