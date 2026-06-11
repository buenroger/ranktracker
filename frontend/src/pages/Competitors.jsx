import React, { useEffect, useState } from 'react'
import { Trash2, Plus } from 'lucide-react'
import {
  getProjects, getProjectKeywords,
  getCompetitors, addCompetitor, removeCompetitor,
  getKeywordCompetitors,
} from '../api/client'

const s = {
  h1: { fontSize: 24, fontWeight: 700, color: '#f1f5f9', marginBottom: 28 },
  row: { display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap', alignItems: 'center' },
  select: {
    background: '#1e2636', color: '#e2e8f0', border: '1px solid #2d3748',
    borderRadius: 8, padding: '6px 12px', fontSize: 14,
  },
  input: {
    background: '#1e2636', color: '#e2e8f0', border: '1px solid #2d3748',
    borderRadius: 8, padding: '6px 12px', fontSize: 14,
  },
  btn: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
    background: '#1e3a5f', color: '#60a5fa', fontSize: 13, fontWeight: 600,
  },
  iconBtn: {
    background: 'transparent', border: 'none', cursor: 'pointer', color: '#f87171',
    display: 'flex', alignItems: 'center',
  },
  card: {
    background: '#161b27', border: '1px solid #1e2636', borderRadius: 12,
    padding: '20px 20px', marginBottom: 28,
  },
  cardTitle: { fontSize: 15, fontWeight: 600, color: '#f1f5f9', marginBottom: 16 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '10px 12px', fontSize: 12, color: '#64748b', borderBottom: '1px solid #1e2636', textTransform: 'uppercase', letterSpacing: '0.05em' },
  td: { padding: '11px 12px', fontSize: 14, borderBottom: '1px solid #1a2030', color: '#cbd5e1' },
  error: { color: '#f87171', fontSize: 13, marginTop: 8 },
}

export default function Competitors() {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState(null)
  const [competitors, setCompetitors] = useState([])
  const [domain, setDomain] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState(null)

  const [keywords, setKeywords] = useState([])
  const [selectedPk, setSelectedPk] = useState(null)
  const [comparison, setComparison] = useState([])

  useEffect(() => {
    getProjects().then((data) => {
      setProjects(data)
      if (data.length > 0) setSelectedProject(data[0])
    })
  }, [])

  useEffect(() => {
    if (!selectedProject) return
    refreshCompetitors(selectedProject.id)
    getProjectKeywords(selectedProject.id, { page_size: 100 }).then((kws) => {
      setKeywords(kws)
      setSelectedPk(null)
      setComparison([])
    })
  }, [selectedProject])

  useEffect(() => {
    if (!selectedProject || !selectedPk) return
    getKeywordCompetitors(selectedProject.id, selectedPk.project_keyword_id, { days: 30 })
      .then(setComparison)
  }, [selectedPk, selectedProject])

  function refreshCompetitors(projectId) {
    getCompetitors(projectId).then(setCompetitors)
  }

  async function handleAdd(e) {
    e.preventDefault()
    setError(null)
    if (!domain.trim()) return
    try {
      await addCompetitor(selectedProject.id, { domain: domain.trim(), name: name.trim() || null })
      setDomain('')
      setName('')
      refreshCompetitors(selectedProject.id)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleRemove(competitorId) {
    await removeCompetitor(selectedProject.id, competitorId)
    refreshCompetitors(selectedProject.id)
  }

  return (
    <div>
      <h1 style={s.h1}>Competidores</h1>

      <div style={s.row}>
        <select style={s.select} value={selectedProject?.id || ''} onChange={(e) => {
          const p = projects.find((x) => x.id === Number(e.target.value))
          setSelectedProject(p)
        }}>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      <div style={s.card}>
        <div style={s.cardTitle}>Dominios competidores</div>
        <table style={s.table}>
          <thead>
            <tr>
              {['Dominio', 'Nombre', ''].map((h) => <th key={h} style={s.th}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {competitors.map((c) => (
              <tr key={c.id}>
                <td style={{ ...s.td, color: '#f1f5f9', fontWeight: 500 }}>{c.domain}</td>
                <td style={s.td}>{c.name ?? '—'}</td>
                <td style={s.td}>
                  <button style={s.iconBtn} onClick={() => handleRemove(c.id)} title="Eliminar">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {competitors.length === 0 && (
              <tr><td style={s.td} colSpan={3}>Sin competidores todavía.</td></tr>
            )}
          </tbody>
        </table>

        <form onSubmit={handleAdd} style={{ ...s.row, marginTop: 16, marginBottom: 0 }}>
          <input
            style={s.input}
            placeholder="dominio.com"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
          />
          <input
            style={s.input}
            placeholder="Nombre (opcional)"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button type="submit" style={s.btn}><Plus size={14} /> Añadir competidor</button>
        </form>
        {error && <p style={s.error}>{error}</p>}
      </div>

      <div style={s.card}>
        <div style={s.cardTitle}>Comparativa por keyword (últimos 30 días)</div>
        <div style={s.row}>
          <select
            style={s.select}
            value={selectedPk?.project_keyword_id || ''}
            onChange={(e) => {
              const pk = keywords.find((k) => k.project_keyword_id === Number(e.target.value))
              setSelectedPk(pk)
            }}
          >
            <option value="">Selecciona una keyword…</option>
            {keywords.map((k) => (
              <option key={k.project_keyword_id} value={k.project_keyword_id}>{k.keyword}</option>
            ))}
          </select>
        </div>

        {selectedPk && (
          <table style={s.table}>
            <thead>
              <tr>
                {['Fecha', 'Competidor', 'Posición', 'URL'].map((h) => <th key={h} style={s.th}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {comparison.map((row, i) => (
                <tr key={i}>
                  <td style={s.td}>{row.check_date}</td>
                  <td style={{ ...s.td, color: '#f1f5f9', fontWeight: 500 }}>{row.competitor_domain}</td>
                  <td style={{ ...s.td, fontWeight: 600, color: '#60a5fa' }}>{row.position ?? '—'}</td>
                  <td style={{ ...s.td, maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.url ?? '—'}</td>
                </tr>
              ))}
              {comparison.length === 0 && (
                <tr><td style={s.td} colSpan={4}>Sin datos para esta keyword.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
