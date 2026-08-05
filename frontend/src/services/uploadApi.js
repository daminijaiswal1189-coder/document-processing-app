import axios from 'axios'
import { API_BASE_URL } from '../utils/constants'

const api = axios.create({
  baseURL: API_BASE_URL,
})

export async function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return data
}

/**
 * Upload many files (one POST /upload per file — matches current backend).
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
