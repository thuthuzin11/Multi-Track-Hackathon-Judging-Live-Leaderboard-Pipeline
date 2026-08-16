import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'
import { getCurrentEvent } from '../eventUtils.js'
import EventStatusBanner from './EventStatusBanner.jsx'

const CRITERIA = [
  { key: 'technical', label: 'Technical Skill', weight: '40%' },
  { key: 'innovation', label: 'Innovation', weight: '30%' },
  { key: 'presentation', label: 'Presentation', weight: '20%' },
  { key: 'impact', label: 'Impact', weight: '10%' },
]

const EMPTY_SCORES = { technical: 5, innovation: 5, presentation: 5, impact: 5 }

export default function JudgeDashboard() {
  const [events, setEvents] = useState([])
  const [tracks, setTracks] = useState([])
  const [teams, setTeams] = useState([])
  const [myScores, setMyScores] = useState([])

  const [trackId, setTrackId] = useState('')
  const [teamId, setTeamId] = useState('')
  const [scores, setScores] = useState(EMPTY_SCORES)

  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)

  const currentEvent = getCurrentEvent(events)
  const eventFinished = currentEvent?.status === 'finished'

  const refreshMyScores = () => api.getMyScores().then(setMyScores).catch(() => {})

  useEffect(() => {
    api.getEvents().then(setEvents).catch(() => {})
    refreshMyScores()
  }, [])

  // Tracks are scoped to the CURRENT event only -- a track that belonged
  // to a past/finished competition never appears here, even if a judge
  // scored it before a newer event was created.
  useEffect(() => {
    if (!currentEvent) {
      setTracks([])
      return
    }
    api.getTracks(currentEvent.id).then(setTracks).catch(() => {})
  }, [currentEvent?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (trackId) {
      api.getTeams(trackId).then(setTeams).catch(() => {})
    } else {
      setTeams([])
    }
  }, [trackId])

  const currentTrackIds = useMemo(() => new Set(tracks.map((t) => t.id)), [tracks])

  const myScoreForTeam = (tid) => myScores.find((s) => String(s.team_id) === String(tid))
  const editingExisting = teamId ? myScoreForTeam(teamId) : null

  const selectTrack = (id) => {
    setTrackId(id)
    setTeamId('')
    setScores(EMPTY_SCORES)
    setStatus(null)
    setError(null)
  }

  const selectTeam = (id) => {
    setTeamId(id)
    const existing = myScoreForTeam(id)
    setScores(existing ? {
      technical: existing.technical,
      innovation: existing.innovation,
      presentation: existing.presentation,
      impact: existing.impact,
    } : EMPTY_SCORES)
    setStatus(null)
    setError(null)
  }

  const jumpToTeam = (score) => {
    selectTrack(String(score.track_id))
    api.getTeams(score.track_id).then((t) => {
      setTeams(t)
      selectTeam(String(score.team_id))
    }).catch(() => {})
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setStatus(null)
    setError(null)
    if (!trackId || !teamId) {
      setError('Please select a track and team.')
      return
    }
    try {
      const res = await api.submitScore({
        team_id: Number(teamId),
        track_id: Number(trackId),
        ...scores,
      })
      setStatus(editingExisting ? '✓ Score updated.' : `✓ ${res.message}`)
      refreshMyScores()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <EventStatusBanner event={currentEvent} />

      <div className="grid-2col" style={{ marginTop: 20 }}>
        <div className="panel">
          <h2>Submit a Score</h2>

          {!currentEvent && (
            <p className="subtitle">No event has been created yet — check back once your organizer sets one up.</p>
          )}

          {currentEvent && eventFinished && (
            <p className="event-status-note event-status-finished">
              🔒 <strong>{currentEvent.name}</strong> has ended — scoring is closed. You can still review your past scores on the right.
            </p>
          )}

          {currentEvent && !eventFinished && (
            <>
              <p className="subtitle">Pick a track and team. Re-selecting a team you've already scored loads your previous scores so you can edit them.</p>

              <form onSubmit={handleSubmit} className="form">
                <label>
                  Track
                  <select value={trackId} onChange={(e) => selectTrack(e.target.value)}>
                    <option value="">-- select track --</option>
                    {tracks.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </label>

                <label>
                  Team
                  <select value={teamId} onChange={(e) => selectTeam(e.target.value)} disabled={!trackId}>
                    <option value="">-- select team --</option>
                    {teams.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </label>

                {editingExisting && (
                  <p className="edit-note">✏️ You already scored this team — editing will overwrite your previous scores (it won't count twice).</p>
                )}

                <div className="criteria-grid">
                  {CRITERIA.map((c) => (
                    <div key={c.key} className="criterion">
                      <div className="criterion-label">
                        <span>{c.label}</span>
                        <span className="weight">{c.weight}</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="10"
                        step="0.5"
                        value={scores[c.key]}
                        onChange={(e) => setScores((s) => ({ ...s, [c.key]: Number(e.target.value) }))}
                      />
                      <span className="criterion-value">{scores[c.key]}</span>
                    </div>
                  ))}
                </div>

                <button type="submit" className="primary" disabled={!teamId}>
                  {editingExisting ? 'Update Score' : 'Submit Score'}
                </button>

                {status && <p className="success">{status}</p>}
                {error && <p className="error">{error}</p>}
              </form>
            </>
          )}
        </div>

        <div className="panel">
          <h2>My Submitted Scores</h2>
          <p className="subtitle">{myScores.length} score{myScores.length === 1 ? '' : 's'} submitted so far.</p>
          <div className="my-scores-list">
            {myScores.map((s) => {
              const isCurrent = currentTrackIds.has(s.track_id)
              const canEdit = isCurrent && s.event_status !== 'finished'
              return (
                <div key={s.id} className="my-score-card">
                  <div className="my-score-head">
                    <div>
                      <strong>{s.team_name}</strong>
                      <span className="my-score-track">{s.track_name}</span>
                    </div>
                    <span className="my-score-final">{s.weighted_score.toFixed(2)}</span>
                  </div>
                  <div className="my-score-breakdown">
                    T {s.technical} · I {s.innovation} · P {s.presentation} · Im {s.impact}
                  </div>
                  <button className="small" onClick={() => jumpToTeam(s)} disabled={!canEdit}>
                    {!isCurrent ? 'Past event' : s.event_status === 'finished' ? 'Event ended' : 'Edit'}
                  </button>
                </div>
              )
            })}
            {myScores.length === 0 && <p className="empty">You haven't submitted any scores yet.</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
