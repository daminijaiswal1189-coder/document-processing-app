from __future__ import annotations

import uuid
from datetime import datetime, timezone

from models.job import JobResult
from services import pdf_assembler, pdf_extractor, plan_profile_service, review_service, rules_engine, save_service


def process_uploads(uploads: list[tuple[str, bytes]]) -> JobResult:
    """
    Phase 1 pipeline:
    assemble → extract → plan profile → rule preview (JSON) → save named PDF.
    PDF page removal and bookmarks are Phase 4 and are not applied here.
    """
    job_id = uuid.uuid4().hex[:12]
    doc = pdf_assembler.merge_pdfs(uploads)
    try:
        profile = pdf_extractor.extract_plan_profile(doc)
        profile = plan_profile_service.finalize_profile(profile)
        review = review_service.validate(profile)
        decisions = rules_engine.evaluate(profile)
        path = save_service.save_package(doc, job_id, profile)
    finally:
        doc.close()

    warnings = list(profile.extraction_warnings)
    if any(d.skipped for d in decisions):
        warnings.append("Some rules were skipped because extraction did not fill required fields.")

    filename = path.name
    return JobResult(
        job_id=job_id,
        filename=filename,
        pdf_path=str(path),
        created_at=datetime.now(timezone.utc),
        plan_profile=profile,
        review=review,
        rule_decisions=decisions,
        warnings=warnings,
        source_files=[name for name, _data in uploads],
        download_url=f"/api/jobs/{job_id}/pdf",
    )
