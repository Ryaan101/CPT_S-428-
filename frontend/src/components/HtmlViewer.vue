<script setup>
// Renders an untrusted HTML email. This is the ONLY place email HTML is displayed, and it is
// never inserted into the page DOM: it goes into a fully sandboxed iframe (empty sandbox
// attribute = no scripts, no forms, no popups, no same-origin access, no top navigation),
// loaded through srcdoc under its own Content-Security-Policy that blocks all network access
// (so tracking pixels and remote images do not load) while still allowing inline styles, so
// hidden text styled with CSS renders the way a real mail client would show it.
import { computed } from 'vue'

const props = defineProps({ html: { type: String, default: '' } })

const CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:"

const doc = computed(
  () =>
    '<!doctype html><html><head><meta charset="utf-8">' +
    `<meta http-equiv="Content-Security-Policy" content="${CSP}">` +
    '<style>body{font-family:system-ui,sans-serif;margin:12px;color:#1f2328}</style>' +
    `</head><body>${props.html}</body></html>`
)
</script>

<template>
  <iframe class="mail-frame" sandbox="" referrerpolicy="no-referrer" title="Email content" :srcdoc="doc"></iframe>
</template>
