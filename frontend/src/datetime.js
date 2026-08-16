// The backend serializes timestamps like "2026-08-16T13:57:17.123456"
// (UTC, but with no 'Z' or +00:00 suffix). Per the JS Date spec, a
// date-time string with no timezone is parsed as LOCAL time, not UTC --
// so without this fix, every timestamp displayed here silently shifts
// by however far the viewer's timezone is from UTC (e.g. ~6.5 hours
// for Myanmar, UTC+6:30).
//
// ensureUtcIso() is the single place that correction happens: if a
// string has no timezone marker, we append 'Z' so it's parsed as UTC
// (matching how the backend actually generated it), then everything
// downstream converts to the viewer's real local time correctly.

const HAS_TZ = /(Z|[+-]\d{2}:?\d{2})$/

export function ensureUtcIso(iso) {
  if (!iso) return iso
  return HAS_TZ.test(iso) ? iso : `${iso}Z`
}

export function toLocalDate(iso) {
  return iso ? new Date(ensureUtcIso(iso)) : null
}

// Full local date + time, e.g. "8/16/2026, 2:31:00 AM" in the viewer's
// own timezone and locale.
export function toLocalString(iso) {
  const d = toLocalDate(iso)
  return d ? d.toLocaleString() : ''
}

// Time-only, e.g. "2:31:00 AM".
export function toLocalTimeString(iso) {
  const d = toLocalDate(iso)
  return d ? d.toLocaleTimeString() : ''
}

// Value for <input type="datetime-local">, which expects the viewer's
// own local wall-clock time with no timezone info ("YYYY-MM-DDTHH:mm").
// Built from local getters (not toISOString(), which is UTC) so the
// input shows the correct local time to edit.
export function toDatetimeLocalValue(iso) {
  const d = toLocalDate(iso)
  if (!d || isNaN(d)) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
