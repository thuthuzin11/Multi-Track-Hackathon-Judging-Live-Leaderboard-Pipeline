// In local dev this stays '/api' and the Vite dev-server proxy forwards it
// to the backend (see vite.config.js). For a real deployment where the
// frontend and backend live on different domains, set VITE_API_URL to
// the backend's public URL at build time.
const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

const TOKEN_KEY = 'auth_token'
const ROLE_KEY = 'auth_role'
const PROFILE_KEY = 'auth_profile'

export function getSession() {
  const token = localStorage.getItem(TOKEN_KEY)
  const role = localStorage.getItem(ROLE_KEY)
  const rawProfile = localStorage.getItem(PROFILE_KEY)
  if (!token || !role || !rawProfile) return null
  try {
    return { token, role, profile: JSON.parse(rawProfile) }
  } catch {
    return null
  }
}

function setSession(token, role, profile) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(ROLE_KEY, role)
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profile))
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
  localStorage.removeItem(PROFILE_KEY)
}

async function request(path, options = {}) {
  const session = getSession()
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  if (session?.token) headers['Authorization'] = `Bearer ${session.token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch (_) {}
    if (res.status === 401) clearSession()
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // ---- auth / session ----
  viewerSignup: async (email, name) => {
    const data = await request('/auth/viewer/signup', {
      method: 'POST',
      body: JSON.stringify({ email, name: name || undefined }),
    })
    setSession(data.access_token, data.role, data.profile)
    return data
  },
  judgeLogin: async (username, password) => {
    const data = await request('/auth/judge/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    setSession(data.access_token, data.role, data.profile)
    return data
  },
  adminLogin: async (username, password) => {
    const data = await request('/auth/admin/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    setSession(data.access_token, data.role, data.profile)
    return data
  },
  me: () => request('/auth/me'),
  logout: () => clearSession(),

  // ---- catalog (read-only, any signed-in role) ----
  getEvents: () => request('/catalog/events'),
  getTracks: (eventId) => request(`/catalog/tracks${eventId ? `?event_id=${eventId}` : ''}`),
  getTeams: (trackId) => request(`/catalog/teams${trackId ? `?track_id=${trackId}` : ''}`),

  // ---- admin CRUD (admin-only) ----
  createEvent: (payload) => request('/admin/events', { method: 'POST', body: JSON.stringify(payload) }),
  updateEvent: (id, payload) => request(`/admin/events/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteEvent: (id) => request(`/admin/events/${id}`, { method: 'DELETE' }),

  createTrack: (name, event_id) => request('/admin/tracks', { method: 'POST', body: JSON.stringify({ name, event_id }) }),
  updateTrack: (id, payload) => request(`/admin/tracks/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteTrack: (id) => request(`/admin/tracks/${id}`, { method: 'DELETE' }),

  createTeam: (name, track_id) => request('/admin/teams', { method: 'POST', body: JSON.stringify({ name, track_id }) }),
  updateTeam: (id, payload) => request(`/admin/teams/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteTeam: (id) => request(`/admin/teams/${id}`, { method: 'DELETE' }),

  createJudge: (payload) => request('/admin/judges', { method: 'POST', body: JSON.stringify(payload) }),
  updateJudge: (id, payload) => request(`/admin/judges/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteJudge: (id) => request(`/admin/judges/${id}`, { method: 'DELETE' }),

  getAdminEvents: () => request('/admin/events'),
  getAdminTracks: () => request('/admin/tracks'),
  getAdminTeams: () => request('/admin/teams'),
  getAdminJudges: () => request('/admin/judges'),
  getResults: () => request('/admin/results'),

  // ---- scores (judge, authenticated) ----
  submitScore: (payload) => request('/scores', { method: 'POST', body: JSON.stringify(payload) }),
  getMyScores: () => request('/scores/mine'),

  // ---- leaderboard (any signed-in role) ----
  getGlobalLeaderboard: () => request('/leaderboard'),
  getTrackLeaderboard: (trackId) => request(`/leaderboard/track/${trackId}`),
}
