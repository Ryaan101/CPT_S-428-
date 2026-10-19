<script setup>
import { useRouter } from 'vue-router'
import { auth, signOut } from './auth.js'

const router = useRouter()

async function onLogout() {
  await signOut()
  router.push('/login')
}
</script>

<template>
  <header v-if="auth.account" class="topbar">
    <strong class="brand">wemail</strong>
    <nav>
      <RouterLink to="/inbox">Inbox</RouterLink>
      <RouterLink to="/sent">Sent</RouterLink>
      <RouterLink to="/compose">Compose</RouterLink>
    </nav>
    <span class="who">{{ auth.account.user.email_address }}</span>
    <button class="logout inline" @click="onLogout">Log out</button>
  </header>
  <RouterView />
</template>
