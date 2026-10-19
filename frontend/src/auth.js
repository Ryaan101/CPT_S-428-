// Shared login state (moved out of App.vue so every page can use it).
import { reactive } from 'vue'
import { login as apiLogin, getMe, logout as apiLogout } from './api.js'

const TOKEN_KEY = 'wemail.token'

function loadToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY) || ''
  } catch (_) {
    return ''
  }
}
function saveToken(t) {
  try {
    if (t) sessionStorage.setItem(TOKEN_KEY, t)
    else sessionStorage.removeItem(TOKEN_KEY)
  } catch (_) {
    /* storage may be unavailable; session still works in-memory */
  }
}

export const auth = reactive({
  token: loadToken(),
  account: null, // { user, profile, inbox_path }
  ready: false, // true once the stored token has been checked
})

export async function restoreSession() {
  if (auth.token) {
    try {
      auth.account = await getMe(auth.token)
    } catch (_) {
      // token invalid/expired/revoked: drop it and show the login form
      auth.token = ''
      auth.account = null
      saveToken('')
    }
  }
  auth.ready = true
}

export async function signIn(email, password) {
  const data = await apiLogin(email, password)
  auth.token = data.access_token
  saveToken(auth.token)
  auth.account = await getMe(auth.token)
}

export async function signOut() {
  await apiLogout(auth.token)
  auth.token = ''
  auth.account = null
  saveToken('')
}
