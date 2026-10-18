<script setup>
import { ref, onMounted } from 'vue'
import { getHealth } from './api.js'

// Landing/login page for the scaffold (issue #1). The form renders but is not
// wired to authentication yet — that is issue #2. The backend health badge
// proves the frontend can reach the API (issue #1 acceptance).
const backend = ref({ state: 'checking', detail: '' })

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

      <form class="login" @submit.prevent>
        <label>
          Email
          <input type="email" placeholder="you@wemail.com" autocomplete="username" />
        </label>
        <label>
          Password
          <input type="password" autocomplete="current-password" />
        </label>
        <button type="submit" disabled>Log in</button>
        <p class="note">Authentication is implemented in issue #2.</p>
      </form>

      <p class="status" :class="backend.state">
        backend: {{ backend.state }}<span v-if="backend.detail"> — {{ backend.detail }}</span>
      </p>
    </section>
  </main>
</template>
