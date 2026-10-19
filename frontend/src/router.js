import { createRouter, createWebHistory } from 'vue-router'
import { auth, restoreSession } from './auth.js'
import LoginView from './views/LoginView.vue'
import MailListView from './views/MailListView.vue'
import EmailView from './views/EmailView.vue'
import ComposeView from './views/ComposeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/inbox' },
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/inbox', component: MailListView, props: { box: 'inbox' } },
    { path: '/inbox/:role', redirect: '/inbox' }, // /auth/login returns inbox_path = /inbox/<role>
    { path: '/sent', component: MailListView, props: { box: 'sent' } },
    { path: '/mail/:id(\\d+)', component: EmailView, props: true },
    { path: '/compose', component: ComposeView },
    { path: '/:pathMatch(.*)*', redirect: '/inbox' },
  ],
})

router.beforeEach(async (to) => {
  if (!auth.ready) await restoreSession()
  if (to.meta.public) return auth.account ? '/inbox' : true
  return auth.account ? true : '/login'
})

export default router
