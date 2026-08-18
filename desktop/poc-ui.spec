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

SPECDIR = Path(SPECPATH).resolve().parent
REPO = SPECDIR.parent
FRONTEND_DIST = REPO / "frontend" / "dist"
CONFIG = SPECDIR / "config.json"

datas = []
if FRONTEND_DIST.is_dir():
    datas.append((str(FRONTEND_DIST), "frontend/dist"))
if CONFIG.is_file():
    datas.append((str(CONFIG), "."))

a = Analysis(
    [str(SPECDIR / "launch.py")],
    pathex=[str(SPECDIR)],
    binaries=[],
    datas=datas,
    hiddenimports=["webview", "webview.platforms.winforms", "webview.platforms.edgechromium"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "uvicorn",
        "fastapi",
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
    console=False,  # windowed app (no console)
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
