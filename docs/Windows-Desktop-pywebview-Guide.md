# Windows desktop UI (WebView2) — ship as .exe

**Users run `POC-UI.exe`**, not `python launch.py`.

Backend stays separate (uvicorn or IIS).

## Quick path

```bat
cd desktop
build-windows.bat
```

Then start backend, then double-click:

`desktop\dist\POC-UI\POC-UI.exe`

Full instructions: [Windows-Desktop-EXE-Build.md](./Windows-Desktop-EXE-Build.md)

## Config (localhost vs domain)

Edit `desktop\dist\POC-UI\config.json` (or `desktop\config.json` before build).

## Optional installer

Use Inno Setup with `desktop\POC-UI.iss` → `POC-UI-Setup.exe`.
