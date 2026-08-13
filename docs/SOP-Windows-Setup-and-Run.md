# SOP: Setup and Run the Document Processing Application on a New Windows Machine

## 1. Purpose
This SOP explains how to set up and run the Document Processing Application on a fresh Windows machine. It covers the required software, dependency installation, frontend build, backend startup, and the steps to launch the app for local use.

---

## 2. Scope
This procedure is intended for:
- New Windows developer or test machines
- Local app setup for demo, testing, or validation
- Browser-based use and optional desktop launcher use via pywebview

---

## 3. Required Software
Install the following before running the application.

### 3.1 Python
- Python 3.11 or 3.12 recommended
- 32-bit Python is acceptable for compatibility with this repo
- 64-bit Python is preferred for larger Excel files and better memory headroom

Check version:
```powershell
python --version
python -c "import struct; print(struct.calcsize('P') * 8, 'bit')"
```

### 3.2 Node.js
- Node.js 20 LTS or newer
- Required to install frontend packages and build the React app

Check version:
```powershell
node --version
npm --version
```

### 3.3 Git (optional but recommended)
```powershell
git --version
```

### 3.4 Microsoft Edge WebView2 Runtime (for desktop window mode)
This is required for the pywebview-based desktop launcher.

- If not already installed, install from:
  https://developer.microsoft.com/microsoft-edge/webview2/

---

## 4. Required Packages

### 4.1 Backend Python packages
The backend dependencies are listed in:
- `backend/requirements.txt`
- `backend/requirements-32bit.txt`

Core packages include:
- fastapi
- uvicorn
- python-multipart
- openpyxl
- xlrd
- python-docx
- pymupdf

For 32-bit Windows, use:
```powershell
pip install -r requirements-32bit.txt
```

For 64-bit Windows, use:
```powershell
pip install -r requirements.txt
```

If using the desktop launcher, also install:
```powershell
pip install pywebview
```

Optional packaging package:
```powershell
pip install pyinstaller
```

### 4.2 Frontend Node packages
The frontend package list is defined in `frontend/package.json` and will be installed using:
```powershell
npm install
```

---

## 5. Project Layout
The app is organized as follows:

```text
document-processing-app-main/
├── backend/
│   ├── app/
│   ├── storage/
│   ├── logs/
│   ├── requirements.txt
│   └── requirements-32bit.txt
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── dist/   # generated after build
├── docs/
├── README.md
└── samples/
```

---

## 6. Setup Procedure on a New Windows Machine

### Step 1: Copy the project
Copy the project folder to a local path such as:
```text
C:\Apps\document-processing-app-main
```

### Step 2: Create a backend virtual environment
Open PowerShell in the backend directory:
```powershell
cd C:\Apps\document-processing-app-main\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 3: Install backend packages
Use the correct requirements file for your Python architecture.

For 32-bit Python:
```powershell
pip install --upgrade pip
pip install -r requirements-32bit.txt
```

For 64-bit Python:
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

Optional desktop runtime dependency:
```powershell
pip install pywebview
```

### Step 4: Install frontend packages
Open a separate PowerShell window and run:
```powershell
cd C:\Apps\document-processing-app-main\frontend
npm install
```

### Step 5: Build the frontend
This creates the production UI files used by the app.

```powershell
cd C:\Apps\document-processing-app-main\frontend
npm run build
```

After a successful build, confirm the output exists:
```text
frontend\dist\index.html
```

---

## 7. Run the Application

### Option A: Run in browser mode
This is the recommended method for local development and validation.

1. Open PowerShell in `backend`
2. Activate the virtual environment
3. Start FastAPI

```powershell
cd C:\Apps\document-processing-app-main\backend
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open:
```text
http://127.0.0.1:8000
```

If the frontend is being served separately, the API is also expected at:
```text
http://127.0.0.1:8000/health
```

Expected response:
```json
{"status": "ok"}
```

### Option B: Run as desktop window (pywebview)
If the desktop launcher is available in the project or is added as a Windows wrapper, start it from the backend project folder:

```powershell
cd C:\Apps\document-processing-app-main\backend
.venv\Scripts\Activate.ps1
python ..\desktop\launch.py
```

This opens a native desktop window and loads the app UI locally without requiring the browser.

---

## 8. Optional: Create a Shortcut for Repeated Use
Create a `.bat` file for one-click startup.

Example:
```bat
@echo off
cd /d C:\Apps\document-processing-app-main\backend
call .venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
```

Place the file on the Desktop and double-click it to run the application.

---

## 9. Optional: Package as EXE
After the app is confirmed working, it can be packaged with PyInstaller.

Example:
```powershell
cd C:\Apps\document-processing-app-main\backend
.venv\Scripts\Activate.ps1
pyinstaller --onefile --windowed your_launcher_script.py
```

This creates a Windows executable for easier deployment.

---

## 10. Troubleshooting

### Problem: Python packages fail to install
- Verify Python architecture: 32-bit vs 64-bit
- Use the correct requirements file
- Reinstall pip and retry:

```powershell
python -m pip install --upgrade pip
```

### Problem: `npm install` fails
- Ensure Node.js and npm are installed
- Delete `node_modules` and retry:

```powershell
rmdir /s /q node_modules
npm install
```

### Problem: frontend build fails
- Ensure all frontend dependencies are installed
- Confirm you are in the correct folder:

```powershell
cd C:\Apps\document-processing-app-main\frontend
```

### Problem: app does not open in desktop mode
- Install WebView2 Runtime
- Confirm the backend is running on port 8000
- Check firewall or port conflicts

### Problem: port 8000 already in use
Stop any other service using the port or update the port number in the startup command.

---

## 11. Daily Use Checklist
Before starting:
- [ ] Python installed and version confirmed
- [ ] Node.js installed and version confirmed
- [ ] Backend venv created and activated
- [ ] Backend packages installed
- [ ] Frontend packages installed
- [ ] Frontend build completed successfully
- [ ] App started with uvicorn or desktop launcher

---

## 12. Approval / Sign-off
This SOP is valid for local setup and deployment on a clean Windows machine when the above steps are followed in order.

---

## 13. Related Files
- `backend/requirements.txt`
- `backend/requirements-32bit.txt`
- `frontend/package.json`
- `docs/Windows-Desktop-pywebview-Guide.md`
- `README.md`
