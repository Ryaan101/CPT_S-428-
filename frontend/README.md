# wemail — frontend (Vue 3 + Vite)

Local webmail UI for the CPT_S 428 experiment. Talks to the FastAPI backend
over HTTP/JSON.

## Requirements
- Node.js 18+ and npm (`../.nvmrc` pins 22, which is what was tested)

## Setup

```bash
cd frontend
npm install
```

## Run

```bash
npm run dev       # dev server at http://localhost:5173
npm run build     # production build into frontend/dist/
npm run preview   # preview the production build
```

Start the backend first (see `../backend/README.md`) so the health badge on the
landing page shows `backend: ok`.

## Configuration
- `VITE_API_BASE` — backend base URL (default `http://localhost:8000`). Set in a
  `.env` file in `frontend/` if your backend runs elsewhere.

## Layout
```
frontend/
  index.html
  vite.config.js
  package.json
  src/
    main.js            app bootstrap (adds the router)
    App.vue            shell: top bar and <RouterView>
    router.js          routes and the login guard
    auth.js            shared login state (token, account)
    api.js             backend client (health, auth, mail)
    format.js          date formatting and the raw-source helper
    style.css
    views/
      LoginView.vue    login form and backend health badge
      MailListView.vue inbox and sent (auto-refreshes every 5 seconds)
      EmailView.vue    one email: Rendered tab and Raw source tab
      ComposeView.vue  compose and reply, plain text or HTML
    components/
      HtmlViewer.vue   the only place email HTML is displayed (sandboxed iframe)
```

## Logging in (issue #2)

Start the backend, then open the dev server. Log in with a predefined account
(see `../backend/README.md` for the synthetic credentials). On success the token
is stored in `localStorage` and a minimal account panel is shown with a logout
button. The inbox, sent, email view and compose pages follow login (issue #4).

## Rendering email safely
Email bodies are untrusted. HTML mail is shown only in `HtmlViewer.vue`, a fully sandboxed iframe
(empty `sandbox` attribute) with a Content-Security-Policy that blocks network access. Never use
`v-html` or `innerHTML` for email content; `tests/test_frontend_static.py` fails if they appear.
