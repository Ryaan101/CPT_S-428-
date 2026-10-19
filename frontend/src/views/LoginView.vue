<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getHealth } from '../api.js'
import { signIn } from '../auth.js'

const router = useRouter()

// --- backend health badge (issue #1 acceptance) ---------------------------
const backend = ref({ state: 'checking', detail: '' })

const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function onLogin() {
  error.value = ''
  busy.value = true
  try {
    await signIn(email.value.trim(), password.value)
    password.value = ''
    router.push('/inbox')
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  try {
    const data = await getHealth()
    backend.value = { state: 'ok', detail: data.service || 'connected' }
  } catch (e) {
    backend.value = { state: 'down', detail: String(e.message || e) }
  }
})
</script>

<template>
  <main class="page">
    <section class="card">
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
  </main>
</template>
