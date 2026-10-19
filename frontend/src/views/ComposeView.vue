<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth } from '../auth.js'
import { getEmail, listContacts, sendEmail, replyEmail } from '../api.js'

const route = useRoute()
const router = useRouter()

const replyId = computed(() => route.query.reply || '')
const contacts = ref([])
const original = ref(null)
const to = ref('')
const subject = ref('')
const format = ref('plain') // 'plain' | 'html'
const text = ref('')
const error = ref('')
const busy = ref(false)

onMounted(async () => {
  try {
    if (replyId.value) {
      original.value = await getEmail(auth.token, replyId.value)
      to.value = original.value.sender.email_address
      const s = original.value.subject || ''
      subject.value = /^re:/i.test(s) ? s : `Re: ${s}`
    } else {
      contacts.value = await listContacts(auth.token)
      if (contacts.value.length) to.value = contacts.value[0].email_address
    }
  } catch (e) {
    error.value = String(e.message || e)
  }
})

async function onSend() {
  error.value = ''
  busy.value = true
  // HTML mode sends exactly what was typed as body_html. It is not sanitized or altered.
  const content = format.value === 'html' ? { body: '', body_html: text.value } : { body: text.value }
  try {
    if (replyId.value) await replyEmail(auth.token, replyId.value, content)
    else await sendEmail(auth.token, { to: to.value, subject: subject.value, ...content })
    router.push('/sent')
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="mail-main">
    <h2>{{ replyId ? 'Reply' : 'Compose' }}</h2>
    <form class="compose" @submit.prevent="onSend">
      <label>
        To
        <select v-if="!replyId" v-model="to">
          <option v-for="c in contacts" :key="c.id" :value="c.email_address">
            {{ c.display_name }} &lt;{{ c.email_address }}&gt;
          </option>
        </select>
        <input v-else :value="to" disabled />
      </label>
      <label>
        Subject
        <input v-model="subject" maxlength="255" :disabled="!!replyId" />
      </label>
      <fieldset>
        <legend>Format</legend>
        <label class="inline"><input v-model="format" type="radio" value="plain" /> Plain text</label>
        <label class="inline"><input v-model="format" type="radio" value="html" /> HTML</label>
      </fieldset>
      <label>
        {{ format === 'html' ? 'HTML source' : 'Message' }}
        <textarea v-model="text" rows="12" :class="{ mono: format === 'html' }" required></textarea>
      </label>
      <p v-if="format === 'html'" class="note">
        Sent exactly as typed and stored unmodified, including comments and hidden elements.
      </p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button type="submit" class="primary" :disabled="busy || !text.trim() || !to">
        {{ busy ? 'Sending…' : 'Send' }}
      </button>
    </form>
  </main>
</template>
