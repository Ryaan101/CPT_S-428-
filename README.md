# CPT_S-428-EMAIL TARGETER

# WHAT DO WE NEED TO DO

1: build webmail application both front end and back end.

1.1: Create connection between webmail accounts so that target email can be sent

1.2: create email accounts with login verification so users can log into their account

2: Create local model to monitor target account

2.1: Create the tools the local model needs (Ability to read and reply to email)




---

# How to run it

Requirements: Python 3.10+ (tested on 3.13) and Node 18+ (`.nvmrc` pins 22). Run from the repo root.

```bash
# 1. Python environment (backend, agent, harness, tests)
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Backend (terminal 1)
cd backend && uvicorn app.main:app --reload --port 8000

# 3. Frontend (terminal 2)
cd frontend && npm ci && npm run dev                      # http://localhost:5173

# 4. Agent (terminal 3, optional live demo; from the repo root)
python -m agent.monitor --backend mock-comply             # no GPU needed
python -m agent.monitor --backend ollama                  # real model, see below
```

Log in as `attacker@wemail.com` / `attacker123` and compose an email to the target (choose HTML to
send markup). The agent answers it, and the reply appears in the attacker's inbox within a few seconds.
Log in as `target@wemail.com` / `target123` in another browser profile to see the target's side,
including the **Raw source** tab, which shows exactly what the agent reads.

## Real model (Ollama)
```bash
ollama pull llama3.1:8b-instruct-q4_K_M      # pinned model, digest 46e0c10c039e
ollama serve
python -m harness.run_trials --backend ollama --n 20
```

## Measurements (the harness needs only Python)
```bash
python -m harness.run_trials --backend mock-refuse --n 20   # negative control, expect 0 leaks
python -m harness.run_trials --backend mock-comply --n 20   # positive control, expect 100%
python -m harness.run_trials --backend ollama --n 20        # the real experiment
```
Each run writes `summary.json`, `trials.csv`, `transcripts.jsonl` and `run_metadata.json` to
`results/runs/<timestamp>_<backend>/`. Reference control results are in `results/reference/`.
Exit code 2 means the backend was unusable or every trial errored. That is never reported as "0 leaks".

## Tests
```bash
python -m pytest -q
```

## Layout
```
backend/    FastAPI app (see backend/README.md)
frontend/   Vue 3 + Vite UI (see frontend/README.md)
agent/      the LLM agent: prompts, the two tools, HTTP client, live monitor
harness/    trial runner, leak detector, statistics, mock backends
attacks/    payload emails used by the harness
results/    reference control results
docs/       API.md, DECISIONS.md, CHANGES.md
tests/      pytest suite
```
