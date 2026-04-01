import React, { useEffect, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { getProjects, getProjectKeywords, getKeywordHistory } from '../api/client'

const s = {
  h1: { fontSize: 24, fontWeight: 700, color: '#f1f5f9', marginBottom: 28 },
  row: { display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' },
  select: {
    background: '#1e2636', color: '#e2e8f0', border: '1px solid #2d3748',
    borderRadius: 8, padding: '6px 12px', fontSize: 14,
  },
  table: { width: '100%', borderCollapse: 'collapse', marginBottom: 40 },
  th: { textAlign: 'left', padding: '10px 12px', fontSize: 12, color: '#64748b', borderBottom: '1px solid #1e2636', textTransform: 'uppercase', letterSpacing: '0.05em' },
  td: { padding: '11px 12px', fontSize: 14, borderBottom: '1px solid #1a2030', color: '#cbd5e1', cursor: 'pointer' },
  selectedRow: { background: '#1e2d45' },
  chartBox: {
    background: '#161b27', border: '1px solid #1e2636', borderRadius: 12,
    padding: '24px 20px',
  },
  chartTitle: { fontSize: 15, fontWeight: 600, color: '#f1f5f9', marginBottom: 20 },
}

const COLORS = ['#60a5fa', '#a78bfa', '#34d399', '#fbbf24', '#f87171']

const CUSTOM_TOOLTIP = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#0f1117', border: '1px solid #1e2636', borderRadius: 8, padding: '10px 14px', fontSize: 13 }}>
      <p style={{ color: '#94a3b8', marginBottom: 4 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>{p.name}: <strong>{p.value ?? '—'}</strong></p>
      ))}
    </div>
  )
}

export default function Keywords() {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState(null)
  const [keywords, setKeywords] = useState([])
  const [selectedPk, setSelectedPk] = useState(null)
  const [history, setHistory] = useState([])
  const [days, setDays] = useState(30)
  const [loadingKw, setLoadingKw] = useState(false)
  const [loadingChart, setLoadingChart] = useState(false)

  useEffect(() => {
    getProjects().then((data) => {
      setProjects(data)
      if (data.length > 0) setSelectedProject(data[0])
    })
  }, [])

  useEffect(() => {
    if (!selectedProject) return
    setLoadingKw(true)
    getProjectKeywords(selectedProject.id, { page_size: 100 })
      .then(setKeywords)
      .finally(() => setLoadingKw(false))
    setSelectedPk(null)
    setHistory([])
  }, [selectedProject])

  useEffect(() => {
    if (!selectedProject || !selectedPk) return
    setLoadingChart(true)
    getKeywordHistory(selectedProject.id, selectedPk.project_keyword_id, { days })
      .then((rows) => {
        const formatted = rows.map((r) => ({
          date: r.check_date,
          posicion: r.position,
          fuente: r.source,
        }))
        setHistory(formatted)
      })
      .finally(() => setLoadingChart(false))
  }, [selectedPk, days, selectedProject])

  // Invertir eje Y: posición 1 es la mejor (arriba)
  const maxPos = Math.max(...history.map((h) => h.posicion ?? 0), 10)
  const yDomain = [1, maxPos + 2]

  return (
    <div>
      <h1 style={s.h1}>Keywords</h1>

      <div style={s.row}>
        <select style={s.select} value={selectedProject?.id || ''} onChange={(e) => {
          const p = projects.find((x) => x.id === Number(e.target.value))
          setSelectedProject(p)
        }}>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>

        <select style={s.select} value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {[7, 14, 30, 60, 90].map((d) => <option key={d} value={d}>Últimos {d} días</option>)}
        </select>
      </div>

      {loadingKw && <p style={{ color: '#64748b' }}>Cargando keywords…</p>}

      {!loadingKw && (
        <table style={s.table}>
          <thead>
            <tr>
              {['Keyword', 'Posición actual', 'Cambio', 'Tag'].map((h) => (
                <th key={h} style={s.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {keywords.map((kw) => {
              const isSelected = selectedPk?.project_keyword_id === kw.project_keyword_id
              return (
                <tr
                  key={kw.project_keyword_id}
                  style={isSelected ? s.selectedRow : {}}
                  onClick={() => setSelectedPk(kw)}
                >
                  <td style={{ ...s.td, color: isSelected ? '#60a5fa' : '#f1f5f9', fontWeight: 500 }}>
                    {kw.keyword}
                  </td>
                  <td style={{ ...s.td, fontWeight: 600 }}>{kw.current_position ?? '—'}</td>
                  <td style={{ ...s.td, color: kw.position_change > 0 ? '#22c55e' : kw.position_change < 0 ? '#ef4444' : '#64748b' }}>
                    {kw.position_change !== null ? (kw.position_change > 0 ? '+' : '') + kw.position_change : '—'}
                  </td>
                  <td style={s.td}>{kw.tag ?? '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      {selectedPk && (
        <div style={s.chartBox}>
          <div style={s.chartTitle}>
            Evolución de posición — <span style={{ color: '#60a5fa' }}>{selectedPk.keyword}</span>
          </div>
          {loadingChart && <p style={{ color: '#64748b' }}>Cargando gráfico…</p>}
          {!loadingChart && history.length === 0 && (
            <p style={{ color: '#64748b', fontSize: 14 }}>Sin datos para el período seleccionado.</p>
          )}
          {!loadingChart && history.length > 0 && (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={history} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2636" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: '#1e2636' }}
                />
                <YAxis
                  reversed
                  domain={yDomain}
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: '#1e2636' }}
                  label={{ value: 'Posición', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11, dx: -4 }}
                />
                <Tooltip content={<CUSTOM_TOOLTIP />} />
                <Legend wrapperStyle={{ fontSize: 13, color: '#94a3b8' }} />
                <Line
                  type="monotone"
                  dataKey="posicion"
                  name="Posición"
                  stroke="#60a5fa"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#60a5fa' }}
                  activeDot={{ r: 5 }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      )}
    </div>
  )
}
