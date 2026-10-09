from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

import fitz
from fastapi import HTTPException

from models.job import JobResult
from models.review import ValidationItem
from models.job import HighlightMark
from services import (
    assembly_log,
    assembly_stops,
    bookmark_service,
    change_marks,
    file_order,
    outlook_service,
    pdf_assembler,
    pdf_extractor,
    package_polish,
    pdf_modifier,
    plan_profile_service,
    review_service,
    rules_engine,
    save_service,
    source_profile,
    source_rewrite,
    ssn_scan,
)


def process_uploads(
    uploads: list[tuple[str, bytes]],
    *,
    auto_order: bool = True,
    extra_warnings: list[str] | None = None,
    source_folder: str | None = None,
    rewrite_sources: bool = False,
) -> JobResult:
    """
    TEST23 pipeline:
    assemble valuation PDFs → overlay Excel + summary pass/fail → keep/remove
    Action Required paragraphs → bookmarks → save named PDF.
    """
    job_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    warnings = list(extra_warnings or [])
    highlights: list[dict] = []
    pdfs, excels = _split_uploads(uploads)
    valuation, summary_texts = _split_summaries(pdfs)
    valuation, brf_notes = package_polish.exclude_brf_uploads(valuation)
    warnings.extend(brf_notes)
    if not valuation:
        raise HTTPException(
            status_code=400,
            detail="BRF reports are not included, and no other PDF was uploaded.",
        )
    ordered = file_order.order_uploads(valuation) if auto_order else list(valuation)
    doc = pdf_assembler.merge_pdfs(ordered)
    email_path = ""
    log_file = ""
    saved_copy = ""
    subject = ""
    try:
        warnings.extend(package_polish.reorder_inner_pages(doc))
        profile = pdf_extractor.extract_plan_profile(doc)
        pdf_plan_name = profile.plan_name
        overlays: list[dict] = []
        excel_plan_name: str | None = None
        for name, data in excels:
            parsed = source_profile.parse_excel(data)
            if parsed.get("plan_name"):
                excel_plan_name = str(parsed["plan_name"])
            overlays.append(parsed)
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
        if package_polish.has_variance_client_copy([name for name, _data in ordered], doc):
            profile.contributions_required = True
        profile = plan_profile_service.finalize_profile(profile)
        review = review_service.validate(profile, doc=doc)
        decisions = rules_engine.evaluate(profile)
        removed = pdf_modifier.apply_decisions(doc, decisions)
        recap_removed = pdf_modifier.apply_recap_bullets(doc, decisions)
        filled = pdf_modifier.fill_qnec_placeholders(doc, profile, highlights)
        warnings.extend(package_polish.remove_disallowed_wording(doc))
        warnings.extend(package_polish.drop_brf_pages(doc))
        if rewrite_sources:
            warnings.extend(source_rewrite.apply_source_rewrites(doc, profile, highlights))
        else:
            warnings.extend(source_rewrite.apply_cover_date(doc, highlights))
        profile.detected_sections = pdf_extractor.detect_sections(doc)
        review.items.extend(package_polish.package_checks(doc, profile))
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
        reasons = assembly_stops.stop_reasons(
            doc,
            profile,
            source_files=[name for name, _data in ordered],
            excel_plan_name=excel_plan_name,
            pdf_plan_name=pdf_plan_name,
        )
        if reasons:
            raise HTTPException(status_code=400, detail="Assembly stopped.\n" + "\n".join(reasons))
        dest = save_service.testing_folder_from_source(source_folder)
        path = save_service.save_package(doc, job_id, profile, dest_dir=dest)
        change_marks.save_marks(path, highlights)
        if dest:
            saved_copy = str(dest / path.name)
            warnings.append(f"Also saved to {saved_copy}")
        eml = outlook_service.write_draft(path.parent / f"{path.stem}.eml", profile, path.name)
        email_path = str(eml)
        elapsed_seconds = time.perf_counter() - started
        log_file = str(
            assembly_log.append_row(
                save_service.OUTPUT_DIR / "ValAssemblyLog.xlsx",
                profile,
                path.name,
                job_id,
                doc=doc,
                finished_at=datetime.now(),
                elapsed_seconds=elapsed_seconds,
            )
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
        highlights=[HighlightMark(**item) for item in highlights],
        source_files=[name for name, _data in ordered] + [name for name, _data in excels] + [name for name, _text in summary_texts],
        download_url=f"/api/jobs/{job_id}/pdf",
        email_subject=subject,
        email_path=email_path,
        log_path=log_file,
        saved_copy_path=saved_copy,
        elapsed_seconds=round(elapsed_seconds, 1),
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
