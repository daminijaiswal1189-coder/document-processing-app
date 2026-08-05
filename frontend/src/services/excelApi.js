import axios from 'axios'
import { API_BASE_URL } from '../utils/constants'

const api = axios.create({
  baseURL: API_BASE_URL,
})

export async function processExcel(filename) {
  const { data } = await api.post('/process/excel', { filename })
  return data
}

export async function downloadProcessedExcel(processedFilename) {
  const { data } = await api.get(`/download/${encodeURIComponent(processedFilename)}`, {
    responseType: 'blob',
  })

  const blobUrl = window.URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = processedFilename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(blobUrl)
}
