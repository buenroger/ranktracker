import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import Keywords from './pages/Keywords'
import Competitors from './pages/Competitors'
import Alerts from './pages/Alerts'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/keywords" element={<Keywords />} />
        <Route path="/competitors" element={<Competitors />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="*" element={<p style={{ color: '#94a3b8' }}>Página no encontrada</p>} />
      </Routes>
    </Layout>
  )
}
