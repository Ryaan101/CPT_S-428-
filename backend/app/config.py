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
