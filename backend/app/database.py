"""Database engine/session setup (issue #3).

SQLite via SQLAlchemy 2.0. The DB file lives next to the backend app and is
git-ignored. Local, synthetic data only.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Default to a file-based SQLite DB in the backend directory.
_DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wemail.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{_DEFAULT_DB}")

# check_same_thread=False is required for SQLite under the dev server's threads.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db():
    """FastAPI dependency that yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
