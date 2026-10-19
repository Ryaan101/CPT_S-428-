# wemail backend (FastAPI)

## Run
From the repo root:

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

On startup the app creates `backend/wemail.db` (SQLite, git-ignored) and seeds two synthetic
accounts. An older `wemail.db` without the `emails.processed` column is upgraded automatically.
Delete the file to reset to a clean state.

## Accounts (synthetic, local only)
| Role     | Email                 | Password      |
|----------|-----------------------|---------------|
| attacker | attacker@wemail.com   | attacker123   |
| target   | target@wemail.com     | target123     |

## Configuration (environment variables)
`SECRET_KEY` (login tokens), `AGENT_TOKEN` (the agent process, see below), `FRONTEND_ORIGINS`,
`DATABASE_URL`, `TOKEN_TTL_MINUTES`. Defaults work for local use; a warning is logged at startup
while the development defaults are in use.

## API
See [../docs/API.md](../docs/API.md). Interactive docs while running: http://localhost:8000/docs

## Layout
```
app/
  main.py        app, CORS, routers, startup seed
  config.py      env settings and size limits
  database.py    engine and session
  models.py      User, Email
  crud.py        the only data-access layer (authorization lives here)
  security.py    bcrypt, JWT, current-user dependency
  seed.py        tables, two accounts, sample mail
  routers/
    auth.py      login, logout, me
    mail.py      the logged-in user's mailbox
    agent.py     the narrow API the local AI agent uses (AGENT_TOKEN)
```
