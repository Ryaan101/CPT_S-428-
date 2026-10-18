// Tiny API client for the backend. Base URL is overridable via VITE_API_BASE.
const BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// Health check used on the landing page to prove the frontend<->backend link.
export async function getHealth() {
  const res = await fetch(`${BASE_URL}/health`)
  if (!res.ok) throw new Error(`health check failed (${res.status})`)
  return res.json()
}

export { BASE_URL }
