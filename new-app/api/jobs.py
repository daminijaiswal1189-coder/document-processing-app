from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from models.job import JobResult
from services.orchestrator import process_uploads

router = APIRouter()
JOBS: dict[str, JobResult] = {}


@router.post("/jobs", response_model=JobResult)
async def create_job(
    request: Request,
    files: list[UploadFile] = File(..., alias="files"),
) -> JobResult:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one PDF")
    uploads: list[tuple[str, bytes]] = []
    for upload in files:
        name = upload.filename or "document.pdf"
        if not name.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{name} is not a PDF")
        data = await upload.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"{name} is empty")
        uploads.append((name, data))
    try:
        result = process_uploads(uploads)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not process PDFs: {exc}") from exc
    result.download_url = str(request.base_url).rstrip("/") + f"/api/jobs/{result.job_id}/pdf"
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
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    path = Path(job.pdf_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Saved PDF is missing")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=job.filename,
        content_disposition_type="attachment",
    )
