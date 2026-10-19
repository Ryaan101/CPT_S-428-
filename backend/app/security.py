"""Authentication primitives (issue #2): password hashing, JWT tokens, and the
current-user dependency.

- Passwords are hashed with bcrypt (passlib).
- A successful login returns a signed JWT bound to the account (sub = user id,
  role, jti). All account data is served against the token's subject, so one
  account can never act as the other.
- Logout revokes the token's jti. Revocation is kept in memory (cleared on
  restart) — acceptable for this local experiment; a persistent denylist would
  be the production approach.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .crud import _get_user_by_id
from .database import get_db
from .models import User

DEV_SECRET_KEY = "dev-only-insecure-secret-change-me"
SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET_KEY)
ALGORITHM = "HS256"
TOKEN_TTL_MINUTES = int(os.environ.get("TOKEN_TTL_MINUTES", "120"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# jti values of tokens invalidated by logout (in-memory; see module docstring).
_REVOKED_JTIS = set()

_bearer = HTTPBearer(auto_error=True)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    return pwd_context.verify(password, password_hash)


def create_access_token(user: User) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def revoke_token(token: str) -> None:
    """Invalidate a token by recording its jti (used by logout)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return  # already invalid; nothing to revoke
    jti = payload.get("jti")
    if jti:
        _REVOKED_JTIS.add(jti)


def _decode(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("jti") in _REVOKED_JTIS:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    return payload


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated account from the Bearer token.

    Everything downstream keys off this user's id, which is how the attacker is
    prevented from acting as the target.
    """
    payload = _decode(creds.credentials)
    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    user = _get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown account")
    return user
