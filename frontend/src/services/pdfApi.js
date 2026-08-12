/**
 * POST /process/pdf — validates required content and returns PASS/FAIL.
 */
import api from './apiClient'

/**
 * @param {string} filename - Stored upload basename (UUID.pdf).
 * @returns {Promise<object>} PdfValidationResponse.
 */
export async function processPdf(filename) {
  const { data } = await api.post('/process/pdf', { filename })
  return data
}
