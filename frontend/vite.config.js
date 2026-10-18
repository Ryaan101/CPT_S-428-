import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vue 3 + Vite dev config. Dev server runs on 5173 (allowed by backend CORS).
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
  },
})
