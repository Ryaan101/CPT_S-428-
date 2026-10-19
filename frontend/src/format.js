// Timestamps from the API are naive UTC (no "Z"); add it so the browser converts to local time.
export function formatDate(iso) {
  if (!iso) return ''
  const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(iso)
  const d = new Date(hasZone ? iso : iso + 'Z')
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString()
}

// What the agent receives for an email: the raw HTML source if it is an HTML email.
export function rawSource(email) {
  return email.is_html ? email.body_html || '' : email.body || ''
}
