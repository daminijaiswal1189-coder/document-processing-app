import { Link as RouterLink, useLocation } from 'react-router-dom'
import {
  AppBar,
  Box,
  Container,
  Link,
  Toolbar,
  Typography,
} from '@mui/material'
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined'

export default function AppLayout({ children }) {
  const location = useLocation()
  const isHome = location.pathname === '/'

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'background.default',
      }}
    >
      <AppBar position="sticky" elevation={0}>
        <Toolbar sx={{ gap: 1.5 }}>
          <DescriptionOutlinedIcon />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 700 }}>
            DocValidate POC
          </Typography>
          {!isHome && (
            <Link
              component={RouterLink}
              to="/"
              underline="hover"
              sx={{ color: 'inherit', fontWeight: 500 }}
            >
              Home
            </Link>
          )}
        </Toolbar>
      </AppBar>

      <Box component="main" sx={{ flex: 1, py: { xs: 3, md: 5 } }}>
        <Container maxWidth="md">{children}</Container>
      </Box>

      <Box
        component="footer"
        sx={{
          py: 2,
          textAlign: 'center',
          color: 'text.secondary',
          typography: 'caption',
          borderTop: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
        }}
      >
        Document Validation & Excel Processing — Proof of Concept
      </Box>
    </Box>
  )
}
