/**
 * Backend API base URL and shared upload constraints.
 *
 * VITE_API_URL overrides the default local FastAPI server (port 8000).
 */
export const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

/** Extensions accepted by the drop zone and validated before upload. */
export const ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.docx', '.pdf']

/** Maximum files when multi-upload mode is selected on HomePage. */
export const MAX_MULTI_UPLOAD = 20

/**
 * @param {string} filename - Original file name from the user's machine.
 * @returns {boolean} True if the name ends with an allowed extension.
 */
export function isAllowedExtension(filename) {
  const lower = filename.toLowerCase()
  return ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))
}
