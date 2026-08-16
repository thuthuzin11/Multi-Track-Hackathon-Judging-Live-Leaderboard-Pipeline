import React, { useState } from 'react'
import { api } from '../api.js'

const TABS = [
  { key: 'viewer', label: 'View Results', icon: '📊' },
  { key: 'judge', label: 'Judge', icon: '⚖️' },
  { key: 'admin', label: 'Admin', icon: '🛠️' },
]

export default function LandingAuth({ onAuthenticated }) {
  const [tab, setTab] = useState('viewer')

  return (
    <div className="landing">
      <div className="landing-hero">
        <div className="landing-badge">Live Distributed Judging Pipeline</div>
        <h1>Multi-Track Hackathon Judging</h1>
        <p>Real-time scores, fair rankings, and a live leaderboard — built for judges, organizers, and everyone watching.</p>
      </div>

      <div className="auth-card">
        <div className="auth-tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={tab === t.key ? 'auth-tab active' : 'auth-tab'}
              onClick={() => setTab(t.key)}
              type="button"
            >
              <span className="auth-tab-icon">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>

        <div className="auth-tab-body">
          {tab === 'viewer' && <ViewerSignupForm onAuthenticated={onAuthenticated} />}
          {tab === 'judge' && <RoleLoginForm role="judge" onAuthenticated={onAuthenticated} />}
          {tab === 'admin' && <RoleLoginForm role="admin" onAuthenticated={onAuthenticated} />}
        </div>
      </div>
    </div>
  )
}

function ViewerSignupForm({ onAuthenticated }) {
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await api.viewerSignup(email.trim(), name.trim())
      onAuthenticated(data.role, data.profile)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={submit} className="form">
      <p className="auth-blurb">
        No password needed — just sign up with your email to watch the live leaderboard as scores come in.
      </p>
      <label>
        Email
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@gmail.com"
          autoComplete="email"
          required
        />
      </label>
      <label>
        Name <span className="optional">(optional)</span>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
      </label>
      <button type="submit" className="primary" disabled={loading}>
        {loading ? 'Signing up…' : 'View Live Results'}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  )
}

function RoleLoginForm({ role, onAuthenticated }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = role === 'admin'
        ? await api.adminLogin(username.trim(), password)
        : await api.judgeLogin(username.trim(), password)
      onAuthenticated(data.role, data.profile)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={submit} className="form">
      <p className="auth-blurb">
        {role === 'admin'
          ? 'Sign in with your organizer account to manage the event.'
          : 'Sign in with the account your event admin created for you.'}
      </p>
      <label>
        Username
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          required
        />
      </label>
      <label>
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
      </label>
      <button type="submit" className="primary" disabled={loading}>
        {loading ? 'Signing in…' : 'Sign In'}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  )
}
