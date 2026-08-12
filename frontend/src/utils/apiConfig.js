/**
 * Runtime API base URL for desktop shell and browser.
 *
 * Order:
 *  1. /app-config.json from the desktop UI static server (pywebview launcher)
 *  2. VITE_API_URL at build time
 *  3. http://127.0.0.1:8000
 */
let apiBaseUrl = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

/** Current API origin (no trailing slash). */
export function getApiBaseUrl() {
  return apiBaseUrl.replace(/\/$/, '')
}

/**
 * Load desktop/runtime config before rendering the app.
 * Safe to call in browser-only mode (missing file → keep default).
 */
export async function loadApiConfig() {
  try {
    const res = await fetch('/app-config.json', { cache: 'no-store' })
    if (!res.ok) return getApiBaseUrl()
    const data = await res.json()
    const local = String(data.apiBaseUrl || '').replace(/\/$/, '')
    const fallback = String(data.fallbackApiBaseUrl || '').replace(/\/$/, '')
    const preferLocal = data.preferLocalhost !== false

    if (preferLocal && local) {
      const ok = await pingHealth(local)
      apiBaseUrl = ok ? local : fallback || local
    } else if (fallback) {
      const ok = await pingHealth(fallback)
      apiBaseUrl = ok ? fallback : local || fallback
    } else if (local) {
      apiBaseUrl = local
    }
  } catch {
    // Vite dev / no desktop config — keep build-time default
  }
  return getApiBaseUrl()
}

async function pingHealth(base) {
  try {
    const ctrl = new AbortController()
    const t = setTimeout(() => ctrl.abort(), 1500)
    const res = await fetch(`${base}/health`, { signal: ctrl.signal })
    clearTimeout(t)
    return res.ok
  } catch {
    return false
  }
}
