import { useLocation, useNavigate, Navigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Typography,
} from '@mui/material'
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'

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

export default function ResultPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { originalFilename, uploadResult, fileSize } = location.state || {}

  if (!originalFilename || !uploadResult) {
    return <Navigate to="/" replace />
  }

  const docType = uploadResult.data?.document_type ?? 'unknown'
  const typeMeta = TYPE_LABELS[docType] ?? { label: docType, color: 'default' }

  const rows = [
    { label: 'Original file name', value: originalFilename },
    { label: 'Detected type', value: typeMeta.label },
    { label: 'Stored file name', value: uploadResult.data?.filename ?? '—' },
    { label: 'File size', value: formatBytes(fileSize) },
    { label: 'Server message', value: uploadResult.message ?? '—' },
  ]

  return (
    <Stack spacing={3}>
      <Box textAlign="center">
        <CheckCircleOutlinedIcon sx={{ fontSize: 56, color: 'success.main', mb: 1 }} />
        <Typography variant="h4" component="h1" gutterBottom>
          Upload successful
        </Typography>
        <Typography color="text.secondary">
          Your file was saved and is ready for the next processing step.
        </Typography>
      </Box>

      <Alert severity="success" icon={<CheckCircleOutlinedIcon fontSize="inherit" />}>
        Status: <strong>{uploadResult.status ?? 'success'}</strong>
        {' · '}
        Validation results will appear here once Word, PDF, and Excel processing are connected.
      </Alert>

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
                {rows.map((row) => (
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

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <Button
          variant="contained"
          size="large"
          startIcon={<UploadFileIcon />}
          onClick={() => navigate('/')}
          fullWidth
        >
          Upload another file
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
    </Stack>
  )
}
