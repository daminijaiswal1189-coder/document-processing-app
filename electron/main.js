const { app, BrowserWindow } = require("electron");
const http = require("http");

const API_URL = "http://127.0.0.1:8000";
const HEALTH_URL = "http://127.0.0.1:8000/health";

function waitForHealth(timeoutMs = 30000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      const req = http.get(HEALTH_URL, (res) => {
        res.resume();
        if (res.statusCode === 200) {
          resolve();
          return;
        }
        retry();
      });
      req.on("error", retry);
      req.setTimeout(1500, () => {
        req.destroy();
        retry();
      });
    };

    const retry = () => {
      if (Date.now() - started > timeoutMs) {
        reject(
          new Error(
            `Backend not ready at ${HEALTH_URL}. Start uvicorn first:\n` +
              `  cd backend && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000`
          )
        );
        return;
      }
      setTimeout(tryOnce, 500);
    };

    tryOnce();
  });
}

async function createWindow() {
  await waitForHealth();

  const win = new BrowserWindow({
    width: 1280,
    height: 840,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.loadURL(API_URL);
}

if (!app) {
  console.error(
    "Electron `app` is undefined. Run with: npx electron . (not node main.js)"
  );
  process.exit(1);
}

app.whenReady().then(createWindow).catch((err) => {
  console.error(err.message || err);
  app.quit();
});

app.on("window-all-closed", () => {
  app.quit();
});
