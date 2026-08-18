/**
 * Backend API base URL and shared upload constraints.
 *
 * Desktop shell: runtime URL from /app-config.json (see apiConfig.js).
 * Vite build: VITE_API_URL, else http://127.0.0.1:8000.
 */
import { getApiBaseUrl } from './apiConfig'

export { getApiBaseUrl } from './apiConfig'

/** Mutable base URL — refreshed after loadApiConfig() in main.jsx. */
export let API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

/** Sync API_BASE_URL with runtime config (call after loadApiConfig). */
export function refreshApiBaseUrl() {
  API_BASE_URL = getApiBaseUrl()
  return API_BASE_URL
}

/** Extensions accepted by the drop zone and validated before upload. */
export const ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.docx', '.pdf']

/** Maximum files when multi-upload mode is selected on HomePage. */
export const MAX_MULTI_UPLOAD = 20

/**
 * When true (default), Excel files auto-download in the browser after POST /process/excel.
 * Set VITE_AUTO_DOWNLOAD_EXCEL=false at build time to disable globally.
 */
export const AUTO_DOWNLOAD_EXCEL_AFTER_PROCESS =
  import.meta.env.VITE_AUTO_DOWNLOAD_EXCEL !== 'false'

/**
 * @param {string} filename - Original file name from the user's machine.
 * @returns {boolean} True if the name ends with an allowed extension.
 */
export function isAllowedExtension(filename) {
  const lower = filename.toLowerCase()
  return ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))
}
