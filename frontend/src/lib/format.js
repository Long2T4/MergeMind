// The backend stores naive UTC timestamps (datetime.utcnow) and serialises
// them without a timezone, so treat a missing offset as UTC.
export function parseApiDate(value) {
  if (!value) return null
  const text = String(value)
  const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(text)
  const date = new Date(hasZone ? text : `${text}Z`)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDateTime(value) {
  const date = parseApiDate(value)
  if (!date) return '—'
  const day = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  const time = date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  return `${day} · ${time}`
}

export function formatShortDate(value) {
  const date = value instanceof Date ? value : parseApiDate(value)
  if (!date) return '—'
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function formatLongDate(value) {
  const date = parseApiDate(value)
  if (!date) return '—'
  return date.toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

export function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`
}

export function greetingFor(date = new Date()) {
  const hour = date.getHours()
  if (hour < 12) return 'Good morning.'
  if (hour < 18) return 'Good afternoon.'
  return 'Good evening.'
}

export function countBySeverity(issues = []) {
  const counts = { high: 0, medium: 0, low: 0 }
  for (const issue of issues) {
    const severity = String(issue.severity || '').toLowerCase()
    if (severity in counts) counts[severity] += 1
  }
  return counts
}
