"""Application configuration (issue #1 scaffold).

Values are read from the environment so the app can run locally with sensible
defaults and no external services. Only local, synthetic data is used.
"""
import os

# CORS: origins allowed to call the API. Defaults to the Vite dev server.
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# Secret used by the local AI agent process to call the /agent/* endpoints. It is
# separate from user login tokens: a user JWT cannot call /agent/* and this token
# cannot call /mail/*. Override it with the AGENT_TOKEN environment variable.
DEV_AGENT_TOKEN = "dev-only-agent-token-change-me"
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", DEV_AGENT_TOKEN)

# Size limits for message fields (characters).
MAX_SUBJECT_LEN = 255
MAX_BODY_LEN = 100_000
MAX_HTML_LEN = 200_000
