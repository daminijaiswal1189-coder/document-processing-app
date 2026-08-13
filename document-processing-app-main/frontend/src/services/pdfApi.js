/**
 * POST /process/pdf — validates required content and returns PASS/FAIL.
 */
import axios from 'axios'
import { API_BASE_URL } from '../utils/constants'

const api = axios.create({
  baseURL: API_BASE_URL,
})

/**
 * @param {string} filename - Stored upload basename (UUID.pdf).
 * @returns {Promise<object>} PdfValidationResponse.
 */
export async function processPdf(filename) {
  const { data } = await api.post('/process/pdf', { filename })
  return data
}
