import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.download import router as download_router
from app.api.excel import router as excel_router
from app.api.pdf import router as pdf_router
from app.api.upload import router as upload_router
from app.utils.paths import ensure_processed_dir, ensure_uploads_dir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Document Validation & Excel Processing POC",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(excel_router)
app.include_router(pdf_router)
app.include_router(download_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Simple check that the API is running."""
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    ensure_uploads_dir()
    ensure_processed_dir()
    logger.info("Backend started")
