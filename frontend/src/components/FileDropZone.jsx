import { useCallback, useState } from 'react'
import {
  Box,
  Chip,
  Paper,
  Stack,
  Typography,
} from '@mui/material'
import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined'
import InsertDriveFileOutlinedIcon from '@mui/icons-material/InsertDriveFileOutlined'
import PictureAsPdfOutlinedIcon from '@mui/icons-material/PictureAsPdfOutlined'
import TableChartOutlinedIcon from '@mui/icons-material/TableChartOutlined'
import ArticleOutlinedIcon from '@mui/icons-material/ArticleOutlined'
import { ALLOWED_EXTENSIONS } from '../utils/constants'

const TYPE_CHIPS = [
  { ext: '.xlsx', label: 'Excel', icon: <TableChartOutlinedIcon fontSize="small" /> },
  { ext: '.docx', label: 'Word', icon: <ArticleOutlinedIcon fontSize="small" /> },
  { ext: '.pdf', label: 'PDF', icon: <PictureAsPdfOutlinedIcon fontSize="small" /> },
]

function fileKey(file) {
  return `${file.name}-${file.size}-${file.lastModified}`
}

export default function FileDropZone({
  multiple = false,
  files = [],
  onFilesChange,
  disabled,
}) {
  const [dragOver, setDragOver] = useState(false)

  const mergeFiles = useCallback(
    (incoming) => {
      if (!incoming.length) return
      if (multiple) {
        const map = new Map(files.map((f) => [fileKey(f), f]))
        incoming.forEach((f) => map.set(fileKey(f), f))
        onFilesChange(Array.from(map.values()))
      } else {
        onFilesChange([incoming[0]])
      }
    },
    [files, multiple, onFilesChange],
  )

  const onDrop = (event) => {
    event.preventDefault()
    setDragOver(false)
    if (disabled) return
    const list = Array.from(event.dataTransfer.files ?? [])
    mergeFiles(list)
  }

  const removeFile = (key) => {
    onFilesChange(files.filter((f) => fileKey(f) !== key))
  }

  return (
    <Paper
      variant="outlined"
      onDragOver={(e) => {
        e.preventDefault()
        if (!disabled) setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      sx={{
        p: { xs: 3, sm: 4 },
        textAlign: 'center',
        borderStyle: 'dashed',
        borderWidth: 2,
        borderColor: dragOver ? 'primary.main' : 'divider',
        bgcolor: dragOver ? 'action.hover' : 'background.paper',
        transition: 'border-color 0.2s, background-color 0.2s',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.7 : 1,
      }}
      component="label"
    >
      <input
        type="file"
        hidden
        multiple={multiple}
        accept={ALLOWED_EXTENSIONS.join(',')}
        disabled={disabled}
        onChange={(e) => {
          mergeFiles(Array.from(e.target.files ?? []))
          e.target.value = ''
        }}
      />

      <Stack spacing={2} alignItems="center">
        <Box
          sx={{
            width: 72,
            height: 72,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
            opacity: 0.9,
          }}
        >
          <CloudUploadOutlinedIcon sx={{ fontSize: 36 }} />
        </Box>

        <Box>
          <Typography variant="h6" gutterBottom>
            {files.length
              ? multiple
                ? 'Add more files'
                : 'Change file'
              : multiple
                ? 'Drag & drop documents'
                : 'Drag & drop your document'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            or click to browse from your computer
          </Typography>
        </Box>

        <Stack direction="row" spacing={1} flexWrap="wrap" justifyContent="center" useFlexGap>
          {TYPE_CHIPS.map(({ ext, label, icon }) => (
            <Chip key={ext} icon={icon} label={`${label} (${ext})`} size="small" variant="outlined" />
          ))}
        </Stack>

        {files.length > 0 && (
          <Stack spacing={1} sx={{ width: '100%', maxWidth: 480 }}>
            {files.map((file) => {
              const key = fileKey(file)
              return (
                <Chip
                  key={key}
                  icon={<InsertDriveFileOutlinedIcon />}
                  label={file.name}
                  color="primary"
                  variant="filled"
                  onDelete={multiple && !disabled ? () => removeFile(key) : undefined}
                  sx={{
                    maxWidth: '100%',
                    '& .MuiChip-label': { overflow: 'hidden', textOverflow: 'ellipsis' },
                  }}
                />
              )
            })}
          </Stack>
        )}
      </Stack>
    </Paper>
  )
}
