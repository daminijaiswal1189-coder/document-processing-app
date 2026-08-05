import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate, Navigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import DownloadIcon from '@mui/icons-material/Download'
import TableChartOutlinedIcon from '@mui/icons-material/TableChartOutlined'
import PictureAsPdfOutlinedIcon from '@mui/icons-material/PictureAsPdfOutlined'
import RefreshIcon from '@mui/icons-material/Refresh'
import { downloadProcessedExcel, processExcel } from '../services/excelApi'
import { processPdf } from '../services/pdfApi'

const TYPE_LABELS = {
  excel: { label: 'Excel', color: 'success' },
  word: { label: 'Word', color: 'primary' },
  pdf: { label: 'PDF', color: 'error' },
}

function formatBytes(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function apiErrorMessage(err, fallback) {
  const detail = err.response?.data?.detail
  if (typeof detail === 'string') return detail
  return fallback
}

function NavButtons({ navigate }) {
  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
      <Button
        variant="contained"
        size="large"
        startIcon={<UploadFileIcon />}
        onClick={() => navigate('/')}
        fullWidth
      >
        Upload more files
      </Button>
      <Button
        variant="outlined"
        size="large"
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate('/')}
        fullWidth
      >
        Back to home
      </Button>
    </Stack>
  )
}

function MissingItemsTable({ title, items }) {
  if (!items?.length) return null
  return (
    <Box>
      <Typography variant="subtitle2" color="error" gutterBottom>
        {title}
      </Typography>
      <TableContainer>
        <Table size="small">
          <TableBody>
            {items.map((item) => (
              <TableRow key={item}>
                <TableCell sx={{ wordBreak: 'break-word' }}>{item}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

function PdfValidationCard({ pdfStatus, pdfError, pdfResult, onRetry }) {
  const passed = pdfResult?.status === 'PASS'

  return (
    <Card elevation={2}>
      <CardContent>
        <Stack direction="row" spacing={1} alignItems="center" mb={2}>
          <PictureAsPdfOutlinedIcon color="error" />
          <Typography variant="h6">PDF validation</Typography>
        </Stack>
        <Divider sx={{ mb: 2 }} />

        {pdfStatus === 'processing' && (
          <Stack direction="row" spacing={2} alignItems="center">
            <CircularProgress size={28} />
            <Typography color="text.secondary">Reading PDF and checking required content…</Typography>
          </Stack>
        )}

        {pdfStatus === 'error' && (
          <Stack spacing={2}>
            <Alert severity="error">{pdfError}</Alert>
            <Button variant="outlined" startIcon={<RefreshIcon />} onClick={onRetry}>
              Retry validation
            </Button>
          </Stack>
        )}

        {pdfStatus === 'done' && pdfResult && (
          <Stack spacing={2}>
            <Alert severity={passed ? 'success' : 'error'}>
              Validation status: <strong>{pdfResult.status}</strong>
              {' — '}
              {pdfResult.message}
            </Alert>
            <Typography variant="body2" color="text.secondary">
              Text extracted: {pdfResult.page_text_length?.toLocaleString()} characters
            </Typography>
            {!passed && (
              <Stack spacing={2}>
                <MissingItemsTable title="Missing headings" items={pdfResult.missing_headings} />
                <MissingItemsTable title="Missing questions" items={pdfResult.missing_questions} />
                <MissingItemsTable title="Missing answers" items={pdfResult.missing_answers} />
              </Stack>
            )}
          </Stack>
        )}
      </CardContent>
    </Card>
  )
}

function ExcelProcessCard({
  excelStatus,
  excelError,
  excelResult,
  downloading,
  onRetry,
  onDownload,
}) {
  return (
    <Card elevation={2}>
      <CardContent>
        <Stack direction="row" spacing={1} alignItems="center" mb={2}>
          <TableChartOutlinedIcon color="success" />
          <Typography variant="h6">Excel processing</Typography>
        </Stack>
        <Divider sx={{ mb: 2 }} />

        {excelStatus === 'processing' && (
          <Stack direction="row" spacing={2} alignItems="center">
            <CircularProgress size={28} />
            <Typography color="text.secondary">Inserting column next to Entry…</Typography>
          </Stack>
        )}

        {excelStatus === 'error' && (
          <Stack spacing={2}>
            <Alert severity="error">{excelError}</Alert>
            <Button variant="outlined" startIcon={<RefreshIcon />} onClick={onRetry}>
              Retry processing
            </Button>
          </Stack>
        )}

        {excelStatus === 'done' && excelResult && (
          <Stack spacing={2}>
            <Alert severity="success">{excelResult.message}</Alert>
            <TableContainer>
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Sheet</TableCell>
                    <TableCell>{excelResult.details.sheet_name}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>New column</TableCell>
                    <TableCell>{excelResult.details.new_column_header}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Rows updated</TableCell>
                    <TableCell>{excelResult.details.rows_updated}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Download file</TableCell>
                    <TableCell sx={{ wordBreak: 'break-word' }}>
                      {excelResult.processed_filename}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
            <Button
              variant="contained"
              color="success"
              size="large"
              startIcon={<DownloadIcon />}
              onClick={onDownload}
              disabled={downloading}
            >
              {downloading ? 'Downloading…' : 'Download updated Excel'}
            </Button>
          </Stack>
        )}
      </CardContent>
    </Card>
  )
}

function SingleResultView({ originalFilename, uploadResult, fileSize, navigate }) {
  const [excelStatus, setExcelStatus] = useState('idle')
  const [excelResult, setExcelResult] = useState(null)
  const [excelError, setExcelError] = useState('')
  const [downloading, setDownloading] = useState(false)

  const [pdfStatus, setPdfStatus] = useState('idle')
  const [pdfResult, setPdfResult] = useState(null)
  const [pdfError, setPdfError] = useState('')

  const storedFilename = uploadResult?.data?.filename
  const docType = uploadResult?.data?.document_type ?? 'unknown'
  const isExcel = docType === 'excel'
  const isPdf = docType === 'pdf'
  const typeMeta = TYPE_LABELS[docType] ?? { label: docType, color: 'default' }

  const runExcelProcess = useCallback(async () => {
    if (!storedFilename) return
    setExcelStatus('processing')
    setExcelError('')
    try {
      const result = await processExcel(storedFilename)
      setExcelResult(result)
      setExcelStatus('done')
    } catch (err) {
      setExcelStatus('error')
      setExcelError(
        apiErrorMessage(err, 'Excel processing failed. Does the sheet have an Entry column?'),
      )
    }
  }, [storedFilename])

  const runPdfValidation = useCallback(async () => {
    if (!storedFilename) return
    setPdfStatus('processing')
    setPdfError('')
    try {
      const result = await processPdf(storedFilename)
      setPdfResult(result)
      setPdfStatus('done')
    } catch (err) {
      setPdfStatus('error')
      setPdfError(apiErrorMessage(err, 'PDF validation failed.'))
    }
  }, [storedFilename])

  useEffect(() => {
    if (isExcel && storedFilename && excelStatus === 'idle') {
      runExcelProcess()
    }
  }, [isExcel, storedFilename, excelStatus, runExcelProcess])

  useEffect(() => {
    if (isPdf && storedFilename && pdfStatus === 'idle') {
      runPdfValidation()
    }
  }, [isPdf, storedFilename, pdfStatus, runPdfValidation])

  const uploadRows = [
    { label: 'Original file name', value: originalFilename },
    { label: 'Detected type', value: typeMeta.label },
    { label: 'Stored file name', value: storedFilename ?? '—' },
    { label: 'File size', value: formatBytes(fileSize) },
    { label: 'Server message', value: uploadResult.message ?? '—' },
  ]

  const handleDownload = async () => {
    if (!excelResult?.processed_filename) return
    setDownloading(true)
    try {
      await downloadProcessedExcel(excelResult.processed_filename)
    } catch (err) {
      setExcelError(apiErrorMessage(err, 'Download failed.'))
    } finally {
      setDownloading(false)
    }
  }

  let subtitle = 'Your file was saved.'
  if (isExcel) subtitle = 'Processing your Excel file (adds a column after Entry).'
  if (isPdf) subtitle = 'Validating PDF against required headings, questions, and answers.'
  if (docType === 'word') subtitle = 'Word validation will be added in the next phase.'

  return (
    <Stack spacing={3}>
      <Box textAlign="center">
        <CheckCircleOutlinedIcon sx={{ fontSize: 56, color: 'success.main', mb: 1 }} />
        <Typography variant="h4" component="h1" gutterBottom>
          Upload successful
        </Typography>
        <Typography color="text.secondary">{subtitle}</Typography>
      </Box>

      <Card elevation={2}>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Upload details</Typography>
            <Chip label={typeMeta.label} color={typeMeta.color} size="small" />
          </Stack>
          <Divider sx={{ mb: 2 }} />
          <TableContainer>
            <Table size="small">
              <TableBody>
                {uploadRows.map((row) => (
                  <TableRow key={row.label}>
                    <TableCell component="th" scope="row" sx={{ fontWeight: 600, width: '40%' }}>
                      {row.label}
                    </TableCell>
                    <TableCell sx={{ wordBreak: 'break-word' }}>{row.value}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {isExcel && (
        <ExcelProcessCard
          excelStatus={excelStatus}
          excelError={excelError}
          excelResult={excelResult}
          downloading={downloading}
          onRetry={() => {
            setExcelStatus('idle')
            setExcelResult(null)
          }}
          onDownload={handleDownload}
        />
      )}

      {isPdf && (
        <PdfValidationCard
          pdfStatus={pdfStatus}
          pdfError={pdfError}
          pdfResult={pdfResult}
          onRetry={() => {
            setPdfStatus('idle')
            setPdfResult(null)
          }}
        />
      )}

      {docType === 'word' && (
        <Alert severity="info">Word validation API coming soon.</Alert>
      )}

      <NavButtons navigate={navigate} />
    </Stack>
  )
}

function initialProcessState(docType) {
  if (docType === 'excel' || docType === 'pdf') {
    return { status: 'pending', result: null, error: '' }
  }
  return { status: 'skipped', result: null, error: '' }
}

function ProcessStatusCell({ status, pdfResult }) {
  if (status === 'processing') return <CircularProgress size={20} />
  if (status === 'pending') return <Chip label="Queued" size="small" variant="outlined" />
  if (status === 'skipped') return <Chip label="N/A" size="small" variant="outlined" />
  if (status === 'error') return <Chip label="Error" color="error" size="small" />
  if (status === 'done' && pdfResult?.status) {
    return (
      <Chip
        label={pdfResult.status}
        color={pdfResult.status === 'PASS' ? 'success' : 'error'}
        size="small"
      />
    )
  }
  if (status === 'done') return <Chip label="Done" color="success" size="small" />
  return null
}

function MultiResultView({ uploads, navigate }) {
  const [items, setItems] = useState(() =>
    uploads.map((u, index) => {
      const docType = u.uploadResult?.data?.document_type ?? 'unknown'
      return {
        id: `${index}-${u.originalFilename}`,
        ...u,
        docType,
        excel: initialProcessState(docType === 'excel' ? 'excel' : 'other'),
        pdf: initialProcessState(docType === 'pdf' ? 'pdf' : 'other'),
      }
    }),
  )

  useEffect(() => {
    let cancelled = false

    async function runQueue() {
      for (let i = 0; i < uploads.length; i += 1) {
        const upload = uploads[i]
        const docType = upload.uploadResult?.data?.document_type
        const stored = upload.uploadResult?.data?.filename
        if (!stored) continue

        if (docType === 'excel') {
          setItems((prev) =>
            prev.map((row, idx) =>
              idx === i ? { ...row, excel: { ...row.excel, status: 'processing' } } : row,
            ),
          )
          try {
            const result = await processExcel(stored)
            if (cancelled) return
            setItems((prev) =>
              prev.map((row, idx) =>
                idx === i
                  ? { ...row, excel: { status: 'done', result, error: '' } }
                  : row,
              ),
            )
          } catch (err) {
            if (cancelled) return
            setItems((prev) =>
              prev.map((row, idx) =>
                idx === i
                  ? {
                      ...row,
                      excel: {
                        status: 'error',
                        result: null,
                        error: apiErrorMessage(err, 'Excel failed.'),
                      },
                    }
                  : row,
              ),
            )
          }
        }

        if (docType === 'pdf') {
          setItems((prev) =>
            prev.map((row, idx) =>
              idx === i ? { ...row, pdf: { ...row.pdf, status: 'processing' } } : row,
            ),
          )
          try {
            const result = await processPdf(stored)
            if (cancelled) return
            setItems((prev) =>
              prev.map((row, idx) =>
                idx === i ? { ...row, pdf: { status: 'done', result, error: '' } } : row,
              ),
            )
          } catch (err) {
            if (cancelled) return
            setItems((prev) =>
              prev.map((row, idx) =>
                idx === i
                  ? {
                      ...row,
                      pdf: {
                        status: 'error',
                        result: null,
                        error: apiErrorMessage(err, 'PDF validation failed.'),
                      },
                    }
                  : row,
              ),
            )
          }
        }
      }
    }

    runQueue()
    return () => {
      cancelled = true
    }
  }, [uploads])

  const retryExcel = async (index) => {
    const stored = items[index].uploadResult?.data?.filename
    if (!stored) return
    setItems((prev) =>
      prev.map((row, idx) =>
        idx === index ? { ...row, excel: { status: 'processing', result: null, error: '' } } : row,
      ),
    )
    try {
      const result = await processExcel(stored)
      setItems((prev) =>
        prev.map((row, idx) =>
          idx === index ? { ...row, excel: { status: 'done', result, error: '' } } : row,
        ),
      )
    } catch (err) {
      setItems((prev) =>
        prev.map((row, idx) =>
          idx === index
            ? {
                ...row,
                excel: { status: 'error', result: null, error: apiErrorMessage(err, 'Failed.') },
              }
            : row,
        ),
      )
    }
  }

  const retryPdf = async (index) => {
    const stored = items[index].uploadResult?.data?.filename
    if (!stored) return
    setItems((prev) =>
      prev.map((row, idx) =>
        idx === index ? { ...row, pdf: { status: 'processing', result: null, error: '' } } : row,
      ),
    )
    try {
      const result = await processPdf(stored)
      setItems((prev) =>
        prev.map((row, idx) =>
          idx === index ? { ...row, pdf: { status: 'done', result, error: '' } } : row,
        ),
      )
    } catch (err) {
      setItems((prev) =>
        prev.map((row, idx) =>
          idx === index
            ? {
                ...row,
                pdf: { status: 'error', result: null, error: apiErrorMessage(err, 'Failed.') },
              }
            : row,
        ),
      )
    }
  }

  return (
    <Stack spacing={3}>
      <Box textAlign="center">
        <CheckCircleOutlinedIcon sx={{ fontSize: 56, color: 'success.main', mb: 1 }} />
        <Typography variant="h4" component="h1" gutterBottom>
          {uploads.length} files uploaded
        </Typography>
        <Typography color="text.secondary">
          Excel and PDF files are processed automatically after upload.
        </Typography>
      </Box>

      <Card elevation={2}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Upload summary
          </Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>File</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Size</TableCell>
                  <TableCell>Result</TableCell>
                  <TableCell align="right">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((item, index) => {
                  const typeMeta = TYPE_LABELS[item.docType] ?? {
                    label: item.docType,
                    color: 'default',
                  }
                  const showPdfResult = item.docType === 'pdf'
                  const showExcelResult = item.docType === 'excel'
                  const processStatus = showPdfResult ? item.pdf.status : item.excel.status
                  const processResult = showPdfResult ? item.pdf.result : item.excel.result

                  return (
                    <TableRow key={item.id}>
                      <TableCell sx={{ wordBreak: 'break-word', maxWidth: 220 }}>
                        {item.originalFilename}
                      </TableCell>
                      <TableCell>
                        <Chip label={typeMeta.label} color={typeMeta.color} size="small" />
                      </TableCell>
                      <TableCell>{formatBytes(item.fileSize)}</TableCell>
                      <TableCell>
                        <ProcessStatusCell status={processStatus} pdfResult={processResult} />
                      </TableCell>
                      <TableCell align="right">
                        {showExcelResult &&
                          item.excel.status === 'done' &&
                          item.excel.result?.processed_filename && (
                            <Button
                              size="small"
                              startIcon={<DownloadIcon />}
                              onClick={() =>
                                downloadProcessedExcel(item.excel.result.processed_filename)
                              }
                            >
                              Download
                            </Button>
                          )}
                        {showExcelResult && item.excel.status === 'error' && (
                          <Button size="small" onClick={() => retryExcel(index)}>
                            Retry
                          </Button>
                        )}
                        {showPdfResult && item.pdf.status === 'error' && (
                          <Button size="small" onClick={() => retryPdf(index)}>
                            Retry
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>

          {items.some((i) => i.pdf.status === 'done' && i.pdf.result?.status === 'FAIL') && (
            <Stack spacing={2} sx={{ mt: 2 }}>
              {items
                .filter((i) => i.pdf.status === 'done' && i.pdf.result?.status === 'FAIL')
                .map((i) => (
                  <Alert key={`pdf-fail-${i.id}`} severity="warning">
                    <Typography variant="subtitle2" gutterBottom>
                      {i.originalFilename} — validation FAIL
                    </Typography>
                    {!!i.pdf.result.missing_headings?.length && (
                      <Typography variant="body2">
                        Missing headings: {i.pdf.result.missing_headings.join(', ')}
                      </Typography>
                    )}
                    {!!i.pdf.result.missing_questions?.length && (
                      <Typography variant="body2">
                        Missing questions: {i.pdf.result.missing_questions.join(', ')}
                      </Typography>
                    )}
                    {!!i.pdf.result.missing_answers?.length && (
                      <Typography variant="body2">
                        Missing answers: {i.pdf.result.missing_answers.join(', ')}
                      </Typography>
                    )}
                  </Alert>
                ))}
            </Stack>
          )}

          {items.some((i) => i.excel.error || i.pdf.error) && (
            <Stack spacing={1} sx={{ mt: 2 }}>
              {items
                .filter((i) => i.excel.error || i.pdf.error)
                .map((i) => (
                  <Alert key={`err-${i.id}`} severity="error">
                    {i.originalFilename}: {i.excel.error || i.pdf.error}
                  </Alert>
                ))}
            </Stack>
          )}
        </CardContent>
      </Card>

      <NavButtons navigate={navigate} />
    </Stack>
  )
}

export default function ResultPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const state = location.state || {}

  const mode = state.mode ?? (state.uploadResult ? 'single' : null)

  if (mode === 'multi' && state.uploads?.length) {
    return <MultiResultView uploads={state.uploads} navigate={navigate} />
  }

  if (mode === 'single' && state.originalFilename && state.uploadResult) {
    return (
      <SingleResultView
        originalFilename={state.originalFilename}
        uploadResult={state.uploadResult}
        fileSize={state.fileSize}
        navigate={navigate}
      />
    )
  }

  return <Navigate to="/" replace />
}
