# Build Windows desktop UI as .exe (and optional Setup installer)

Frontend-only Windows app. Backend stays separate (Python / IIS).

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

1. Start backend (separate):
   ```bat
   cd C:\Apps\POC-APP\backend
   .venv\Scripts\activate
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   Or use IIS on your domain.

2. Double-click:
   `C:\Apps\POC-APP\desktop\dist\POC-UI\POC-UI.exe`

3. To switch localhost vs domain, edit:
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
- Small local static server + WebView2 window
- `config.json` for API URL

**Not inside:** FastAPI, openpyxl, Excel processing — those stay on the backend host.

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
