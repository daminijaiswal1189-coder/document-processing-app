import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from '@mui/material/styles'
import HomePage from './pages/HomePage'
import ResultPage from './pages/ResultPage'
import AppLayout from './components/AppLayout'
import { appTheme } from './theme'

export default function App() {
  return (
    <ThemeProvider theme={appTheme}>
      <Router>
        <AppLayout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/result" element={<ResultPage />} />
          </Routes>
        </AppLayout>
      </Router>
    </ThemeProvider>
  )
}
