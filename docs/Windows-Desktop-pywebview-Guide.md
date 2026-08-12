# Windows desktop (pywebview) — steps for 32-bit or 64-bit Python

This runs the POC as a **desktop window** using **pywebview** + FastAPI.  
Works with **32-bit Python** (recommended path for 32-bit machines). Electron/Tauri are not required.

---

## What you need on the Windows machine

1. **Python 3.11 or 3.12** (32-bit OK; 64-bit better for large Excel)  
2. **Node.js 20 LTS** (only to build the React UI once)  
3. **Microsoft Edge WebView2** (usually already on Windows 10/11)  
   - If missing: [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)  
4. This repo copied to a folder, e.g. `C:\Apps\POC-APP`

---

## Step 1 — Confirm Python bitness

Open **Command Prompt** or **PowerShell**:

```bat
python --version
python -c "import struct; print(struct.calcsize('P') * 8, 'bit')"
```

- Prints `32 bit` or `64 bit` — both work with this launcher.  
- Prefer **64 bit** if you process large Excel files.

---

## Step 2 — Backend virtual environment + packages

```bat
cd C:\Apps\POC-APP\backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
```

**If 32-bit Python:**

```bat
pip install -r requirements-32bit.txt
pip install pywebview
```

**If 64-bit Python:**

```bat
pip install -r requirements.txt
pip install pywebview
```

---

## Step 3 — Build the React UI (once, or after UI changes)

```bat
cd C:\Apps\POC-APP\frontend
npm ci
set VITE_API_URL=http://127.0.0.1:8000
npm run build
```

This creates `C:\Apps\POC-APP\frontend\dist`.  
FastAPI serves that folder when you start the desktop app.

---

## Step 4 — Run as desktop app

```bat
cd C:\Apps\POC-APP\backend
.venv\Scripts\activate
python ..\desktop\launch.py
```

You should see:

1. API start on `http://127.0.0.1:8000`  
2. A **native window** titled **Document Processing POC**  
3. The same Home / upload / process UI as in the browser  

Close the window to exit (API thread stops with the process).

---

## Step 5 — Optional: shortcut for demo

1. Create `C:\Apps\POC-APP\desktop\run-poc.bat`:

```bat
@echo off
cd /d C:\Apps\POC-APP\backend
call .venv\Scripts\activate
python ..\desktop\launch.py
pause
```

2. Right-click → **Create shortcut** on Desktop.  
3. Double-click the shortcut for demos.

---

## Step 6 — Optional: one EXE later (PyInstaller)

Only after Steps 1–4 work:

```bat
cd C:\Apps\POC-APP\backend
.venv\Scripts\activate
pip install pyinstaller
```

Packaging needs care (include `frontend\dist`, app package, etc.).  
Get the window working with `launch.py` first; EXE packaging can be a follow-up.

---

## Daily use checklist

| Check | Command / action |
|--------|------------------|
| WebView2 installed | Open Edge once; or install WebView2 Runtime |
| UI built | `frontend\dist` exists |
| Venv active | `backend\.venv\Scripts\activate` |
| Launch | `python ..\desktop\launch.py` |
| Health | Browser: `http://127.0.0.1:8000/health` → `{"status":"ok"}` |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `frontend/dist not found` | Run Step 3 (`npm run build`) |
| `pywebview is not installed` | `pip install pywebview` in the venv |
| Blank / white window | Install **WebView2 Runtime**; retry |
| Port 8000 in use | Stop other uvicorn; or change `PORT` in `desktop\launch.py` |
| Excel very slow (32-bit) | Expected for large files; use 64-bit Python if possible |
| Static path permission errors | Upload processing still works; static update is skipped |

---

## Notes

- Bind is **127.0.0.1** only (local desktop, not public).  
- On 32-bit, the app uses a lighter Excel path by default (see `excel_config.py`).  
- Dev mode (Vite on 5173 + uvicorn) still works separately if you prefer not to use the desktop window.
