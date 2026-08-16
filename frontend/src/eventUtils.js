// The "current" event is whichever one was created most recently --
// matches the backend's crud.get_current_event() (order by id desc).
// As soon as an admin creates a new event, this flips to it everywhere.
export function getCurrentEvent(events) {
  if (!events || events.length === 0) return null
  return [...events].sort((a, b) => b.id - a.id)[0]
}

// Formats a millisecond duration as "2d 3h 15m 04s" (dropping leading
// zero units), or "0s" for anything at/under zero.
export function formatDuration(ms) {
  if (ms <= 0) return '0s'
  const totalSeconds = Math.floor(ms / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  const parts = []
  if (days) parts.push(`${days}d`)
  if (days || hours) parts.push(`${hours}h`)
  if (days || hours || minutes) parts.push(`${minutes}m`)
  parts.push(`${String(seconds).padStart(2, '0')}s`)
  return parts.join(' ')
}
