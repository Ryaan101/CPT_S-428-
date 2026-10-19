"""Mail routes: the logged-in user's own mailbox.

Every handler keys off the authenticated user (``get_current_user``), so an
account can only list, read, send from, reply from, or delete in its OWN mailbox.
HTML bodies are accepted and stored verbatim; this API never sanitizes them,
because the experiment depends on the raw markup reaching the agent. The
frontend is responsible for rendering them safely (sandboxed iframe).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import crud
from ..config import MAX_BODY_LEN, MAX_HTML_LEN, MAX_SUBJECT_LEN
from ..database import get_db
from ..models import User
from ..security import get_current_user

router = APIRouter(prefix="/mail", tags=["mail"])


class SendRequest(BaseModel):
    to: str = Field(max_length=120)
    subject: str = Field("", max_length=MAX_SUBJECT_LEN)
    body: str = Field("", max_length=MAX_BODY_LEN)
    body_html: Optional[str] = Field(None, max_length=MAX_HTML_LEN)


class ReplyRequest(BaseModel):
    body: str = Field("", max_length=MAX_BODY_LEN)
    body_html: Optional[str] = Field(None, max_length=MAX_HTML_LEN)


def _not_found() -> HTTPException:
    # Same response whether the email does not exist or belongs to someone else.
    return HTTPException(status_code=404, detail="Email not found")


@router.get("/inbox")
def inbox(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.list_inbox(db, current.id)


@router.get("/sent")
def sent(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.list_sent(db, current.id)


@router.get("/contacts")
def contacts(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The other account(s) this user may write to."""
    return crud.list_contacts(db, current.id)


@router.post("/send", status_code=201)
def send(body: SendRequest, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return crud.send_email(db, current.id, body.to, body.subject, body.body, body.body_html)
    except (crud.InvalidRecipient, crud.InvalidMessage) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{email_id}")
def read(email_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        email = crud.get_email_for(db, current.id, email_id)
    except crud.AccessDenied:
        raise _not_found()
    crud.mark_read(db, current.id, email_id)
    return email


@router.post("/{email_id}/reply", status_code=201)
def reply(
    email_id: int,
    body: ReplyRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return crud.reply_to_email(db, current.id, email_id, body.body, body.body_html)
    except crud.AccessDenied:
        raise _not_found()
    except (crud.InvalidRecipient, crud.InvalidMessage) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{email_id}", status_code=204)
def delete(email_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        crud.delete_email(db, current.id, email_id)
    except crud.AccessDenied:
        raise _not_found()
