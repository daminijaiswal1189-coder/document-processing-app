import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  LinearProgress,
  Stack,
  Typography,
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import VerifiedUserOutlinedIcon from '@mui/icons-material/VerifiedUserOutlined'
import FileDropZone from '../components/FileDropZone'
import { uploadDocument } from '../services/uploadApi'
import { ALLOWED_EXTENSIONS } from '../utils/constants'

function hasAllowedExtension(name) {
  const lower = name.toLowerCase()
  return ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))
}

export default function HomePage() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState('idle')
  const [errorMessage, setErrorMessage] = useState('')

  const uploading = status === 'uploading'

  const handleUpload = async () => {
    if (!file) {
      setStatus('error')
      setErrorMessage('Please choose a file first.')
      return
    }
    if (!hasAllowedExtension(file.name)) {
      setStatus('error')
      setErrorMessage('Only .xlsx, .docx, and .pdf are allowed.')
      return
    }

    setStatus('uploading')
    setErrorMessage('')
    try {
      const result = await uploadDocument(file)
      navigate('/result', {
        state: {
          originalFilename: file.name,
          uploadResult: result,
          fileSize: file.size,
        },
      })
    } catch (err) {
      setStatus('error')
      const detail = err.response?.data?.detail
      setErrorMessage(
        typeof detail === 'string'
          ? detail
          : 'Upload failed. Is the backend running on port 8000?',
      )
      setStatus('idle')
    }
  }

  const handleFileSelect = (selected) => {
    setFile(selected)
    setStatus('idle')
    setErrorMessage('')
  }

  return (
    <Stack spacing={3}>
      <Box textAlign="center">
        <Typography variant="overline" color="primary" fontWeight={700}>
          Proof of concept
        </Typography>
        <Typography variant="h4" component="h1" gutterBottom>
          Upload & validate documents
        </Typography>
        <Typography variant="body1" color="text.secondary" maxWidth={520} mx="auto">
          Upload a single Excel, Word, or PDF file. The app detects the type and prepares it
          for validation and processing.
        </Typography>
      </Box>

      <Card elevation={2}>
        <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
          <Stack spacing={3}>
            <Stack direction="row" spacing={1} alignItems="center" justifyContent="center">
              <VerifiedUserOutlinedIcon color="action" />
              <Typography variant="subtitle2" color="text.secondary">
                Max 1 file per upload · Local processing only
              </Typography>
            </Stack>

            <FileDropZone
              file={file}
              onFileSelect={handleFileSelect}
              disabled={uploading}
            />

            {uploading && <LinearProgress />}

            <Button
              variant="contained"
              size="large"
              fullWidth
              startIcon={<CloudUploadIcon />}
              onClick={handleUpload}
              disabled={!file || uploading}
              sx={{ py: 1.5 }}
            >
              {uploading ? 'Uploading…' : 'Upload & continue'}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {status === 'error' && errorMessage && (
        <Alert severity="error" variant="filled">
          {errorMessage}
        </Alert>
      )}
    </Stack>
  )
}
