import React, { useEffect, useState } from 'react'
import { api, getSession, clearSession } from './api.js'
import LandingAuth from './components/LandingAuth.jsx'
import JudgeDashboard from './components/JudgeDashboard.jsx'
import AdminDashboard from './components/AdminDashboard.jsx'
import SpectatorLeaderboard from './components/SpectatorLeaderboard.jsx'

const TABS_BY_ROLE = {
  viewer: [{ key: 'results', label: 'Live Results' }],
  judge: [
    { key: 'score', label: 'Submit Scores' },
    { key: 'results', label: 'Live Results' },
  ],
  admin: [
    { key: 'admin', label: 'Manage Event' },
    { key: 'results', label: 'Live Results' },
  ],
}

const DEFAULT_TAB = { viewer: 'results', judge: 'score', admin: 'admin' }

export default function App() {
  const [session, setSession] = useState(null)
  const [checking, setChecking] = useState(true)
  const [tab, setTab] = useState(null)

  useEffect(() => {
    const stored = getSession()
    if (!stored) {
      setChecking(false)
      return
    }
    api.me()
      .then((data) => {
        setSession({ role: data.role, profile: data.profile })
        setTab(DEFAULT_TAB[data.role])
      })
      .catch(() => clearSession())
      .finally(() => setChecking(false))
  }, [])

  const handleAuthenticated = (role, profile) => {
    setSession({ role, profile })
    setTab(DEFAULT_TAB[role])
  }

  const handleLogout = () => {
    clearSession()
    setSession(null)
    setTab(null)
  }

  if (checking) {
    return (
      <div className="app">
        <div className="boot-loader">
          <div className="spinner" />
        </div>
      </div>
    )
  }

  if (!session) {
    return (
      <div className="app">
        <LandingAuth onAuthenticated={handleAuthenticated} />
      </div>
    )
  }

  const tabs = TABS_BY_ROLE[session.role] || []
  const displayName = session.profile?.name || session.profile?.email || session.profile?.username

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="topbar-logo">🏆</span>
          <h1>Hackathon Judging</h1>
        </div>
        <nav>
          {tabs.map((t) => (
            <button
              key={t.key}
              className={tab === t.key ? 'active' : ''}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <div className="topbar-user">
          <span className={`role-pill role-${session.role}`}>{session.role}</span>
          <span className="topbar-username">{displayName}</span>
          <button className="secondary" onClick={handleLogout}>Log out</button>
        </div>
      </header>

      <main>
        {tab === 'results' && <SpectatorLeaderboard />}
        {tab === 'score' && session.role === 'judge' && <JudgeDashboard />}
        {tab === 'admin' && session.role === 'admin' && <AdminDashboard />}
      </main>
    </div>
  )
}
