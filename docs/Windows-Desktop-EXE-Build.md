# Build Windows desktop UI as .exe (and optional Setup installer)

Standalone Windows app. The EXE contains the FastAPI backend and starts it locally.

## Output

| Artifact | Path |
|----------|------|
| **App EXE** | `desktop\dist\POC-UI\POC-UI.exe` |
| **Config** | `desktop\dist\POC-UI\config.json` |
| **Optional Setup** | `desktop\installer\POC-UI-Setup.exe` (via Inno Setup) |

Users double-click **POC-UI.exe** — not `python launch.py`.

---

## One-time build on Windows

### Prerequisites
- Python 3.11/3.12 (**use 32-bit Python if target PCs are 32-bit**)
- Node.js 20
- WebView2 Runtime
- Repo at e.g. `C:\Apps\POC-APP`

### Build the EXE

```bat
cd C:\Apps\POC-APP\desktop
build-windows.bat
```

This will:
1. `npm run build` → `frontend\dist`
2. Install `pywebview` + `pyinstaller`
3. Create `desktop\dist\POC-UI\POC-UI.exe`

### Run the desktop app

1. Double-click:
   `C:\Apps\POC-APP\desktop\dist\POC-UI\POC-UI.exe`

2. To switch localhost vs domain, edit:
   `desktop\dist\POC-UI\config.json`
   then restart the EXE (no rebuild).

---

## Optional: Setup.exe / Start Menu (Inno Setup)

1. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Run `build-windows.bat` first
3. Open `desktop\POC-UI.iss` in Inno Setup Compiler → **Build**
4. Installer output: `desktop\installer\POC-UI-Setup.exe`

That gives a normal Windows install experience. A true **`.msi`** needs WiX; Setup.exe is usually enough for POC demos.

---

## What is inside the EXE package

- React UI (`frontend/dist`)
- Local FastAPI server + WebView2 window
- FastAPI and the Excel, Word, and PDF processing dependencies
- `config.json` for API URL


---

## Partial updates

| Change | Action |
|--------|--------|
| UI only | Re-run `build-windows.bat`, redistribute `POC-UI` folder or new Setup |
| API URL only | Edit `config.json` next to EXE |
| Backend only | Update Python/IIS only — no new EXE |

---

## Dev without EXE

```bat
python desktop\launch.py
```

Same behavior; use EXE for demos and distribution.
