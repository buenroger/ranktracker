const BASE = '/api'

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

// Ingesta manual
export const triggerFullIngest = () => request('/ingest/all', { method: 'POST' })
export const triggerGscProject = (id) => request(`/ingest/projects/${id}/gsc`, { method: 'POST' })
export const triggerDfsProject = (id) => request(`/ingest/projects/${id}/dataforseo`, { method: 'POST' })
