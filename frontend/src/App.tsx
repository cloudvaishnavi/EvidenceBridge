import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { VoiceProvider } from './context/VoiceContext'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Home from './pages/Home'
import Claims from './pages/Claims'
import ClaimDetail from './pages/ClaimDetail'
import TrustDensity from './pages/TrustDensity'
import Evaluation from './pages/Evaluation'
import CommunityStories from './pages/CommunityStories'
import Insights from './pages/Insights'
import HospitalFinder from './pages/HospitalFinder'

function RootRoute() {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) {
    return <Landing />
  }
  return <Navigate to="/audit" replace />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <VoiceProvider>
          <Routes>
            {/* Landing page at root when unauthenticated */}
            <Route path="/" element={<RootRoute />} />
            <Route path="/welcome" element={<Landing />} />

            {/* Main workspace layout */}
            <Route element={<Layout />}>
              <Route path="/audit" element={<Home />} />
              <Route path="/claims" element={<Claims />} />
              <Route path="/claims/:claimId" element={<ClaimDetail />} />
              <Route path="/trust-density" element={<TrustDensity />} />
              <Route path="/insights" element={<Insights />} />
              <Route path="/dashboard" element={<Navigate to="/insights" replace />} />
              <Route path="/hospitals" element={<HospitalFinder />} />
              <Route path="/finder" element={<Navigate to="/hospitals" replace />} />
              <Route path="/evaluation" element={<Evaluation />} />
              <Route path="/community" element={<CommunityStories />} />
              <Route path="/stories" element={<Navigate to="/community" replace />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </VoiceProvider>
      </BrowserRouter>
    </AuthProvider>
  )
}
