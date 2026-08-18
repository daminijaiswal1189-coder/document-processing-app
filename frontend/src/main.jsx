/** Vite entry: load API config (desktop), then mount React app with MUI CssBaseline. */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { CssBaseline } from '@mui/material'
import { loadApiConfig } from './utils/apiConfig'
import { refreshApiBaseUrl } from './utils/constants'

async function bootstrap() {
  await loadApiConfig()
  refreshApiBaseUrl()

  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <CssBaseline />
      <App />
    </StrictMode>,
  )
}

bootstrap()
