<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../auth.js'
import { getEmail, deleteEmail } from '../api.js'
import { formatDate, rawSource } from '../format.js'
import HtmlViewer from '../components/HtmlViewer.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()

const email = ref(null)
const error = ref('')
const tab = ref('rendered') // 'rendered' | 'raw'

const raw = computed(() => (email.value ? rawSource(email.value) : ''))
const isMine = computed(() => email.value && email.value.recipient.id === auth.account.user.id)

onMounted(async () => {
  try {
    email.value = await getEmail(auth.token, props.id)
  } catch (e) {
    error.value = String(e.message || e)
  }
})

async function onDelete() {
  try {
    await deleteEmail(auth.token, props.id)
    router.push(isMine.value ? '/inbox' : '/sent')
  } catch (e) {
    error.value = String(e.message || e)
  }
}
</script>

<template>
  <main class="mail-main">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <article v-else-if="email">
      <div class="row-head">
        <h2>{{ email.subject || '(no subject)' }}</h2>
        <span>
          <button v-if="isMine" class="link" @click="router.push({ path: '/compose', query: { reply: email.id } })">
            Reply
          </button>
          <button class="link danger" @click="onDelete">Delete</button>
        </span>
      </div>
      <dl class="headers">
        <dt>From</dt>
        <dd>{{ email.sender.display_name }} &lt;{{ email.sender.email_address }}&gt;</dd>
        <dt>To</dt>
        <dd>{{ email.recipient.display_name }} &lt;{{ email.recipient.email_address }}&gt;</dd>
        <dt>Date</dt>
        <dd>{{ formatDate(email.created_at) }}</dd>
      </dl>

      <div class="tabs" role="tablist">
        <button role="tab" :class="{ on: tab === 'rendered' }" @click="tab = 'rendered'">Rendered</button>
        <button role="tab" :class="{ on: tab === 'raw' }" @click="tab = 'raw'">
          Raw source (what the agent reads)
        </button>
      </div>

      <template v-if="tab === 'rendered'">
        <HtmlViewer v-if="email.is_html" :html="email.body_html" />
        <pre v-else class="plain">{{ email.body }}</pre>
        <p v-if="email.is_html" class="note">
          HTML email shown in a sandbox: scripts are disabled and remote images are blocked.
        </p>
      </template>
      <template v-else>
        <pre class="raw">{{ raw }}</pre>
        <p class="note">
          This is the exact text the agent receives from read_email, including HTML tags, comments and
          attributes that the Rendered tab does not show.
        </p>
      </template>
    </article>
    <p v-else class="muted">Loading…</p>
  </main>
</template>
