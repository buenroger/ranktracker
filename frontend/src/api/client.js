const BASE = import.meta.env.VITE_API_URL || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || 'Error de red')
  }
  if (res.status === 204) return null
  return res.json()
}

// Projects
export const getProjects = () => request('/projects/')
export const getProject = (id) => request(`/projects/${id}`)
export const getProjectSummary = (id) => request(`/projects/${id}/summary`)
export const createProject = (body) => request('/projects/', { method: 'POST', body: JSON.stringify(body) })

// Keywords por proyecto
export const getProjectKeywords = (projectId, params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return request(`/projects/${projectId}/keywords/${qs ? '?' + qs : ''}`)
}
export const getKeywordHistory = (projectId, pkId, params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return request(`/projects/${projectId}/keywords/${pkId}/history${qs ? '?' + qs : ''}`)
}

// Global keywords
export const getKeywords = (q) => request(`/keywords/${q ? '?q=' + encodeURIComponent(q) : ''}`)
export const createKeyword = (body) => request('/keywords/', { method: 'POST', body: JSON.stringify(body) })

// Project keywords (alta/baja)
export const addProjectKeyword = (projectId, body) =>
  request(`/projects/${projectId}/keywords/`, { method: 'POST', body: JSON.stringify(body) })
export const removeProjectKeyword = (projectId, pkId) =>
  request(`/projects/${projectId}/keywords/${pkId}`, { method: 'DELETE' })
export const getKeywordCompetitors = (projectId, pkId, params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return request(`/projects/${projectId}/keywords/${pkId}/competitors${qs ? '?' + qs : ''}`)
}

// Competidores
export const getCompetitors = (projectId) => request(`/projects/${projectId}/competitors/`)
export const addCompetitor = (projectId, body) =>
  request(`/projects/${projectId}/competitors/`, { method: 'POST', body: JSON.stringify(body) })
export const removeCompetitor = (projectId, competitorId) =>
  request(`/projects/${projectId}/competitors/${competitorId}`, { method: 'DELETE' })

// Alertas
export const getAlerts = (projectId) => request(`/projects/${projectId}/alerts/`)
export const createAlert = (projectId, body) =>
  request(`/projects/${projectId}/alerts/`, { method: 'POST', body: JSON.stringify(body) })
export const deleteAlert = (projectId, alertId) =>
  request(`/projects/${projectId}/alerts/${alertId}`, { method: 'DELETE' })

// Ingesta manual
export const triggerFullIngest = () => request('/ingest/all', { method: 'POST' })
export const triggerGscProject = (id) => request(`/ingest/projects/${id}/gsc`, { method: 'POST' })
export const triggerDfsProject = (id) => request(`/ingest/projects/${id}/dataforseo`, { method: 'POST' })
