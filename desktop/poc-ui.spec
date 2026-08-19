# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec: standalone desktop application (WebView2 / pywebview + FastAPI).

Build (from repo root, with venv that has pywebview + pyinstaller):
  cd frontend && npm ci && npm run build
  cd ../desktop && pyinstaller poc-ui.spec

Output: desktop/dist/POC-UI/POC-UI.exe
The FastAPI backend and document-processing dependencies are included.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

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

BACKEND_UTILS = REPO / "backend" / "logs"
if BACKEND_UTILS.exists():
    datas.append((str(BACKEND_UTILS), "logs"))

a = Analysis(
    [str(SPECDIR / "launch.py")],
    # ``app`` is imported by the launcher only at runtime.  It must be on the
    # analysis path or PyInstaller omits the whole FastAPI application.
    pathex=[str(SPECDIR), str(REPO / "backend")],
    binaries=[],
    datas=datas,
    hiddenimports=collect_submodules("app") + [
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
        # These are imported lazily by the document readers.
        "docx",
        "pypdf",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Do not exclude document-processing libraries: app.main imports the Excel
    # routes at startup, and the PDF/Word readers load their libraries lazily.
    excludes=[],
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
