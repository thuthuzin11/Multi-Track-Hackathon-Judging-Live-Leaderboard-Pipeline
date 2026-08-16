import React, { useEffect, useState } from 'react'
import { toLocalString, toLocalDate } from '../datetime.js'
import { formatDuration } from '../eventUtils.js'

const STATUS_LABEL = { upcoming: 'Upcoming', ongoing: 'Live', finished: 'Finished' }

export default function EventStatusBanner({ event }) {
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  if (!event) {
    return (
      <div className="event-banner event-banner-empty">
        <span>No event has been created yet.</span>
      </div>
    )
  }

  const start = toLocalDate(event.start_date)
  const end = toLocalDate(event.end_date)

  let countdownLabel = null
  if (event.status === 'upcoming' && start) {
    countdownLabel = `Starts in ${formatDuration(start.getTime() - now)}`
  } else if (event.status === 'ongoing' && end) {
    countdownLabel = `Ends in ${formatDuration(end.getTime() - now)}`
  } else if (event.status === 'ongoing' && !end) {
    countdownLabel = 'No end time set'
  } else if (event.status === 'finished' && end) {
    countdownLabel = `Ended ${formatDuration(now - end.getTime())} ago`
  }

  return (
    <div className={`event-banner event-banner-${event.status}`}>
      <div className="event-banner-main">
        <div className="event-banner-title">
          <span className="event-banner-name">{event.name}</span>
          <span className={`status-badge status-${event.status}`}>{STATUS_LABEL[event.status]}</span>
        </div>
        <div className="event-banner-times">
          <span><strong>Start:</strong> {start ? toLocalString(event.start_date) : 'Not set'}</span>
          <span><strong>End:</strong> {end ? toLocalString(event.end_date) : 'Not set'}</span>
        </div>
      </div>
      {countdownLabel && (
        <div className="event-banner-countdown">
          {countdownLabel}
        </div>
      )}
    </div>
  )
}
