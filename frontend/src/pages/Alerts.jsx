import React, { useEffect, useState } from 'react'
import { Trash2, Plus } from 'lucide-react'
import { getProjects, getProjectKeywords, getAlerts, createAlert, deleteAlert } from '../api/client'

const ALERT_TYPES = [
  { value: 'position_drop', label: 'Caída de posición' },
  { value: 'position_gain', label: 'Subida de posición' },
  { value: 'entered_top10', label: 'Entró en Top 10' },
  { value: 'left_top10', label: 'Salió del Top 10' },
  { value: 'entered_top3', label: 'Entró en Top 3' },
  { value: 'not_found', label: 'Keyword no encontrada' },
]

const CHANNELS = [
  { value: 'email', label: 'Email' },
  { value: 'webhook', label: 'Webhook' },
  { value: 'slack', label: 'Slack' },
]

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
  badge: (color) => ({
    display: 'inline-block', padding: '2px 8px', borderRadius: 6,
    fontSize: 12, fontWeight: 600, background: color + '22', color,
  }),
  error: { color: '#f87171', fontSize: 13, marginTop: 8 },
}

const ALERT_TYPE_LABEL = Object.fromEntries(ALERT_TYPES.map((t) => [t.value, t.label]))

export default function Alerts() {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState(null)
  const [keywords, setKeywords] = useState([])
  const [alerts, setAlerts] = useState([])
  const [error, setError] = useState(null)

  const [pkId, setPkId] = useState('')
  const [alertType, setAlertType] = useState('position_drop')
  const [threshold, setThreshold] = useState(5)
  const [channel, setChannel] = useState('email')
  const [channelValue, setChannelValue] = useState('')

  useEffect(() => {
    getProjects().then((data) => {
      setProjects(data)
      if (data.length > 0) setSelectedProject(data[0])
    })
  }, [])

  useEffect(() => {
    if (!selectedProject) return
    refresh(selectedProject.id)
    getProjectKeywords(selectedProject.id, { page_size: 100 }).then(setKeywords)
  }, [selectedProject])

  function refresh(projectId) {
    getAlerts(projectId).then(setAlerts)
  }

  function keywordLabel(pkIdValue) {
    const kw = keywords.find((k) => k.project_keyword_id === pkIdValue)
    return kw ? kw.keyword : `#${pkIdValue}`
  }

  function channelConfig() {
    if (channel === 'email') return { email: channelValue }
    if (channel === 'webhook') return { url: channelValue }
    if (channel === 'slack') return { webhook_url: channelValue }
    return {}
  }

  function channelPlaceholder() {
    if (channel === 'email') return 'destinatario@ejemplo.com'
    if (channel === 'webhook') return 'https://miapp.com/webhook'
    return 'https://hooks.slack.com/services/...'
  }

  async function handleCreate(e) {
    e.preventDefault()
    setError(null)
    if (!pkId) {
      setError('Selecciona una keyword')
      return
    }
    if (!channelValue.trim()) {
      setError('Indica el destino del canal de notificación')
      return
    }
    try {
      await createAlert(selectedProject.id, {
        project_keyword_id: Number(pkId),
        alert_type: alertType,
        threshold_positions: ['position_drop', 'position_gain'].includes(alertType) ? Number(threshold) : null,
        channel,
        channel_config: channelConfig(),
      })
      setChannelValue('')
      refresh(selectedProject.id)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDelete(alertId) {
    await deleteAlert(selectedProject.id, alertId)
    refresh(selectedProject.id)
  }

  return (
    <div>
      <h1 style={s.h1}>Alertas</h1>

      <div style={s.row}>
        <select style={s.select} value={selectedProject?.id || ''} onChange={(e) => {
          const p = projects.find((x) => x.id === Number(e.target.value))
          setSelectedProject(p)
        }}>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      <div style={s.card}>
        <div style={s.cardTitle}>Reglas activas</div>
        <table style={s.table}>
          <thead>
            <tr>
              {['Keyword', 'Tipo', 'Umbral', 'Canal', ''].map((h) => <th key={h} style={s.th}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id}>
                <td style={{ ...s.td, color: '#f1f5f9', fontWeight: 500 }}>{keywordLabel(a.project_keyword_id)}</td>
                <td style={s.td}>{ALERT_TYPE_LABEL[a.alert_type] ?? a.alert_type}</td>
                <td style={s.td}>{a.threshold_positions ?? '—'}</td>
                <td style={s.td}><span style={s.badge('#60a5fa')}>{a.channel}</span></td>
                <td style={s.td}>
                  <button style={s.iconBtn} onClick={() => handleDelete(a.id)} title="Eliminar">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {alerts.length === 0 && (
              <tr><td style={s.td} colSpan={5}>Sin alertas configuradas.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div style={s.card}>
        <div style={s.cardTitle}>Nueva alerta</div>
        <form onSubmit={handleCreate} style={{ ...s.row, marginBottom: 0 }}>
          <select style={s.select} value={pkId} onChange={(e) => setPkId(e.target.value)}>
            <option value="">Keyword…</option>
            {keywords.map((k) => (
              <option key={k.project_keyword_id} value={k.project_keyword_id}>{k.keyword}</option>
            ))}
          </select>

          <select style={s.select} value={alertType} onChange={(e) => setAlertType(e.target.value)}>
            {ALERT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>

          {['position_drop', 'position_gain'].includes(alertType) && (
            <input
              style={{ ...s.input, width: 90 }}
              type="number"
              min={1}
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              title="Umbral de posiciones"
            />
          )}

          <select style={s.select} value={channel} onChange={(e) => setChannel(e.target.value)}>
            {CHANNELS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>

          <input
            style={{ ...s.input, minWidth: 240 }}
            placeholder={channelPlaceholder()}
            value={channelValue}
            onChange={(e) => setChannelValue(e.target.value)}
          />

          <button type="submit" style={s.btn}><Plus size={14} /> Crear alerta</button>
        </form>
        {error && <p style={s.error}>{error}</p>}
      </div>
    </div>
  )
}
