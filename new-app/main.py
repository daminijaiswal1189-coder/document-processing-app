from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.jobs import router as jobs_router
from config.settings import HOST, PORT, TEMPLATES_DIR

app = FastAPI(
    title="MOA Valuation Package Automation",
    version="0.1.0",
    description="Phase 1: assemble source PDFs, extract a Plan Profile, and save the named valuation package.",
    servers=[{"url": "/"}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "phase": "1"}


@app.get("/")
def ui() -> FileResponse:
    html = TEMPLATES_DIR / "index.html"
    if not html.is_file():
        raise FileNotFoundError(f"UI missing: {html}")
    return FileResponse(html, media_type="text/html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
