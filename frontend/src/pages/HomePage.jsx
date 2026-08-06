/**
 * Home page: ingest documents before processing.
 *
 * Flow:
 *   1. User chooses upload file(s) OR server path.
 *   2. POST /upload or POST /upload/path stores file in backend storage.
 *   3. Navigate to /result with uploadResult; ResultPage calls /process/* by type.
 */
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
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import FolderOpenIcon from '@mui/icons-material/FolderOpen'
import VerifiedUserOutlinedIcon from '@mui/icons-material/VerifiedUserOutlined'
import LooksOneIcon from '@mui/icons-material/LooksOne'
import LibraryBooksOutlinedIcon from '@mui/icons-material/LibraryBooksOutlined'
import FileDropZone from '../components/FileDropZone'
import { uploadDocument, uploadDocuments, registerDocumentPath } from '../services/uploadApi'
import {
  ALLOWED_EXTENSIONS,
  isAllowedExtension,
  MAX_MULTI_UPLOAD,
} from '../utils/constants'

/**
 * Landing page with file drop zone, server path input, and upload actions.
 */
export default function HomePage() {
  const navigate = useNavigate()
  const [uploadMode, setUploadMode] = useState('single')
  const [inputMode, setInputMode] = useState('file')
  const [localPath, setLocalPath] = useState('')
  const [files, setFiles] = useState([])
  const [status, setStatus] = useState('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [uploadProgress, setUploadProgress] = useState(null)

  const uploading = status === 'uploading'
  const multiple = uploadMode === 'multi'

  const handleModeChange = (_event, next) => {
    if (next === null) return
    setUploadMode(next)
    setFiles([])
    setLocalPath('')
    setStatus('idle')
    setErrorMessage('')
    setUploadProgress(null)
  }

  const handleInputModeChange = (_event, next) => {
    if (next === null) return
    setInputMode(next)
    setFiles([])
    setLocalPath('')
    setErrorMessage('')
  }

  const validateFiles = () => {
    if (inputMode === 'path') {
      if (!localPath.trim()) {
        return 'Enter a file path on the server.'
      }
      const name = localPath.trim().split(/[/\\]/).pop() ?? ''
      if (!isAllowedExtension(name)) {
        return `Invalid type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`
      }
      return null
    }
    if (files.length === 0) {
      return 'Please choose at least one file.'
    }
    if (!multiple && files.length > 1) {
      return 'Single mode allows only one file.'
    }
    if (multiple && files.length > MAX_MULTI_UPLOAD) {
      return `You can upload up to ${MAX_MULTI_UPLOAD} files at once.`
    }
    const invalid = files.find((f) => !isAllowedExtension(f.name))
    if (invalid) {
      return `Invalid type: ${invalid.name}. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`
    }
    return null
  }

  const handleUpload = async () => {
    const validationError = validateFiles()
    if (validationError) {
      setStatus('error')
      setErrorMessage(validationError)
      return
    }

    setStatus('uploading')
    setErrorMessage('')
    setUploadProgress(null)

    try {
      if (inputMode === 'path') {
        const result = await registerDocumentPath(localPath)
        const displayName =
          result.data?.source_path?.split(/[/\\]/).pop() ?? localPath.trim()
        navigate('/result', {
          state: {
            mode: 'single',
            originalFilename: displayName,
            uploadResult: result,
            fileSize: null,
            sourcePath: result.data?.source_path ?? localPath.trim(),
          },
        })
        return
      }

      if (multiple) {
        const uploads = await uploadDocuments(files, (p) => setUploadProgress(p))
        navigate('/result', { state: { mode: 'multi', uploads } })
      } else {
        const result = await uploadDocument(files[0])
        navigate('/result', {
          state: {
            mode: 'single',
            originalFilename: files[0].name,
            uploadResult: result,
            fileSize: files[0].size,
          },
        })
      }
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

  return (
    <Stack spacing={3}>
      <Box textAlign="center">
        <Typography variant="overline" color="primary" fontWeight={700}>
          Proof of concept
        </Typography>
        <Typography variant="h4" component="h1" gutterBottom>
          Upload & validate documents
        </Typography>
        <Typography variant="body1" color="text.secondary" maxWidth={560} mx="auto">
          Upload one or many Excel, Word, or PDF files. The app detects each type and
          processes Excel files automatically.
        </Typography>
      </Box>

      <Card elevation={2}>
        <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
          <Stack spacing={3}>
            <Stack alignItems="center" spacing={1}>
              <ToggleButtonGroup
                exclusive
                value={inputMode}
                onChange={handleInputModeChange}
                size="small"
                color="primary"
                disabled={uploading}
              >
                <ToggleButton value="file">
                  <CloudUploadIcon sx={{ mr: 0.5 }} fontSize="small" />
                  Upload file
                </ToggleButton>
                <ToggleButton value="path">
                  <FolderOpenIcon sx={{ mr: 0.5 }} fontSize="small" />
                  Server path
                </ToggleButton>
              </ToggleButtonGroup>

              {inputMode === 'file' && (
                <ToggleButtonGroup
                  exclusive
                  value={uploadMode}
                  onChange={handleModeChange}
                  size="small"
                  color="primary"
                  disabled={uploading}
                >
                  <ToggleButton value="single">
                    <LooksOneIcon sx={{ mr: 0.5 }} fontSize="small" />
                    Single file
                  </ToggleButton>
                  <ToggleButton value="multi">
                    <LibraryBooksOutlinedIcon sx={{ mr: 0.5 }} fontSize="small" />
                    Multiple files
                  </ToggleButton>
                </ToggleButtonGroup>
              )}

              <Stack direction="row" spacing={1} alignItems="center">
                <VerifiedUserOutlinedIcon color="action" fontSize="small" />
                <Typography variant="subtitle2" color="text.secondary" textAlign="center">
                  {inputMode === 'path'
                    ? 'Path is read on the server: project folder, your home folder, or an absolute path'
                    : multiple
                      ? `Up to ${MAX_MULTI_UPLOAD} files · Local processing only`
                      : 'One file per upload · Local processing only'}
                </Typography>
              </Stack>
            </Stack>

            {inputMode === 'file' ? (
              <FileDropZone
                multiple={multiple}
                files={files}
                onFilesChange={setFiles}
                disabled={uploading}
              />
            ) : (
              <TextField
                label="Document path on server"
                placeholder="samples/2024helpwc 000012.xlsx"
                value={localPath}
                onChange={(e) => setLocalPath(e.target.value)}
                disabled={uploading}
                fullWidth
                helperText="Absolute path (e.g. under Documents) or relative to POC-APP. Excel (.xlsx, .xls), Word, or PDF."
              />
            )}

            {uploading && (
              <Stack spacing={1}>
                <LinearProgress />
                {uploadProgress && (
                  <Typography variant="caption" color="text.secondary" textAlign="center">
                    Uploading {uploadProgress.current} of {uploadProgress.total}:{' '}
                    {uploadProgress.fileName}
                  </Typography>
                )}
              </Stack>
            )}

            <Button
              variant="contained"
              size="large"
              fullWidth
              startIcon={inputMode === 'path' ? <FolderOpenIcon /> : <CloudUploadIcon />}
              onClick={handleUpload}
              disabled={
                uploading ||
                (inputMode === 'file' ? files.length === 0 : !localPath.trim())
              }
              sx={{ py: 1.5 }}
            >
              {uploading
                ? 'Working…'
                : inputMode === 'path'
                  ? 'Use path & continue'
                  : multiple
                    ? `Upload ${files.length} file${files.length === 1 ? '' : 's'} & continue`
                    : 'Upload & continue'}
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
