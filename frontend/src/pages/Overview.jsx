import React, { useEffect, useState } from 'react'
import { getProjects, getProjectSummary, getProjectKeywords, triggerFullIngest } from '../api/client'
import { TrendingUp, TrendingDown, Minus, RefreshCw } from 'lucide-react'

const s = {
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 },
  h1: { fontSize: 24, fontWeight: 700, color: '#f1f5f9' },
  btn: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
    background: '#1e3a5f', color: '#60a5fa', fontSize: 13, fontWeight: 600,
  },
  select: {
    background: '#1e2636', color: '#e2e8f0', border: '1px solid #2d3748',
    borderRadius: 8, padding: '6px 12px', fontSize: 14, marginBottom: 28,
  },
  kpis: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 16, marginBottom: 36 },
  kpi: { background: '#161b27', border: '1px solid #1e2636', borderRadius: 12, padding: '18px 20px' },
  kpiLabel: { fontSize: 12, color: '#64748b', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' },
  kpiValue: { fontSize: 28, fontWeight: 700, color: '#f1f5f9' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '10px 12px', fontSize: 12, color: '#64748b', borderBottom: '1px solid #1e2636', textTransform: 'uppercase', letterSpacing: '0.05em' },
  td: { padding: '11px 12px', fontSize: 14, borderBottom: '1px solid #1a2030', color: '#cbd5e1' },
  badge: (color) => ({
    display: 'inline-block', padding: '2px 8px', borderRadius: 6,
    fontSize: 12, fontWeight: 600, background: color + '22', color,
  }),
}

function KPI({ label, value, color = '#f1f5f9' }) {
  return (
    <div style={s.kpi}>
      <div style={s.kpiLabel}>{label}</div>
      <div style={{ ...s.kpiValue, color }}>{value ?? '—'}</div>
    </div>
  )
}

function ChangeIcon({ change }) {
  if (change === null || change === undefined) return <Minus size={14} color="#64748b" />
  if (change > 0) return <TrendingUp size={14} color="#22c55e" />
  if (change < 0) return <TrendingDown size={14} color="#ef4444" />
  return <Minus size={14} color="#64748b" />
}

export default function Overview() {
  const [projects, setProjects] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [summary, setSummary] = useState(null)
  const [keywords, setKeywords] = useState([])
  const [loading, setLoading] = useState(false)
  const [ingestStatus, setIngestStatus] = useState(null)

  useEffect(() => {
    getProjects().then((data) => {
      setProjects(data)
      if (data.length > 0) setSelectedId(data[0].id)
    })
  }, [])

  useEffect(() => {
    if (!selectedId) return
    setLoading(true)
    Promise.all([
      getProjectSummary(selectedId),
      getProjectKeywords(selectedId, { page_size: 50 }),
    ]).then(([sum, kws]) => {
      setSummary(sum)
      setKeywords(kws)
    }).finally(() => setLoading(false))
  }, [selectedId])

  async function handleIngest() {
    setIngestStatus('enviando…')
    try {
      const res = await triggerFullIngest()
      setIngestStatus(res.detail)
    } catch (e) {
      setIngestStatus('Error: ' + e.message)
    }
    setTimeout(() => setIngestStatus(null), 4000)
  }

  return (
    <div>
      <div style={s.header}>
        <h1 style={s.h1}>Overview</h1>
        <button style={s.btn} onClick={handleIngest}>
          <RefreshCw size={14} /> Ingestar ahora
        </button>
      </div>

      {ingestStatus && (
        <div style={{ background: '#1e3a5f', color: '#60a5fa', padding: '10px 16px', borderRadius: 8, marginBottom: 20, fontSize: 13 }}>
          {ingestStatus}
        </div>
      )}

      <select style={s.select} value={selectedId || ''} onChange={(e) => setSelectedId(Number(e.target.value))}>
        {projects.map((p) => <option key={p.id} value={p.id}>{p.name} — {p.domain}</option>)}
      </select>

      {loading && <p style={{ color: '#64748b' }}>Cargando…</p>}

      {summary && !loading && (
        <>
          <div style={s.kpis}>
            <KPI label="Total keywords" value={summary.total_keywords} />
            <KPI label="Top 3" value={summary.keywords_top3} color="#a78bfa" />
            <KPI label="Top 10" value={summary.keywords_top10} color="#60a5fa" />
            <KPI label="Top 100" value={summary.keywords_top100} color="#34d399" />
            <KPI label="Sin resultado" value={summary.keywords_not_found} color="#f87171" />
            <KPI label="Posición media" value={summary.avg_position} color="#fbbf24" />
          </div>

          <table style={s.table}>
            <thead>
              <tr>
                {['Keyword', 'Tag', 'Posición', 'Cambio', 'Clicks', 'Impresiones', 'CTR', 'Fuente'].map((h) => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {keywords.map((kw) => (
                <tr key={kw.project_keyword_id}>
                  <td style={{ ...s.td, color: '#f1f5f9', fontWeight: 500 }}>{kw.keyword}</td>
                  <td style={s.td}>
                    {kw.tag ? <span style={s.badge('#a78bfa')}>{kw.tag}</span> : '—'}
                  </td>
                  <td style={{ ...s.td, fontWeight: 600, color: '#60a5fa' }}>
                    {kw.current_position ?? '—'}
                  </td>
                  <td style={s.td}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <ChangeIcon change={kw.position_change} />
                      <span style={{ color: kw.position_change > 0 ? '#22c55e' : kw.position_change < 0 ? '#ef4444' : '#64748b' }}>
                        {kw.position_change !== null ? (kw.position_change > 0 ? '+' : '') + kw.position_change : '—'}
                      </span>
                    </span>
                  </td>
                  <td style={s.td}>{kw.clicks ?? '—'}</td>
                  <td style={s.td}>{kw.impressions ?? '—'}</td>
                  <td style={s.td}>{kw.ctr != null ? (kw.ctr * 100).toFixed(1) + '%' : '—'}</td>
                  <td style={s.td}>
                    <span style={s.badge(kw.source === 'gsc' ? '#34d399' : '#60a5fa')}>
                      {kw.source ?? '—'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
