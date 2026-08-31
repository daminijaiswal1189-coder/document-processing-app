"""
Standalone FastAPI for PDF read / extract / remove / update.

Client-machine utility. Does not import or depend on the POC backend.

Run:
  pip install fastapi uvicorn python-multipart pymupdf
  uvicorn pdf-process:app --host 127.0.0.1 --port 8001 --reload

Docs:
  http://127.0.0.1:8001/docs
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

HERE = Path(__file__).resolve().parent

app = FastAPI(
    title="PDF Process API",
    version="1.0.0",
    description="Read, extract, remove, and update PDF content.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_SUFFIX = ".pdf"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _ensure_pdf(upload: UploadFile) -> None:
    name = (upload.filename or "").lower()
    if not name.endswith(ALLOWED_SUFFIX):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted")


def _read_upload(upload: UploadFile) -> bytes:
    _ensure_pdf(upload)
    data = upload.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF larger than 50 MB")
    return data


def _open_pdf(data: bytes) -> fitz.Document:
    try:
        return fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid PDF: {exc}") from exc


def _pdf_response(doc: fitz.Document, filename: str) -> StreamingResponse:
    buffer = io.BytesIO()
    doc.save(buffer, garbage=4, deflate=True)
    doc.close()
    buffer.seek(0)
    safe_name = Path(filename).stem + "-updated.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


def _extract_pages(doc: fitz.Document) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for index, page in enumerate(doc):
        pages.append(
            {
                "page": index + 1,
                "width": round(page.rect.width, 2),
                "height": round(page.rect.height, 2),
                "text": page.get_text("text") or "",
                "word_count": len((page.get_text("text") or "").split()),
            }
        )
    return pages


def _metadata(doc: fitz.Document) -> dict[str, Any]:
    meta = doc.metadata or {}
    return {
        "title": meta.get("title") or "",
        "author": meta.get("author") or "",
        "subject": meta.get("subject") or "",
        "keywords": meta.get("keywords") or "",
        "creator": meta.get("creator") or "",
        "producer": meta.get("producer") or "",
        "creationDate": meta.get("creationDate") or "",
        "modDate": meta.get("modDate") or "",
        "page_count": doc.page_count,
        "is_encrypted": bool(doc.is_encrypted),
    }


@app.get("/")
def ui() -> FileResponse:
    html = HERE / "index.html"
    if not html.is_file():
        raise HTTPException(status_code=404, detail="index.html not found next to pdf-process.py")
    return FileResponse(html, media_type="text/html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/pdf/read")
async def read_pdf(file: UploadFile = File(...)) -> JSONResponse:
    """Read PDF: metadata + per-page text."""
    data = _read_upload(file)
    doc = _open_pdf(data)
    try:
        payload = {
            "filename": file.filename,
            "metadata": _metadata(doc),
            "pages": _extract_pages(doc),
        }
    finally:
        doc.close()
    return JSONResponse(payload)


@app.post("/pdf/extract")
async def extract_pdf(
    file: UploadFile = File(...),
    include_blocks: bool = Form(False),
) -> JSONResponse:
    """Extract text (and optional text blocks with coordinates)."""
    data = _read_upload(file)
    doc = _open_pdf(data)
    try:
        pages: list[dict[str, Any]] = []
        full_text_parts: list[str] = []
        for index, page in enumerate(doc):
            text = page.get_text("text") or ""
            full_text_parts.append(text)
            item: dict[str, Any] = {"page": index + 1, "text": text}
            if include_blocks:
                blocks = []
                for block in page.get_text("blocks"):
                    x0, y0, x1, y1, block_text, *_rest = block
                    if str(block_text).strip():
                        blocks.append(
                            {
                                "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                                "text": str(block_text),
                            }
                        )
                item["blocks"] = blocks
            pages.append(item)
        payload = {
            "filename": file.filename,
            "page_count": doc.page_count,
            "full_text": "\n".join(full_text_parts),
            "pages": pages,
        }
    finally:
        doc.close()
    return JSONResponse(payload)


@app.post("/pdf/remove-text")
async def remove_text(
    file: UploadFile = File(...),
    texts: str = Form(..., description="Comma-separated phrases to redact"),
    fill: str = Form("white"),
) -> StreamingResponse:
    """Remove matching text by redaction (covers the original glyphs)."""
    data = _read_upload(file)
    phrases = [part.strip() for part in texts.split(",") if part.strip()]
    if not phrases:
        raise HTTPException(status_code=400, detail="Provide at least one phrase in texts")

    fill_rgb = (1, 1, 1) if fill.lower() == "white" else (0, 0, 0)
    doc = _open_pdf(data)
    hits = 0
    try:
        for page in doc:
            for phrase in phrases:
                for rect in page.search_for(phrase):
                    page.add_redact_annot(rect, fill=fill_rgb)
                    hits += 1
            page.apply_redactions()
        if hits == 0:
            doc.close()
            raise HTTPException(status_code=404, detail="No matching text found to remove")
        return _pdf_response(doc, file.filename or "document.pdf")
    except HTTPException:
        raise
    except Exception:
        doc.close()
        raise


@app.post("/pdf/remove-pages")
async def remove_pages(
    file: UploadFile = File(...),
    pages: str = Form(..., description="Comma-separated 1-based page numbers, e.g. 1,3"),
) -> StreamingResponse:
    """Delete pages from the PDF."""
    data = _read_upload(file)
    try:
        numbers = sorted({int(p.strip()) for p in pages.split(",") if p.strip()})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="pages must be integers") from exc
    if not numbers:
        raise HTTPException(status_code=400, detail="Provide at least one page number")

    doc = _open_pdf(data)
    try:
        invalid = [n for n in numbers if n < 1 or n > doc.page_count]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Page numbers out of range (1-{doc.page_count}): {invalid}",
            )
        if len(numbers) >= doc.page_count:
            raise HTTPException(status_code=400, detail="Cannot delete all pages")
        # delete from the end so earlier indexes stay valid
        for page_no in reversed(numbers):
            doc.delete_page(page_no - 1)
        return _pdf_response(doc, file.filename or "document.pdf")
    except HTTPException:
        doc.close()
        raise
    except Exception:
        doc.close()
        raise


@app.post("/pdf/remove-metadata")
async def remove_metadata(file: UploadFile = File(...)) -> StreamingResponse:
    """Strip document metadata fields."""
    data = _read_upload(file)
    doc = _open_pdf(data)
    try:
        doc.set_metadata(
            {
                "title": "",
                "author": "",
                "subject": "",
                "keywords": "",
                "creator": "",
                "producer": "",
            }
        )
        return _pdf_response(doc, file.filename or "document.pdf")
    except Exception:
        doc.close()
        raise


@app.post("/pdf/update")
async def update_pdf(
    file: UploadFile = File(...),
    find: str = Form(""),
    replace: str = Form(""),
    title: str = Form(""),
    author: str = Form(""),
    subject: str = Form(""),
    keywords: str = Form(""),
) -> StreamingResponse:
    """
    Update PDF:
    - replace visible text (find -> replace) via redact + insert
    - optionally set metadata fields
    """
    data = _read_upload(file)
    find_text = find.strip()
    doc = _open_pdf(data)
    try:
        if find_text:
            replaced = 0
            for page in doc:
                matches = page.search_for(find_text)
                if not matches:
                    continue
                for rect in matches:
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                    replaced += 1
                page.apply_redactions()
                for rect in matches:
                    fontsize = max(8.0, min(14.0, rect.height * 0.8))
                    page.insert_textbox(
                        rect,
                        replace,
                        fontsize=fontsize,
                        color=(0, 0, 0),
                        align=fitz.TEXT_ALIGN_LEFT,
                    )
            if replaced == 0:
                raise HTTPException(status_code=404, detail=f"Text not found: {find_text}")

        meta_update: dict[str, str] = {}
        if title:
            meta_update["title"] = title
        if author:
            meta_update["author"] = author
        if subject:
            meta_update["subject"] = subject
        if keywords:
            meta_update["keywords"] = keywords
        if meta_update:
            current = doc.metadata or {}
            current.update(meta_update)
            doc.set_metadata(current)

        if not find_text and not meta_update:
            raise HTTPException(
                status_code=400,
                detail="Provide find/replace and/or at least one metadata field",
            )

        return _pdf_response(doc, file.filename or "document.pdf")
    except HTTPException:
        doc.close()
        raise
    except Exception:
        doc.close()
        raise


@app.post("/pdf/add-text")
async def add_text(
    file: UploadFile = File(...),
    text: str = Form(...),
    page: int = Form(1),
    x: float = Form(72),
    y: float = Form(72),
    fontsize: float = Form(11),
) -> StreamingResponse:
    """Insert text at a page coordinate (PDF points, origin top-left via insert_text)."""
    data = _read_upload(file)
    if not text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    doc = _open_pdf(data)
    try:
        if page < 1 or page > doc.page_count:
            raise HTTPException(status_code=400, detail=f"page must be 1-{doc.page_count}")
        pdf_page = doc[page - 1]
        # PyMuPDF insert_text uses top-left origin when fontsize is set this way
        pdf_page.insert_text(
            fitz.Point(x, y),
            text,
            fontsize=fontsize,
            color=(0, 0, 0),
        )
        return _pdf_response(doc, file.filename or "document.pdf")
    except HTTPException:
        doc.close()
        raise
    except Exception:
        doc.close()
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("pdf-process:app", host="127.0.0.1", port=8001, reload=False)
