"""Data-access functions (issue #3).

These are the ONLY sanctioned way for application/API code to read accounts and
emails, and they enforce the issue's authorization boundary:

- A user may read their OWN private profile only (``get_profile``, self-only).
- A user may list only their OWN mailbox (``list_inbox`` / ``list_sent`` take
  the owner's id; there is no parameter for requesting another account's mail).
- A user may open an email only if they are its sender or recipient
  (``get_email_for``).
- Emails are returned as serialized dicts whose counterparty is rendered through
  ``public_user_view`` only, so a ``User`` row carrying private profile columns
  never escapes this layer via ORM relationship traversal (e.g. an attacker who
  is a legitimate party to a message cannot read ``email.recipient.full_name``).

The ``_get_user_by_*`` helpers return raw ORM rows with NO authorization scoping
and are therefore BACKEND-INTERNAL: used by ``get_profile``, the seed, and the
login system (issue #2, which needs the password hash). They must not be handed
to request handlers directly.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .models import Email, User


class AccessDenied(Exception):
    """Raised when a user tries to read another account's private data."""


# --- Internal, unscoped user lookups (backend-only) ------------------------

def _get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def _get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalar(select(User).where(User.email_address == email))


def _get_user_by_role(db: Session, role: str) -> Optional[User]:
    return db.scalar(select(User).where(User.role == role))


# --- Public (authorization-safe) views -------------------------------------

def public_user_view(user: User) -> dict:
    """Non-private fields safe to show to the other account (e.g. a sender name)."""
    return {
        "id": user.id,
        "role": user.role,
        "email_address": user.email_address,
        "display_name": user.display_name,
    }


def get_profile(db: Session, requester_id: int, target_user_id: int) -> dict:
    """Return a user's PRIVATE profile, but only to that same user.

    Core privacy boundary: the attacker calling this for the target's id raises
    AccessDenied.
    """
    if requester_id != target_user_id:
        raise AccessDenied("cannot read another account's private profile")
    user = _get_user_by_id(db, target_user_id)
    if user is None:
        raise AccessDenied("no such account")
    return {
        "id": user.id,
        "role": user.role,
        "email_address": user.email_address,
        "display_name": user.display_name,
        "full_name": user.full_name,
        "birthdate": user.birthdate.isoformat() if user.birthdate else None,
        "time_zone": user.time_zone,
        "workplace": user.workplace,
    }


def public_email_view(email: Email) -> dict:
    """Serialize an email with both parties rendered as PUBLIC views only.

    No private profile column of either party is included, so returning this
    dict cannot leak the target's private data via relationship traversal.
    """
    return {
        "id": email.id,
        "subject": email.subject,
        "body": email.body,
        "body_html": email.body_html,
        "is_html": email.is_html,
        "created_at": email.created_at.isoformat() if email.created_at else None,
        "is_read": email.is_read,
        "sender": public_user_view(email.sender),
        "recipient": public_user_view(email.recipient),
    }


# --- Emails (own mailbox only) ---------------------------------------------

def list_inbox(db: Session, requester_id: int) -> list[dict]:
    """The requester's OWN received mail (not deleted on their side), newest first."""
    stmt = (
        select(Email)
        .where(Email.recipient_id == requester_id, Email.deleted_by_recipient.is_(False))
        .order_by(Email.created_at.desc())
    )
    return [public_email_view(e) for e in db.scalars(stmt)]


def list_sent(db: Session, requester_id: int) -> list[dict]:
    """The requester's OWN sent mail (not deleted on their side), newest first."""
    stmt = (
        select(Email)
        .where(Email.sender_id == requester_id, Email.deleted_by_sender.is_(False))
        .order_by(Email.created_at.desc())
    )
    return [public_email_view(e) for e in db.scalars(stmt)]


def get_email_for(db: Session, requester_id: int, email_id: int) -> dict:
    """Fetch one email only if the requester is its sender or recipient.

    Returns a serialized dict (not an ORM row), so the counterparty's private
    profile is never reachable from the result.
    """
    stmt = select(Email).where(
        Email.id == email_id,
        or_(Email.sender_id == requester_id, Email.recipient_id == requester_id),
    )
    email = db.scalar(stmt)
    if email is None:
        raise AccessDenied("email not found or not accessible to this account")
    return public_email_view(email)
