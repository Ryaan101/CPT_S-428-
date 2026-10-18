"""Authentication routes (issue #2): login, logout, current account, and an
explicit 'registration disabled' endpoint.

Only the two predefined accounts can log in. /auth/me returns ONLY the caller's
own account data, so the attacker cannot reach the target's account here.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..crud import _get_user_by_email, get_profile, public_user_view
from ..database import get_db
from ..models import User
from ..security import (
    create_access_token,
    get_current_user,
    revoke_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=True)


class LoginRequest(BaseModel):
    email: str
    password: str


def _inbox_path(role: str) -> str:
    # Each account is routed to its own inbox after login.
    return f"/inbox/{role}"


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = _get_user_by_email(db, body.email.strip().lower())
    # Same error whether the email is unknown or the password is wrong.
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": public_user_view(user),
        "inbox_path": _inbox_path(user.role),
    }


@router.post("/logout")
def logout(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    revoke_token(creds.credentials)
    return {"status": "logged out"}


@router.get("/me")
def me(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Self-only: the authenticated account's own public info + private profile.
    return {
        "user": public_user_view(current),
        "profile": get_profile(db, current.id, current.id),
        "inbox_path": _inbox_path(current.role),
    }


@router.post("/register", status_code=status.HTTP_403_FORBIDDEN)
def register():
    # Public registration is disabled by design; only two predefined accounts exist.
    raise HTTPException(
        status_code=403,
        detail="Registration is disabled: this app has only two predefined accounts.",
    )
