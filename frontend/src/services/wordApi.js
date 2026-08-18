/**
 * POST /process/word — validates .docx required content and returns PASS/FAIL.
 */
import api from './apiClient'

/**
 * @param {string} filename - Stored upload basename (UUID.docx).
 * @returns {Promise<object>} WordValidationResponse.
 */
export async function processWord(filename) {
  const { data } = await api.post('/process/word', { filename })
  return data
}
