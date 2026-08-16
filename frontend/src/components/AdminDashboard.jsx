import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import EntityManager from './EntityManager.jsx'
import EventStatusBanner from './EventStatusBanner.jsx'
import { toLocalTimeString, toLocalDate } from '../datetime.js'
import { getCurrentEvent, formatDuration } from '../eventUtils.js'

const STATUS_LABEL = { upcoming: 'Upcoming', ongoing: 'Ongoing', finished: 'Finished' }

function StatusBadge({ status }) {
  return <span className={`status-badge status-${status}`}>{STATUS_LABEL[status] || status}</span>
}

function TimeLeft({ event }) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  const end = toLocalDate(event.end_date)
  const start = toLocalDate(event.start_date)

  if (event.status === 'upcoming' && start) return <span>starts in {formatDuration(start.getTime() - now)}</span>
  if (event.status === 'ongoing' && end) return <span className="time-left-live">{formatDuration(end.getTime() - now)} left</span>
  if (event.status === 'ongoing') return <span className="muted">no end time set</span>
  if (event.status === 'finished' && end) return <span className="muted">ended {formatDuration(now - end.getTime())} ago</span>
  return <span className="muted">—</span>
}

export default function AdminDashboard() {
  const [events, setEvents] = useState([])
  const [tracks, setTracks] = useState([])
  const [teams, setTeams] = useState([])
  const [judges, setJudges] = useState([])
  const [results, setResults] = useState([])

  const refreshAll = () => {
    api.getAdminEvents().then(setEvents).catch(() => {})
    api.getAdminTracks().then(setTracks).catch(() => {})
    api.getAdminTeams().then(setTeams).catch(() => {})
    api.getAdminJudges().then(setJudges).catch(() => {})
    api.getResults().then(setResults).catch(() => {})
  }

  useEffect(() => {
    refreshAll()
    const id = setInterval(() => {
      api.getResults().then(setResults).catch(() => {})
      api.getAdminEvents().then(setEvents).catch(() => {}) // keep status badges (upcoming->ongoing->finished) fresh
    }, 5000)
    return () => clearInterval(id)
  }, [])

  const currentEvent = getCurrentEvent(events)

  const eventNameById = Object.fromEntries(events.map((e) => [e.id, e.name]))
  const eventStatusById = Object.fromEntries(events.map((e) => [e.id, e.status]))
  const trackEventStatus = Object.fromEntries(tracks.map((t) => [t.id, eventStatusById[t.event_id]]))
  const teamNameById = Object.fromEntries(teams.map((t) => [t.id, t.name]))
  const teamTrackNameById = Object.fromEntries(
    teams.map((t) => [t.id, tracks.find((tr) => tr.id === t.track_id)?.name || '—'])
  )
  const teamEventNameById = Object.fromEntries(
    teams.map((t) => {
      const track = tracks.find((tr) => tr.id === t.track_id)
      return [t.id, track ? eventNameById[track.event_id] : '—']
    })
  )

  return (
    <div>
      <EventStatusBanner event={currentEvent} />

      <div className="panel" style={{ marginTop: 20 }}>
        <h2>Admin</h2>
        <p className="subtitle">
          Create, edit and delete hackathon events, tracks, teams and judge accounts.
          
        </p>

        <EntityManager
          title="Hackathon Events"
          items={events}
          idKey="id"
          fields={[
            { key: 'name', label: 'Event Name', type: 'text' },
            { key: 'start_date', label: 'Start Time', type: 'datetime-local', dynamicMin: true },
            { key: 'end_date', label: 'End Time', type: 'datetime-local', dynamicMin: true },
          ]}
          extraColumns={[
            { label: 'Status', render: (e) => <StatusBadge status={e.status} /> },
            { label: 'Time Left', render: (e) => <TimeLeft event={e} /> },
          ]}
          onCreate={(v) => api.createEvent(v).then(refreshAll)}
          onUpdate={(id, v) => api.updateEvent(id, v).then(refreshAll)}
          onDelete={(id) => api.deleteEvent(id).then(refreshAll)}
        />

        <EntityManager
          title="Tracks"
          items={tracks}
          idKey="id"
          fields={[
            { key: 'name', label: 'Track Name', type: 'text' },
            {
              key: 'event_id',
              label: 'Event',
              type: 'select',
              numeric: true,
              options: events.map((e) => ({ value: e.id, label: e.name })),
            },
          ]}
          extraColumns={[{
            label: 'Event Status',
            render: (t) => <StatusBadge status={trackEventStatus[t.id] || 'upcoming'} />,
          }]}
          onCreate={(v) => api.createTrack(v.name, v.event_id).then(refreshAll)}
          onUpdate={(id, v) => api.updateTrack(id, v).then(refreshAll)}
          onDelete={(id) => api.deleteTrack(id).then(refreshAll)}
        />

        <EntityManager
          title="Teams"
          items={teams}
          idKey="id"
          fields={[
            { key: 'name', label: 'Team Name', type: 'text' },
            {
              key: 'track_id',
              label: 'Track',
              type: 'select',
              numeric: true,
              options: tracks.map((t) => ({ value: t.id, label: `${t.name} (${eventNameById[t.event_id] || ''})` })),
            },
          ]}
          onCreate={(v) => api.createTeam(v.name, v.track_id).then(refreshAll)}
          onUpdate={(id, v) => api.updateTeam(id, v).then(refreshAll)}
          onDelete={(id) => api.deleteTeam(id).then(refreshAll)}
        />

        <EntityManager
          title="Judges (login accounts)"
          items={judges}
          idKey="id"
          fields={[
            { key: 'name', label: 'Display Name', type: 'text' },
            { key: 'username', label: 'Username', type: 'text' },
            { key: 'password', label: 'Password', type: 'password', editPlaceholder: 'leave blank to keep current' },
          ]}
          onCreate={(v) => api.createJudge(v).then(refreshAll)}
          onUpdate={(id, v) => api.updateJudge(id, v).then(refreshAll)}
          onDelete={(id) => api.deleteJudge(id).then(refreshAll)}
        />

        <h3>Results table (PostgreSQL, authoritative — every event)</h3>
        <div className="table-scroll">
          <table className="results-table">
            <thead>
              <tr><th>Team</th><th>Event</th><th>Track</th><th>Final Score</th><th># Judges</th><th>Updated</th></tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.team_id}>
                  <td>{teamNameById[r.team_id] || r.team_id}</td>
                  <td>{teamEventNameById[r.team_id] || '—'}</td>
                  <td>{teamTrackNameById[r.team_id] || '—'}</td>
                  <td>{r.final_score.toFixed(2)}</td>
                  <td>{r.num_scores}</td>
                  <td>{toLocalTimeString(r.updated_at)}</td>
                </tr>
              ))}
              {results.length === 0 && (
                <tr><td colSpan="6" className="empty">No results yet — submit some scores.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
