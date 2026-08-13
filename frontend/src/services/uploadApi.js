/**
 * HTTP client for POST /upload and POST /upload/path.
 *
 * Flow:
 *   HomePage → uploadDocument | registerDocumentPath → navigate to /result with uploadResult.
 *   ResultPage uses uploadResult.data.filename for /process/* calls.
 */
import axios from 'axios'
import { API_BASE_URL } from '../utils/constants'

/** Axios instance targeting the FastAPI backend. */
const api = axios.create({
  baseURL: API_BASE_URL,
})

/**
 * Upload one file via multipart POST /upload.
 *
 * @param {File} file - Browser File from the drop zone.
 * @returns {Promise<object>} UploadResponse JSON (message, data.filename, data.document_type).
 */
export async function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post('/upload', formData)

  return data
}

/**
 * Register a document that already exists on the server (POST /upload/path).
 *
 * @param {string} filePath - Absolute or project-relative path on the backend machine.
 * @returns {Promise<object>} UploadResponse including data.source_path when copied from disk.
 */
export async function registerDocumentPath(filePath) {
  const { data } = await api.post('/upload/path', { file_path: filePath.trim() })
  return data
}

/**
 * Upload many files sequentially (one POST /upload per file).
 *
 * @param {File[]} files - Selected files from multi-upload mode.
 * @param {(progress: { current: number, total: number, fileName: string }) => void} [onProgress]
 * @returns {Promise<Array<{ originalFilename, fileSize, uploadResult }>>}
 */
export async function uploadDocuments(files, onProgress) {
  const results = []
  const total = files.length

  for (let i = 0; i < total; i += 1) {
    const file = files[i]
    onProgress?.({ current: i + 1, total, fileName: file.name })
    const uploadResult = await uploadDocument(file)
    results.push({
      originalFilename: file.name,
      fileSize: file.size,
      uploadResult,
    })
  }

  return results
}
