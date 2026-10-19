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

from html.parser import HTMLParser
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import MAX_BODY_LEN, MAX_HTML_LEN, MAX_SUBJECT_LEN
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


# --- Sending, replying, deleting (user mailbox) -----------------------------

class InvalidRecipient(Exception):
    """The recipient is not one of the wemail accounts, or is the sender."""


class InvalidMessage(Exception):
    """The message is empty or a field is too long."""


class _TextExtractor(HTMLParser):
    """Collects text nodes. Used ONLY to build a plain-text preview for HTML mail."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    """Crude plain-text preview of an HTML body (for list views and search).

    This is NOT what the agent reads and NOT what is rendered: the raw HTML is
    stored verbatim in ``body_html`` and that is the source of truth.
    """
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return " ".join("".join(parser.parts).split())


def list_contacts(db: Session, requester_id: int) -> list[dict]:
    """Public views of every OTHER account (the only valid recipients)."""
    stmt = select(User).where(User.id != requester_id).order_by(User.id)
    return [public_user_view(u) for u in db.scalars(stmt)]


def _store_email(
    db: Session,
    sender: User,
    recipient_email: str,
    subject: str,
    body: str,
    body_html: Optional[str],
    processed: bool = False,
) -> Email:
    """Validate and insert one email. Shared by user sends, replies and agent replies."""
    recipient = _get_user_by_email(db, (recipient_email or "").strip().lower())
    if recipient is None:
        raise InvalidRecipient("unknown recipient: mail can only be sent to a wemail account")
    if recipient.id == sender.id:
        raise InvalidRecipient("cannot send mail to yourself")

    subject = subject or ""
    body = body or ""
    if body_html is not None and body_html == "":
        body_html = None
    if len(subject) > MAX_SUBJECT_LEN:
        raise InvalidMessage(f"subject is longer than {MAX_SUBJECT_LEN} characters")
    if len(body) > MAX_BODY_LEN or (body_html is not None and len(body_html) > MAX_HTML_LEN):
        raise InvalidMessage("message body is too long")
    if not body.strip() and body_html is None:
        raise InvalidMessage("message body is empty")

    is_html = body_html is not None
    if is_html and not body.strip():
        body = html_to_text(body_html)  # preview only; body_html stays verbatim

    email = Email(
        sender_id=sender.id,
        recipient_id=recipient.id,
        subject=subject,
        body=body,
        body_html=body_html,  # stored exactly as received: never sanitized or altered
        is_html=is_html,
        is_read=False,
        processed=processed,
    )
    db.add(email)
    db.commit()
    db.refresh(email)
    return email


def send_email(
    db: Session,
    sender_id: int,
    recipient_email: str,
    subject: str,
    body: str,
    body_html: Optional[str] = None,
) -> dict:
    """Send a new email from the requester to another wemail account."""
    sender = _get_user_by_id(db, sender_id)
    if sender is None:
        raise AccessDenied("no such account")
    return public_email_view(_store_email(db, sender, recipient_email, subject, body, body_html))


def _reply_subject(subject: str) -> str:
    return subject if subject.lower().startswith("re:") else "Re: " + subject


def _get_received(db: Session, requester_id: int, email_id: int) -> Email:
    """An email the requester RECEIVED and has not deleted; else AccessDenied."""
    email = db.scalar(
        select(Email).where(
            Email.id == email_id,
            Email.recipient_id == requester_id,
            Email.deleted_by_recipient.is_(False),
        )
    )
    if email is None:
        raise AccessDenied("email not found or not accessible to this account")
    return email


def reply_to_email(
    db: Session,
    requester_id: int,
    email_id: int,
    body: str,
    body_html: Optional[str] = None,
) -> dict:
    """Reply to an email the requester received. The reply always goes back to
    the original sender; the caller cannot pick another recipient."""
    original = _get_received(db, requester_id, email_id)
    sender = _get_user_by_id(db, requester_id)
    stored = _store_email(
        db, sender, original.sender.email_address, _reply_subject(original.subject), body, body_html
    )
    return public_email_view(stored)


def mark_read(db: Session, requester_id: int, email_id: int) -> None:
    """Mark an email read, only if the requester is its recipient."""
    email = db.scalar(
        select(Email).where(Email.id == email_id, Email.recipient_id == requester_id)
    )
    if email is not None and not email.is_read:
        email.is_read = True
        db.commit()


def delete_email(db: Session, requester_id: int, email_id: int) -> None:
    """Soft-delete an email from the requester's own side only."""
    email = db.scalar(
        select(Email).where(
            Email.id == email_id,
            or_(Email.sender_id == requester_id, Email.recipient_id == requester_id),
        )
    )
    if email is None:
        raise AccessDenied("email not found or not accessible to this account")
    if email.recipient_id == requester_id:
        email.deleted_by_recipient = True
    if email.sender_id == requester_id:
        email.deleted_by_sender = True
    db.commit()


# --- Agent (operator) access: bound to the TARGET mailbox ------------------
#
# These are called only from routers/agent.py, which requires the operator's
# AGENT_TOKEN. They are hard-wired to the target account: there is no parameter
# that selects another mailbox, and a reply always goes to the original sender.
# The agent tools (read_email, reply) are the only things the model can invoke;
# the private profile is returned by agent_context() to the OPERATOR process,
# which places it in the system prompt. No tool exposes it.

def _agent_user(db: Session) -> User:
    user = _get_user_by_role(db, "target")
    if user is None:
        raise AccessDenied("no target account")
    return user


def agent_context(db: Session) -> dict:
    """The target's own private profile, for building the agent's system prompt."""
    user = _agent_user(db)
    return get_profile(db, user.id, user.id)


def agent_list_unprocessed(db: Session) -> list[dict]:
    """Target's unprocessed inbox, oldest first. Metadata only."""
    user = _agent_user(db)
    stmt = (
        select(Email)
        .where(
            Email.recipient_id == user.id,
            Email.processed.is_(False),
            Email.deleted_by_recipient.is_(False),
        )
        .order_by(Email.id)
    )
    return [
        {"id": e.id, "from": e.sender.email_address, "subject": e.subject}
        for e in db.scalars(stmt)
    ]


def agent_get_email(db: Session, email_id: int) -> dict:
    """One email as the agent receives it. For HTML mail ``content`` is the RAW
    HTML source (tags, comments and attributes intact), which is the attack surface."""
    user = _agent_user(db)
    email = _get_received(db, user.id, email_id)
    return {
        "id": email.id,
        "from": email.sender.email_address,
        "subject": email.subject,
        "is_html": email.is_html,
        "content": email.body_html if email.is_html else email.body,
    }


def agent_reply(db: Session, email_id: int, body: str) -> dict:
    """Plain-text reply from the target to the original sender; marks it processed."""
    user = _agent_user(db)
    original = _get_received(db, user.id, email_id)
    stored = _store_email(
        db, user, original.sender.email_address, _reply_subject(original.subject), body, None
    )
    original.processed = True
    db.commit()
    return {"id": stored.id, "to": original.sender.email_address}


def agent_mark_processed(db: Session, email_id: int) -> None:
    user = _agent_user(db)
    original = _get_received(db, user.id, email_id)
    original.processed = True
    db.commit()
