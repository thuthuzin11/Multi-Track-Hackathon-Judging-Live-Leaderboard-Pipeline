import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { getCurrentEvent } from '../eventUtils.js'
import EventStatusBanner from './EventStatusBanner.jsx'

const POLL_MS = 2000

export default function SpectatorLeaderboard() {
  const [events, setEvents] = useState([])
  const [tracks, setTracks] = useState([])
  const [trackId, setTrackId] = useState('') // '' = whole event, combined
  const [entries, setEntries] = useState([])
  const [lastUpdated, setLastUpdated] = useState(null)

  const currentEvent = getCurrentEvent(events)

  useEffect(() => {
    api.getEvents().then(setEvents).catch(() => {})
  }, [])

  // Tracks are scoped to the CURRENT event only -- once a new event
  // exists, older events' tracks (and their finished competitions)
  // drop out of this list automatically.
  useEffect(() => {
    if (!currentEvent) {
      setTracks([])
      return
    }
    api.getTracks(currentEvent.id).then(setTracks).catch(() => {})
    setTrackId('')
  }, [currentEvent?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let cancelled = false

    const load = () => {
      const fetcher = trackId ? api.getTrackLeaderboard(trackId) : api.getGlobalLeaderboard()
      fetcher
        .then((data) => {
          if (!cancelled) {
            setEntries(data)
            setLastUpdated(new Date())
          }
        })
        .catch(() => {})
    }

    load()
    const id = setInterval(load, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [trackId])

  return (
    <div>
      <EventStatusBanner event={currentEvent} />

      <div className="panel" style={{ marginTop: 20 }}>
        <div className="leaderboard-header">
          <h2>Live Leaderboard</h2>
          <div className="leaderboard-header-right">
            <select value={trackId} onChange={(e) => setTrackId(e.target.value)}>
              <option value="">All Tracks (this event)</option>
              {tracks.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
        </div>
        <p className="subtitle">
         "Real-time rankings updated as scores are processed."
          {lastUpdated && <span className="pill"> refreshed {lastUpdated.toLocaleTimeString()}</span>}
        </p>

        <div className="table-scroll">
          <table className="results-table leaderboard-table">
            <thead>
              <tr><th>Rank</th><th>Team</th>{!trackId && <th>Track</th>}<th>Score</th><th># Judges</th></tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.team_id} className={e.rank <= 3 ? `top-${e.rank}` : ''}>
                  <td>{e.rank <= 3 ? <span className="medal">{['🥇','🥈','🥉'][e.rank - 1]}</span> : e.rank}</td>
                  <td>{e.team_name}</td>
                  {!trackId && <td>{e.track_name}</td>}
                  <td>{e.final_score.toFixed(2)}</td>
                  <td>{e.num_scores}</td>
                </tr>
              ))}
              {entries.length === 0 && (
                <tr><td colSpan={trackId ? 4 : 5} className="empty">No scores yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
