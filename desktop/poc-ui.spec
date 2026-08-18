# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec: frontend-only desktop UI (WebView2 / pywebview).

Build (from repo root, with venv that has pywebview + pyinstaller):
  cd frontend && npm ci && npm run build
  cd ../desktop && pyinstaller poc-ui.spec

Output: desktop/dist/POC-UI/POC-UI.exe
Backend is NOT included — run uvicorn/IIS separately.
"""

from pathlib import Path

# SPECPATH is the directory containing this .spec file, not the spec file itself.
SPECDIR = Path(SPECPATH).resolve()
REPO = SPECDIR.parent
FRONTEND_DIST = REPO / "frontend" / "dist"
CONFIG = SPECDIR / "config.json"

datas = []
if FRONTEND_DIST.is_dir():
    datas.append((str(FRONTEND_DIST), "frontend/dist"))
if CONFIG.is_file():
    datas.append((str(CONFIG), "."))

# Bundle the backend app package so the EXE can start its own FastAPI server.
BACKEND_APP = REPO / "backend" / "app"
if BACKEND_APP.is_dir():
    datas.append((str(BACKEND_APP), "app"))

BACKEND_UTILS = REPO / "backend" / "logs"
if BACKEND_UTILS.exists():
    datas.append((str(BACKEND_UTILS), "logs"))

a = Analysis(
    [str(SPECDIR / "launch.py")],
    pathex=[str(SPECDIR)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "webview",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        "uvicorn",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "uvicorn.config",
        "fastapi",
        "fastapi.middleware.cors",
        "app",
        "app.main",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "openpyxl",
        "xlrd",
        "pymupdf",
        "fitz",
        "docx",
        "pypdf",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="POC-UI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # keep visible logs for startup diagnosis
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="POC-UI",
)
