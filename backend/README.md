# wemail — backend (FastAPI)

Local, self-hosted webmail API for the CPT_S 428 experiment. Two predefined
accounts only (`attacker`, `target`); synthetic data only; no public exposure.

## Requirements
- Python 3.8+ (pinned deps target 3.8, the local dev interpreter)

## Setup

```bash
cd backend
python3 -m venv .venv
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
