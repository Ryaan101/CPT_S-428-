<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { auth } from '../auth.js'
import { listInbox, listSent } from '../api.js'
import { formatDate } from '../format.js'

const props = defineProps({ box: { type: String, required: true } }) // 'inbox' | 'sent'

const emails = ref([])
const error = ref('')
const loading = ref(true)
let timer = null

const isInbox = computed(() => props.box === 'inbox')

async function load() {
  try {
    emails.value = await (isInbox.value ? listInbox : listSent)(auth.token)
    error.value = ''
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    loading.value = false
  }
}

function preview(e) {
  const t = (e.body || '').replace(/\s+/g, ' ').trim()
  return t.length > 90 ? t.slice(0, 90) + '…' : t
}

onMounted(() => {
  load()
  timer = setInterval(load, 5000) // so a reply from the agent shows up without a refresh
})
onBeforeUnmount(() => clearInterval(timer))
watch(() => props.box, () => {
  loading.value = true
  load()
})
</script>

<template>
  <main class="mail-main">
    <div class="row-head">
      <h2>{{ isInbox ? 'Inbox' : 'Sent' }}</h2>
      <button class="link" @click="load">Refresh</button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="loading" class="muted">Loading…</p>
    <p v-else-if="!emails.length" class="muted">No messages.</p>
    <ul v-else class="mail-list">
      <li v-for="e in emails" :key="e.id" :class="{ unread: isInbox && !e.is_read }">
        <RouterLink :to="`/mail/${e.id}`">
          <span class="who">{{ isInbox ? e.sender.email_address : e.recipient.email_address }}</span>
          <span class="subj">
            {{ e.subject || '(no subject)' }}
            <span v-if="e.is_html" class="badge">HTML</span>
            <span class="snippet"> - {{ preview(e) }}</span>
          </span>
          <span class="when">{{ formatDate(e.created_at) }}</span>
        </RouterLink>
      </li>
    </ul>
  </main>
</template>
