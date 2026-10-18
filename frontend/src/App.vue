<script setup>
import { ref, onMounted } from 'vue'
import { getHealth, login as apiLogin, getMe, logout as apiLogout } from './api.js'

// --- backend health badge (issue #1 acceptance) ---------------------------
const backend = ref({ state: 'checking', detail: '' })

// --- auth state (issue #2) -------------------------------------------------
const TOKEN_KEY = 'wemail.token'
const token = ref('')
const account = ref(null) // { user, profile, inbox_path }
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

function loadToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch (_) {
    return ''
  }
}
function saveToken(t) {
  try {
    if (t) localStorage.setItem(TOKEN_KEY, t)
    else localStorage.removeItem(TOKEN_KEY)
  } catch (_) {
    /* storage may be unavailable; session still works in-memory */
  }
}

async function refreshAccount() {
  if (!token.value) return
  try {
    account.value = await getMe(token.value)
  } catch (_) {
    // token invalid/expired/revoked: drop it and show the login form
    token.value = ''
    account.value = null
    saveToken('')
  }
}

async function onLogin() {
  error.value = ''
  busy.value = true
  try {
    const data = await apiLogin(email.value.trim(), password.value)
    token.value = data.access_token
    saveToken(token.value)
    password.value = ''
    await refreshAccount()
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

async function onLogout() {
  await apiLogout(token.value)
  token.value = ''
  account.value = null
  saveToken('')
  email.value = ''
}

onMounted(async () => {
  try {
    const data = await getHealth()
    backend.value = { state: 'ok', detail: data.service || 'connected' }
  } catch (e) {
    backend.value = { state: 'down', detail: String(e.message || e) }
  }
  token.value = loadToken()
  await refreshAccount()
})
</script>

<template>
  <main class="page">
    <!-- Logged OUT: login form -->
    <section v-if="!account" class="card">
      <h1>wemail</h1>
      <p class="sub">Self-hosted webmail — local experiment</p>

      <form class="login" @submit.prevent="onLogin">
        <label>
          Email
          <input v-model="email" type="email" placeholder="you@wemail.com" autocomplete="username" />
        </label>
        <label>
          Password
          <input v-model="password" type="password" autocomplete="current-password" />
        </label>
        <button type="submit" :disabled="busy || !email || !password">
          {{ busy ? 'Signing in…' : 'Log in' }}
        </button>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
      </form>

      <p class="status" :class="backend.state">
        backend: {{ backend.state }}<span v-if="backend.detail"> — {{ backend.detail }}</span>
      </p>
    </section>

    <!-- Logged IN: minimal account panel (full inbox UI is issue #4) -->
    <section v-else class="card">
      <h1>wemail</h1>
      <p class="sub">Signed in</p>
      <dl class="account">
        <dt>Account</dt>
        <dd>{{ account.user.display_name }} ({{ account.user.role }})</dd>
        <dt>Email</dt>
        <dd>{{ account.user.email_address }}</dd>
        <dt>Inbox</dt>
        <dd><code>{{ account.inbox_path }}</code></dd>
      </dl>
      <p class="note">Inbox interface is implemented in issue #4.</p>
      <button class="logout" @click="onLogout">Log out</button>
      <p class="status" :class="backend.state">backend: {{ backend.state }}</p>
    </section>
  </main>
</template>
