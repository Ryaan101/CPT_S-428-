// Tiny API client for the backend. Base URL is overridable via VITE_API_BASE.
const BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function parse(res) {
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `request failed (${res.status})`)
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

export { BASE_URL }
