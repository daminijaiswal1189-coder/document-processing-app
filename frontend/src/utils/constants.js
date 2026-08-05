export const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export const ALLOWED_EXTENSIONS = ['.xlsx', '.docx', '.pdf']

/** Max files when multi-upload mode is selected */
export const MAX_MULTI_UPLOAD = 20

export function isAllowedExtension(filename) {
  const lower = filename.toLowerCase()
  return ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))
}
