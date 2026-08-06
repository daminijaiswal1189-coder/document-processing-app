/**
 * POST /process/word — validates .docx required content and returns PASS/FAIL.
 */
import axios from 'axios'
import { API_BASE_URL } from '../utils/constants'

const api = axios.create({
  baseURL: API_BASE_URL,
})

/**
 * @param {string} filename - Stored upload basename (UUID.docx).
 * @returns {Promise<object>} WordValidationResponse.
 */
export async function processWord(filename) {
  const { data } = await api.post('/process/word', { filename })
  return data
}
