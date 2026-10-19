# wemail backend (FastAPI)

Local, self-hosted webmail API for the CPT_S 428 experiment. Two predefined
accounts only (`attacker`, `target`); synthetic data only; no public exposure.

## Requirements
- **Python 3.10–3.13** (3.12 recommended if installing fresh). Avoid 3.14 for
  now (some deps lack stable 3.14 wheels) and 3.8/3.9 (the deps dropped them).
  `requirements.txt` uses version ranges, so `pip` installs a build compatible
  with your interpreter.

## Setup

```bash
cd backend
python3 -m venv .venv              # Windows: use py if python3 doesn't work
source .venv/bin/activate          # Windows: .venv\Scripts\activate
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

## Accounts & login (issue #2)

Two predefined accounts only — there is no registration (`POST /auth/register`
returns 403). Synthetic, local-only demo credentials:

| Role     | Email                | Password      |
|----------|----------------------|---------------|
| attacker | attacker@wemail.com  | `attacker123` |
| target   | target@wemail.com    | `target123`   |

These are set on first startup (the DB auto-seeds). They are **not secrets** —
they exist so the team can log in locally. Change them via the DB if desired.

### Auth endpoints
- `POST /auth/login` — body `{ "email", "password" }` → `{ access_token, token_type, user, inbox_path }`. Wrong credentials → `401`.
- `GET  /auth/me` — `Authorization: Bearer <token>` → the caller's OWN account + profile. Another account's data is never returned here.
- `POST /auth/logout` — `Authorization: Bearer <token>` → revokes the token (reuse → `401`).
- `POST /auth/register` — always `403` (registration disabled).

### Configuration (auth)
- `SECRET_KEY` — JWT signing key (default is a dev-only placeholder; set a real one).
- `TOKEN_TTL_MINUTES` — token lifetime (default `120`).

## Troubleshooting
- **`ArgumentError: Could not interpret annotation Mapped[...]` or a crash while
  mapping `User`/`Email` on startup** → your SQLAlchemy is too old for your
  Python (e.g. SQLAlchemy 2.0.36 on Python 3.14). Recreate the venv on Python
  3.10–3.13 and reinstall: `pip install -r requirements.txt`.
- **`bcrypt` fails to install / build** → you're on a Python with no bcrypt
  wheel (old pin on 3.12+). The current range (`bcrypt>=4.2`) has wheels for
  3.10–3.13; recreate the venv and reinstall.
- **Startup log: `(trapped) error reading bcrypt version`** → harmless cosmetic
  warning from passlib reading bcrypt 4.1+. Auth works normally; ignore it.
