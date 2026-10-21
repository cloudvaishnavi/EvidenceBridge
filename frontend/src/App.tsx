import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Claims from './pages/Claims'
import ClaimDetail from './pages/ClaimDetail'
import TrustDensity from './pages/TrustDensity'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/claims" element={<Claims />} />
          <Route path="/claims/:claimId" element={<ClaimDetail />} />
          <Route path="/trust-density" element={<TrustDensity />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
