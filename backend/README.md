# wemail — backend (FastAPI)

Local, self-hosted webmail API for the CPT_S 428 experiment. Two predefined
accounts only (`attacker`, `target`); synthetic data only; no public exposure.

## Requirements
- **Python 3.14** (team standard; verified on CPython 3.14.6). Dependencies are
  pinned to an exact 3.14-verified set in `requirements.txt` so everyone runs
  the identical stack. On Windows, install Python 3.14 from python.org and use
  `py -3.14` if `python3` isn't on PATH.

## Setup

```bash
cd backend
python3 -m venv .venv              # Windows: use py if python3 doesn't work
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
# from backend/ with the venv active
uvicorn app.main:app --reload --port 8000
```

- API root: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health → `{"status": "ok", "service": "wemail-backend"}`

## Configuration
- `FRONTEND_ORIGINS` — comma-separated CORS origins allowed to call the API
  (default: `http://localhost:5173,http://127.0.0.1:5173`).

## Layout
```
backend/
  app/
    __init__.py
    config.py    # env-driven settings (CORS origins)
    main.py      # FastAPI app, CORS, /health
  requirements.txt
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
  mapping `User`/`Email` on startup** → your installed deps are older than those
  pinned here (e.g. an old SQLAlchemy on Python 3.14). Recreate the venv on
  Python 3.14 and reinstall the pinned set: `pip install -r requirements.txt`.
- **`bcrypt` fails to install / build** → you're not on the pinned `bcrypt==4.3.0`
  (older bcrypt lacks Python 3.14 wheels). Recreate the venv on 3.14 and reinstall.
- **Startup log: `(trapped) error reading bcrypt version`** → harmless cosmetic
  warning from passlib reading bcrypt 4.1+. Auth works normally; ignore it.
