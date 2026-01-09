import { Routes, Route } from 'react-router-dom'
import { ModGenerationProvider } from './contexts/ModGenerationContext'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'

function App() {
  return (
    <ModGenerationProvider>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    </ModGenerationProvider>
  )
}

export default App

