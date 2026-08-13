# Windows Server Deployment Guide — Document Processing POC

This guide explains how to host the POC on a **Windows Server** and serve it on a **custom domain** (HTTPS). It matches the current repo layout: **React (Vite) frontend** + **FastAPI backend**.

---

## 1. What you are deploying

| Component | Role | Production shape |
|-----------|------|------------------|
| **Frontend** | React UI | Static files (`frontend/dist`) served by IIS |
| **Backend** | FastAPI + uvicorn | Windows service on `127.0.0.1:8000` (not public) |
| **Reverse proxy** | IIS + URL Rewrite + ARR | Public HTTPS on your domain → API + static site |
| **Storage** | Uploads & processed Excel | `backend/storage/uploads`, `backend/storage/processed` |
| **Logs** | Backend logs | `backend/logs/` |

**Recommended URL layout (single domain, simplest for browsers):**

- `https://docs.yourcompany.com/` → React app  
- `https://docs.yourcompany.com/upload`, `/process/*`, `/download/*`, `/health` → proxied to FastAPI  

With that layout, the browser sees **one origin**; you avoid most CORS issues.

---

## 2. Server prerequisites

### Hardware / OS

- Windows Server 2019 or 2022 (or Windows 10/11 for a lab demo)
- Enough disk for uploads and processed files (plan for large Excel/PDF)

### Software to install

1. **Python 3.11 or 3.12 (64-bit)**  
   - [python.org](https://www.python.org/downloads/windows/) — check **“Add python to PATH”** during install  
   - Verify: `python --version`

2. **Node.js 20 LTS (64-bit)** — only needed **on the build machine** (can be the same server)  
   - Verify: `node --version`, `npm --version`

3. **Git** (optional) — to clone the repo on the server

4. **IIS (Internet Information Services)**  
   - Server Manager → Add Roles → **Web Server (IIS)**  
   - Enable: **Static Content**, **HTTP Redirection**, **Application Request Routing** (install ARR separately if needed), **URL Rewrite** ([download URL Rewrite](https://www.iis.net/downloads/microsoft/url-rewrite))

5. **Visual C++ Redistributable** — sometimes required for PyMuPDF wheels

### Network / DNS

- **A record** (or CNAME): `docs.yourcompany.com` → public IP of the server  
- Firewall: allow inbound **TCP 443** (and **80** temporarily for certificate validation)

---

## 3. Deploy application files on the server

Example install path: `C:\Apps\POC-APP`

### Option A — Git clone

```powershell
cd C:\Apps
git clone <your-repo-url> POC-APP
cd POC-APP
```

### Option B — Copy ZIP from your dev machine

Copy the project **without** `node_modules`, `.venv`, or large sample files you do not need.

---

## 4. Backend setup (Python)

```powershell
cd C:\Apps\POC-APP\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Test manually:**

```powershell
cd C:\Apps\POC-APP\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another window:

```powershell
curl http://127.0.0.1:8000/health
```

Expect: `{"status":"ok"}`

Stop uvicorn (Ctrl+C) before configuring the service.

### Folders created at runtime

On startup the API creates:

- `backend\storage\uploads`
- `backend\storage\processed`
- `backend\logs`

Ensure the **Windows service account** (see below) has **Modify** permission on `backend\storage` and `backend\logs`.

### Environment variables (recommended on server)

Set these for the service account (System Properties → Environment Variables, or NSSM):

| Variable | Purpose | Example (Windows) |
|----------|---------|-------------------|
| `ALLOWED_DOCUMENT_PATH_ROOTS` | Extra roots for **Server path** upload | `D:\SharedDocs;D:\OneDrive` |
| (optional) | Path list uses **`;`** on Windows | |

Paths for `/upload/path` must still be under allowed roots (project folder, user home, or `ALLOWED_DOCUMENT_PATH_ROOTS`).

### In-place Excel path

If you use static in-place processing, edit `backend\app\services\excel\excel_config.py`:

- `STATIC_INPLACE_EXCEL_PATH` → Windows path, e.g. `D:\Data\2026helpwc 000006.xlsx`
- The file must be readable/writable by the service account
- Close Excel on the server when processing; OneDrive/sync locks can block saves

---

## 5. Frontend build (production)

Set the API base URL to your **public site URL** (same domain as the UI if using IIS reverse proxy):

```powershell
cd C:\Apps\POC-APP\frontend
npm ci
$env:VITE_API_URL = "https://docs.yourcompany.com"
npm run build
```

Output: `frontend\dist\` (static HTML/JS/CSS)

**Important:** Rebuild whenever you change domains or API URL. `VITE_API_URL` is baked in at build time.

---

## 6. Production CORS (required if API and UI use different hostnames)

Today `backend/app/main.py` allows only localhost Vite ports. For production you must either:

**A (recommended):** Same domain via IIS proxy (no cross-origin calls) — still safe to add your domain to CORS for health checks.

**B:** API on `https://api.yourcompany.com` and UI on `https://docs.yourcompany.com` — add those origins to `CORSMiddleware` in `main.py` before go-live.

Example origins to add:

```python
"https://docs.yourcompany.com",
"https://www.yourcompany.com",
```

Redeploy backend after changing CORS.

---

## 7. Run backend as a Windows service (NSSM)

Running uvicorn in a logged-in session is fine for demos; production should use a service.

1. Download [NSSM](https://nssm.cc/download) and extract `nssm.exe` (e.g. to `C:\Tools\nssm`).

2. Install service (run **elevated** Command Prompt or PowerShell):

```powershell
C:\Tools\nssm\nssm.exe install POC-APP-API
```

Set in the NSSM GUI:

| Field | Value |
|-------|--------|
| **Path** | `C:\Apps\POC-APP\backend\.venv\Scripts\python.exe` |
| **Startup directory** | `C:\Apps\POC-APP\backend` |
| **Arguments** | `-m uvicorn app.main:app --host 127.0.0.1 --port 8000` |

Optional **I/O** tab: redirect stdout/stderr to `C:\Apps\POC-APP\backend\logs\uvicorn.log`.

3. Start service:

```powershell
C:\Tools\nssm\nssm.exe start POC-APP-API
```

**Alternative:** IIS can run HttpPlatformHandler with uvicorn; NSSM is simpler for this POC.

---

## 8. IIS — site, SSL, static frontend, API proxy

### 8.1 Create IIS site

1. IIS Manager → **Sites** → **Add Website**  
   - Site name: `POC-APP`  
   - Physical path: `C:\Apps\POC-APP\frontend\dist`  
   - Binding: `https`, port `443`, hostname `docs.yourcompany.com`, select SSL certificate  

2. Application pool: **No Managed Code**, identity with read access to `dist` and (if needed) write nowhere for static site.

### 8.2 SSL certificate

- **Corporate:** Import PFX into **Local Computer → Personal**, bind in IIS.  
- **Public CA (Let’s Encrypt):** Use [win-acme](https://www.win-acme.com/) on Windows to issue and auto-renew.

### 8.3 SPA routing (React Router)

For client-side routes (e.g. `/result`), add a `web.config` in `frontend\dist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="SPA fallback" stopProcessing="true">
          <match url=".*" />
          <conditions logicalGrouping="MatchAll">
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
            <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
          </conditions>
          <action type="Rewrite" url="/index.html" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
```

Rebuild/copy after `npm run build` if you add this file under `frontend/public/` so Vite copies it to `dist`.

### 8.4 Reverse proxy API to uvicorn

Enable **ARR** proxy: IIS → server node → **Application Request Routing Cache** → **Server Proxy Settings** → Enable proxy.

In the site’s `web.config` (merge with SPA rule carefully), add rules **before** SPA fallback for API paths:

```xml
<rule name="ReverseProxyToFastAPI" stopProcessing="true">
  <match url="^(health|upload|process|download)(/.*)?$" />
  <action type="Rewrite" url="http://127.0.0.1:8000/{R:0}" />
</rule>
```

Adjust the regex if you add more top-level API routes later.

**Large uploads:** In IIS → site → **Configuration Editor** → `system.webServer/serverRuntime` → increase **`uploadReadAheadSize`** and request limits as needed (e.g. 100MB+ for big Excel). Also consider `maxRequestBodySize` in ASP.NET settings if applicable.

---

## 9. Post-deploy verification checklist

| Step | Action | Expected |
|------|--------|----------|
| 1 | Browse `https://docs.yourcompany.com` | Home page loads |
| 2 | `https://docs.yourcompany.com/health` | `{"status":"ok"}` |
| 3 | Upload a small PDF/Excel | Result page runs processing |
| 4 | Download processed Excel | File downloads |
| 5 | Server path (if used) | Path under allowed roots works |
| 6 | Check `backend\logs\` | New log file on service start |

---

## 10. Domain-only vs split API subdomain

### Single domain (recommended)

- `VITE_API_URL=https://docs.yourcompany.com`  
- IIS proxies API paths to `127.0.0.1:8000`  
- Minimal CORS changes  

### Split subdomain

- UI: `https://docs.yourcompany.com`  
- API: `https://api.yourcompany.com` → separate IIS site or binding, proxy all traffic to uvicorn  
- `VITE_API_URL=https://api.yourcompany.com`  
- **Must** update CORS in `main.py`  

---

## 11. Security notes for production (beyond POC)

The POC is not production-hardened. Before exposing to the internet:

- [ ] Add **authentication** (Azure AD, IIS Windows Auth, or API keys)  
- [ ] Restrict **Server path** feature to admins or disable on public deployments  
- [ ] Review `STATIC_INPLACE_EXCEL_PATH` — do not point at sensitive shares without ACLs  
- [ ] **HTTPS only**; redirect HTTP → HTTPS  
- [ ] Patch Windows, Python, and Node regularly  
- [ ] Antivirus scanning on upload folder (policy-dependent)  
- [ ] Backup `storage` and document retention policy  
- [ ] Rate limiting / max upload size at IIS and application layer  

---

## 12. Updating the app

```powershell
cd C:\Apps\POC-APP
git pull   # or copy new files

cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Restart POC-APP-API service

cd ..\frontend
npm ci
$env:VITE_API_URL = "https://docs.yourcompany.com"
npm run build
# IIS serves updated dist automatically
```

Restart IIS site or app pool only if you changed `web.config`.

---

## 13. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| UI loads, API 404 | Proxy rule missing/wrong | Fix `web.config` rewrite; confirm ARR enabled |
| CORS error in browser | UI and API different origins | Same-domain proxy or update `CORSMiddleware` |
| 502 Bad Gateway | uvicorn not running | Start NSSM service; check port 8000 |
| Upload fails on large file | IIS/body size limit | Increase upload limits in IIS |
| Path upload rejected | Path outside allowed roots | Set `ALLOWED_DOCUMENT_PATH_ROOTS` or move file |
| In-place Excel fails | File locked or permissions | Close Excel; grant service account write access |
| `.xls` fails on server | Missing xlrd | `pip install -r requirements.txt` in venv |

---

## 14. Quick reference — paths on server

| Item | Path |
|------|------|
| App root | `C:\Apps\POC-APP` |
| Backend venv | `C:\Apps\POC-APP\backend\.venv` |
| Uploads | `C:\Apps\POC-APP\backend\storage\uploads` |
| Processed | `C:\Apps\POC-APP\backend\storage\processed` |
| Logs | `C:\Apps\POC-APP\backend\logs` |
| Frontend build | `C:\Apps\POC-APP\frontend\dist` |

---

## 15. Optional: firewall lock-down

- Do **not** expose port **8000** on the public firewall.  
- Only **443** (and 80 for redirect) should be open; IIS talks to uvicorn on localhost.

---

*Replace `docs.yourcompany.com` with your real domain throughout. Adjust `C:\Apps\POC-APP` if you use a different install path.*
