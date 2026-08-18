/**
 * POST /process/excel — adds POC Status column and returns download metadata.
 */
import api from './apiClient'

/**
 * @param {string} filename - Stored upload basename (UUID.xlsx) from UploadResponse.
 * @returns {Promise<object>} ExcelProcessResponse with download_url and details.
 */
export async function processExcel(filename) {
  const { data } = await api.post('/process/excel', { filename })
  return data
}

/**
 * Download processed workbook from GET /download/{processed_filename}.
 *
 * @param {string} processedFilename - e.g. processed_<uuid>.xlsx
 * @param {number|string} [cacheBust] - Query param to avoid browser cache reuse.
 */
export async function downloadProcessedExcel(processedFilename, cacheBust) {
  const version =
    cacheBust != null && cacheBust !== '' ? cacheBust : Date.now()
  const { data } = await api.get(
    `/download/${encodeURIComponent(processedFilename)}?v=${encodeURIComponent(version)}`,
    {
      responseType: 'blob',
    },
  )

  const blobUrl = window.URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = processedFilename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(blobUrl)
}

/**
 * Trigger browser download for a processed Excel result (file stays on server).
 */
export async function downloadProcessedExcelResult(excelResult) {
  if (!excelResult?.processed_filename) return
  await downloadProcessedExcel(
    excelResult.processed_filename,
    excelResult.processing_time_ms ?? Date.now(),
  )
}
