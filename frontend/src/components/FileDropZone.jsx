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

const TYPE_CHIPS = [
  { ext: '.xlsx', label: 'Excel', icon: <TableChartOutlinedIcon fontSize="small" /> },
  { ext: '.docx', label: 'Word', icon: <ArticleOutlinedIcon fontSize="small" /> },
  { ext: '.pdf', label: 'PDF', icon: <PictureAsPdfOutlinedIcon fontSize="small" /> },
]

export default function FileDropZone({ file, onFileSelect, disabled }) {
  const [dragOver, setDragOver] = useState(false)

  const pickFile = useCallback(
    (selected) => {
      if (selected && !disabled) {
        onFileSelect(selected)
      }
    },
    [disabled, onFileSelect],
  )

  const onDrop = (event) => {
    event.preventDefault()
    setDragOver(false)
    if (disabled) return
    const dropped = event.dataTransfer.files?.[0]
    pickFile(dropped ?? null)
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
        accept=".xlsx,.docx,.pdf"
        disabled={disabled}
        onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
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
            {file ? 'Change file' : 'Drag & drop your document'}
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

        {file && (
          <Chip
            icon={<InsertDriveFileOutlinedIcon />}
            label={file.name}
            color="primary"
            variant="filled"
            sx={{ maxWidth: '100%', '& .MuiChip-label': { overflow: 'hidden', textOverflow: 'ellipsis' } }}
          />
        )}
      </Stack>
    </Paper>
  )
}
