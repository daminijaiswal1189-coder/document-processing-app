/** MUI theme shared by App (palette, typography, component defaults). */
import { createTheme } from '@mui/material/styles'

export const appTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1565c0',
      dark: '#0d47a1',
      light: '#42a5f5',
    },
    secondary: {
      main: '#00897b',
    },
    background: {
      default: '#f0f4f8',
      paper: '#ffffff',
    },
  },
  shape: {
    borderRadius: 12,
  },
  typography: {
    fontFamily: '"Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    h4: { fontWeight: 700, letterSpacing: '-0.02em' },
    h5: { fontWeight: 600 },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundImage: 'linear-gradient(90deg, #0d47a1 0%, #1565c0 50%, #00897b 100%)',
        },
      },
    },
  },
})
