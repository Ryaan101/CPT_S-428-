"""FastAPI application entry point (issue #1 scaffold).

This file wires up the app, enables CORS for the local Vite frontend, and
exposes a health endpoint the frontend uses to prove the connection. Feature
routers (database, login, mail) are added by their own issues.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import AGENT_TOKEN, DEV_AGENT_TOKEN, FRONTEND_ORIGINS
from .routers import agent as agent_router
from .routers import auth as auth_router
from .routers import mail as mail_router
from .security import DEV_SECRET_KEY, SECRET_KEY
from .seed import seed

app = FastAPI(title="wemail backend", version="0.1.0")

app.include_router(auth_router.router)
app.include_router(mail_router.router)
app.include_router(agent_router.router)


@app.on_event("startup")
def on_startup():
    """Create tables and seed the two predefined accounts if needed (issue #3)."""
    seed()
    if SECRET_KEY == DEV_SECRET_KEY or AGENT_TOKEN == DEV_AGENT_TOKEN:
        logging.getLogger("uvicorn.error").warning(
            "Using development default SECRET_KEY/AGENT_TOKEN. Fine for the local "
            "experiment; set the SECRET_KEY and AGENT_TOKEN environment variables otherwise."
        )

# Allow the local dev frontend (Vite) to call the API from its own origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Liveness probe. The frontend calls this to confirm it can reach the API."""
    return {"status": "ok", "service": "wemail-backend"}
