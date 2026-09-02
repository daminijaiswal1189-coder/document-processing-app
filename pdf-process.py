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
    expose_headers=["X-Replaced-Count", "X-Assembled-Files", "X-Assembled-Pages", "Content-Disposition"],
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


def _pdf_response(
    doc: fitz.Document,
    filename: str,
    extra_headers: dict[str, str] | None = None,
    download_name: str | None = None,
) -> StreamingResponse:
    buffer = io.BytesIO()
    doc.save(buffer, garbage=4, deflate=True)
    doc.close()
    buffer.seek(0)
    safe_name = download_name or (Path(filename).stem + "-updated.pdf")
    headers = {"Content-Disposition": f'attachment; filename="{safe_name}"'}
    if extra_headers:
        headers.update(extra_headers)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers=headers,
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


def _apply_redactions(page: fitz.Page) -> None:
    try:
        page.apply_redactions(images=2, graphics=1, text=0)
    except TypeError:
        page.apply_redactions()


def _inflate(rect: fitz.Rect, pad: float = 1.0) -> fitz.Rect:
    box = fitz.Rect(rect)
    box.x0 -= pad
    box.y0 -= pad
    box.x1 += pad
    box.y1 += pad
    return box


def _unique_rects(rects: list[fitz.Rect]) -> list[fitz.Rect]:
    seen: set[tuple[float, float, float, float]] = set()
    out: list[fitz.Rect] = []
    for rect in rects:
        box = fitz.Rect(rect)
        key = (round(box.x0, 1), round(box.y0, 1), round(box.x1, 1), round(box.y1, 1))
        if key in seen:
            continue
        seen.add(key)
        out.append(box)
    return out


def _word_boundary_ok(text: str, start: int, length: int) -> bool:
    end = start + length
    left_ok = start == 0 or not text[start - 1].isalnum()
    right_ok = end >= len(text) or not text[end].isalnum()
    return left_ok and right_ok


def _rects_from_rawdict(page: fitz.Page, needle: str) -> list[fitz.Rect]:
    """Match text using per-character boxes (works when words are split)."""
    needle_l = needle.lower()
    single_word = " " not in needle_l
    rects: list[fitz.Rect] = []
    raw = page.get_text("rawdict")
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            chars: list[dict[str, Any]] = []
            for span in line.get("spans", []):
                chars.extend(span.get("chars") or [])
            if not chars:
                continue
            line_text = "".join(item.get("c", "") for item in chars)
            line_l = line_text.lower()
            start = 0
            while True:
                pos = line_l.find(needle_l, start)
                if pos < 0:
                    break
                if single_word and not _word_boundary_ok(line_l, pos, len(needle_l)):
                    start = pos + 1
                    continue
                chunk = chars[pos : pos + len(needle)]
                if chunk:
                    union = fitz.Rect(chunk[0]["bbox"])
                    for item in chunk[1:]:
                        union |= fitz.Rect(item["bbox"])
                    rects.append(union)
                start = pos + 1
    return rects


def _fontsize_for_rect(page: fitz.Page, rect: fitz.Rect) -> float:
    target = fitz.Rect(rect)
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                box = fitz.Rect(span.get("bbox") or (0, 0, 0, 0))
                if box.intersects(target):
                    size = float(span.get("size") or 0)
                    if size > 0:
                        return size
    return max(8.0, min(rect.height * 0.75, 18.0))


def _needle_variants(needle: str) -> list[str]:
    raw = " ".join((needle or "").split())
    if not raw:
        return []
    variants = {raw}
    variants.add(raw.replace("'", "\u2019").replace('"', "\u201d"))
    variants.add(raw.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"'))
    return list(variants)


def _search_rects(page: fitz.Page, needle: str) -> list[fitz.Rect]:
    """Find text boxes, including case-insensitive and split-character PDFs."""
    variants = _needle_variants(needle)
    if not variants:
        return []

    rects: list[fitz.Rect] = []
    for variant in variants:
        rects.extend(fitz.Rect(item) for item in page.search_for(variant))
        rects.extend(_rects_from_rawdict(page, variant))

        lower = variant.lower()
        words = page.get_text("words")
        parts = lower.split()
        if len(parts) == 1:
            for word in words:
                token = "".join(ch for ch in word[4].lower() if ch.isalnum())
                if token == "".join(ch for ch in lower if ch.isalnum()):
                    rects.append(fitz.Rect(word[:4]))
        else:
            for index in range(len(words) - len(parts) + 1):
                chunk = words[index : index + len(parts)]
                if not all(item[6] == chunk[0][6] for item in chunk):
                    continue
                if [item[4].lower() for item in chunk] != parts:
                    continue
                union = fitz.Rect(chunk[0][:4])
                for item in chunk[1:]:
                    union |= fitz.Rect(item[:4])
                rects.append(union)

    unique = _unique_rects(rects)
    lower = " ".join(variants[0].split()).lower()
    if " " not in lower:
        exact: list[fitz.Rect] = []
        needle_alnum = "".join(ch for ch in lower if ch.isalnum())
        for box in unique:
            got = "".join(ch for ch in page.get_textbox(box).lower() if ch.isalnum())
            if got == needle_alnum:
                exact.append(box)
        if exact:
            return exact
    return unique


def _replacement_box(page: fitz.Page, rect: fitz.Rect, text: str, fontsize: float) -> tuple[fitz.Rect, float]:
    size = max(7.0, min(fontsize, 28.0))
    needed = fitz.get_text_length(text or " ", fontname="helv", fontsize=size) + 8
    width = max(rect.width, needed)
    height = max(rect.height, size * 1.35)
    box = fitz.Rect(
        rect.x0,
        rect.y0,
        min(page.rect.x1 - 3, rect.x0 + width),
        min(page.rect.y1 - 3, rect.y0 + height),
    )
    return box, size


def _cover_box(page: fitz.Page, box: fitz.Rect) -> None:
    shape = page.new_shape()
    shape.draw_rect(box)
    shape.finish(color=None, fill=(1, 1, 1), width=0)
    shape.commit(overlay=True)


def _insert_replacement(page: fitz.Page, rect: fitz.Rect, text: str, fontsize: float) -> None:
    if not text:
        return
    size = max(7.0, min(fontsize, 28.0))
    baseline = min(rect.y1 - 1, rect.y0 + size * 0.82)
    page.insert_text(
        (rect.x0 + 0.5, baseline),
        text,
        fontsize=size,
        fontname="helv",
        color=(0, 0, 0),
        overlay=True,
    )


def _replace_text_on_page(page: fitz.Page, find_text: str, replace_text: str) -> int:
    """Remove original glyphs, then write replacement in that location."""
    rects = _search_rects(page, find_text)
    if not rects:
        return 0

    jobs: list[tuple[fitz.Rect, fitz.Rect, float]] = []
    for rect in rects:
        orig = fitz.Rect(rect)
        size = _fontsize_for_rect(page, orig)
        box, size = _replacement_box(page, orig, replace_text, size)
        jobs.append((orig, box, size))

    for orig, box, _size in jobs:
        wipe = _inflate(orig | box, 0.5)
        try:
            page.add_redact_annot(wipe, fill=(1, 1, 1), cross_out=False)
        except TypeError:
            page.add_redact_annot(wipe, fill=(1, 1, 1))
    _apply_redactions(page)
    try:
        page.wrap_contents()
    except Exception:
        pass
    try:
        page.clean_contents()
    except Exception:
        pass

    if replace_text:
        for _orig, box, size in jobs:
            _cover_box(page, box)
            _insert_replacement(page, box, replace_text, size)
        if replace_text not in (page.get_text() or ""):
            for _orig, box, size in jobs:
                annot = page.add_freetext_annot(
                    box,
                    replace_text,
                    fontsize=size,
                    fontname="helv",
                    text_color=(0, 0, 0),
                    fill_color=(1, 1, 1),
                    border_width=0,
                    align=0,
                )
                annot.update()

    return len(jobs)


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
                for rect in _search_rects(page, phrase):
                    try:
                        page.add_redact_annot(_inflate(rect), fill=fill_rgb, cross_out=False)
                    except TypeError:
                        page.add_redact_annot(_inflate(rect), fill=fill_rgb)
                    hits += 1
            if page.annots():
                _apply_redactions(page)
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
    - replace visible text (find -> replace) by redacting original glyphs
    - optionally set metadata fields
    """
    data = _read_upload(file)
    find_text = find.strip()
    replace_text = replace
    if find_text and not replace_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Replace text is required. An empty replace only deletes the original text. Use /pdf/remove-text to redact.",
        )
    doc = _open_pdf(data)
    replaced = 0
    try:
        if find_text:
            for index in range(doc.page_count):
                replaced += _replace_text_on_page(doc[index], find_text, replace_text)
            if replaced == 0:
                raise HTTPException(status_code=404, detail=f"Text not found: {find_text}")
            written = "\n".join(doc[i].get_text() for i in range(doc.page_count))
            if replace_text not in written:
                raise HTTPException(
                    status_code=500,
                    detail="Original text was removed but replacement could not be written. Try a shorter replace string.",
                )

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

        extra = {"X-Replaced-Count": str(replaced)}
        return _pdf_response(doc, file.filename or "document.pdf", extra_headers=extra)
    except HTTPException:
        doc.close()
        raise
    except Exception:
        doc.close()
        raise


@app.post("/pdf/assemble")
async def assemble_pdfs(files: list[UploadFile] = File(...)) -> StreamingResponse:
    """Combine multiple PDFs into one PDF, in the order uploaded."""
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Upload at least two PDF files to assemble")
    if len(files) > 30:
        raise HTTPException(status_code=400, detail="Maximum 30 PDF files per assemble")

    combined = fitz.open()
    try:
        for upload in files:
            data = _read_upload(upload)
            source = _open_pdf(data)
            try:
                if source.page_count < 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{upload.filename or 'file'} has no pages",
                    )
                if source.is_encrypted:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{upload.filename or 'file'} is encrypted and cannot be assembled",
                    )
                combined.insert_pdf(source)
            finally:
                source.close()
        extra = {"X-Assembled-Files": str(len(files)), "X-Assembled-Pages": str(combined.page_count)}
        return _pdf_response(
            combined,
            "assembled.pdf",
            extra_headers=extra,
            download_name="assembled.pdf",
        )
    except HTTPException:
        combined.close()
        raise
    except Exception:
        combined.close()
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
