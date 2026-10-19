// Tiny API client for the backend. Base URL is overridable via VITE_API_BASE.
const BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// FastAPI sends `detail` as a string for most errors but as a list of objects for
// request-validation (422) errors; turn either into readable text.
function detailText(detail, status) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
  return `request failed (${status})`
}

async function parse(res) {
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(detailText(data.detail, res.status))
  return data
}

// Health check used on the landing page to prove the frontend<->backend link.
export async function getHealth() {
  return parse(await fetch(`${BASE_URL}/health`))
}

// Log in with email + password. Returns { access_token, user, inbox_path }.
export async function login(email, password) {
  return parse(
    await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
  )
}

// Current authenticated account (self-only).
export async function getMe(token) {
  return parse(await fetch(`${BASE_URL}/auth/me`, { headers: { Authorization: `Bearer ${token}` } }))
}

// Invalidate the current token server-side.
export async function logout(token) {
  try {
    await fetch(`${BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
  } catch (_) {
    // best-effort; the client clears its token regardless
  }
}

// --- Mail (issue #4). All calls are made as the logged-in user and only ever see
// that user's own mailbox; the server enforces this.
function authed(token, path, { method = 'GET', body } = {}) {
  const headers = { Authorization: `Bearer ${token}` }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  return fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(parse)
}

export const listInbox = (token) => authed(token, '/mail/inbox')
export const listSent = (token) => authed(token, '/mail/sent')
export const listContacts = (token) => authed(token, '/mail/contacts')
export const getEmail = (token, id) => authed(token, `/mail/${id}`)
export const deleteEmail = (token, id) => authed(token, `/mail/${id}`, { method: 'DELETE' })
// payload: { to, subject, body, body_html? }  (body_html is stored exactly as typed)
export const sendEmail = (token, payload) => authed(token, '/mail/send', { method: 'POST', body: payload })
// payload: { body, body_html? }  (the reply always goes to the original sender)
export const replyEmail = (token, id, payload) =>
  authed(token, `/mail/${id}/reply`, { method: 'POST', body: payload })

export { BASE_URL }
