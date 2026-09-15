from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from config.settings import OUTPUT_DIR
from models.job import JobResult
from services.folder_loader import load_pdfs_from_folder
from services.orchestrator import process_uploads

router = APIRouter()
JOBS: dict[str, JobResult] = {}


def _saved_pdf(job_id: str) -> tuple[Path, str] | None:
    """Find the assembled PDF in memory or on disk (survives a server restart)."""
    if not job_id.isalnum() or len(job_id) > 40:
        return None
    job = JOBS.get(job_id)
    if job:
        path = Path(job.pdf_path)
        if path.is_file():
            return path, job.filename
    job_dir = OUTPUT_DIR / job_id
    if not job_dir.is_dir():
        return None
    pdfs = sorted(job_dir.glob("*.pdf"))
    if not pdfs:
        return None
    return pdfs[0], pdfs[0].name


@router.post("/jobs", response_model=JobResult)
async def create_job(
    request: Request,
    files: list[UploadFile] | None = File(default=None),
    source_path: str = Form(default=""),
    auto_order: bool = Form(default=True),
) -> JobResult:
    uploads: list[tuple[str, bytes]] = []
    warnings: list[str] = []
    folder = (source_path or "").strip()
    if folder:
        folder_uploads, folder_warnings = load_pdfs_from_folder(folder)
        uploads.extend(folder_uploads)
        warnings.extend(folder_warnings)

    for upload in files or []:
        name = upload.filename or ""
        if not name or name.startswith("~$"):
            continue
        if not name.lower().endswith((".pdf", ".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail=f"{name} must be a PDF or Excel file")
        data = await upload.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"{name} is empty")
        uploads.append((name, data))

    if not uploads:
        raise HTTPException(
            status_code=400,
            detail="Upload PDF files or enter a Valuation Package folder path",
        )

    try:
        result = process_uploads(
            uploads,
            auto_order=auto_order,
            extra_warnings=warnings,
            source_folder=folder or None,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not process PDFs: {exc}") from exc
    base = str(request.base_url).rstrip("/")
    result.download_url = f"{base}/api/jobs/{result.job_id}/pdf"
    result.preview_url = f"{base}/api/jobs/{result.job_id}/preview"
    JOBS[result.job_id] = result
    return result


@router.get("/jobs/{job_id}", response_model=JobResult)
def get_job(job_id: str) -> JobResult:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/pdf")
def download_job_pdf(job_id: str) -> FileResponse:
    found = _saved_pdf(job_id)
    if not found:
        raise HTTPException(
            status_code=404,
            detail="Assembled PDF not found. Restart python main.py, then click Process package again. Do not reuse an old preview URL.",
        )
    path, filename = found
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="attachment",
    )


@router.get("/jobs/{job_id}/preview")
def preview_job_pdf(job_id: str) -> FileResponse:
    found = _saved_pdf(job_id)
    if not found:
        raise HTTPException(
            status_code=404,
            detail="Assembled PDF not found. Restart python main.py, then click Process package again. Do not reuse an old preview URL.",
        )
    path, filename = found
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/jobs/{job_id}/email")
def download_job_email(job_id: str) -> FileResponse:
    job = JOBS.get(job_id)
    path = Path(job.email_path) if job and job.email_path else None
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="Outlook draft not found. Process the package again.")
    return FileResponse(
        path,
        media_type="message/rfc822",
        filename=path.name,
        content_disposition_type="attachment",
    )


@router.get("/jobs/{job_id}/log")
def download_assembly_log(job_id: str) -> FileResponse:
    job = JOBS.get(job_id)
    path = Path(job.log_path) if job and job.log_path else OUTPUT_DIR / "ValAssemblyLog.xlsx"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Val Assembly Log not found. Process a package first.")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
        content_disposition_type="attachment",
    )
