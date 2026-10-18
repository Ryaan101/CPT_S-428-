# wemail — frontend (Vue 3 + Vite)

Local webmail UI for the CPT_S 428 experiment. Talks to the FastAPI backend
over HTTP/JSON.

## Requirements
- Node.js 18+ and npm

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
    main.js       # app bootstrap
    App.vue       # landing / login page (auth wired in issue #2)
    api.js        # backend client (health check)
    style.css
```
