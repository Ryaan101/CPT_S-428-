"""Agent routes: the narrow API the local AI agent process uses.

Authentication is a shared secret (AGENT_TOKEN), deliberately separate from user
login JWTs: a browser session can never call these routes, and this token can
never call /mail/*. The routes are bound to the TARGET mailbox.

What the agent's two tools map to:
    read_email  ->  GET  /agent/emails/{id}        (raw content as received)
    reply       ->  POST /agent/emails/{id}/reply  (always to the original sender)

Forwarding is restricted to the fixed attacker account; arbitrary sending is unavailable.

Two routes are for the operator (the agent runner process), not for the model:
    GET  /agent/context                   the target's profile, placed in the system prompt
    GET  /agent/emails                    unprocessed inbox, for the monitor loop
    POST /agent/emails/{id}/processed     mark handled when no reply was sent
"""
import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import crud
from ..config import AGENT_TOKEN, MAX_BODY_LEN
from ..database import get_db

_bearer = HTTPBearer(auto_error=True)
logger = logging.getLogger("uvicorn.error")


def require_agent(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> None:
    if not hmac.compare_digest(creds.credentials.encode(), AGENT_TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Invalid agent token")


router = APIRouter(prefix="/agent", tags=["agent"], dependencies=[Depends(require_agent)])


class AgentReply(BaseModel):
    body: str = Field(max_length=MAX_BODY_LEN)


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Email not found")


@router.get("/context")
def context(db: Session = Depends(get_db)):
    try:
        return crud.agent_context(db)
    except crud.AccessDenied:
        raise HTTPException(status_code=404, detail="No target account")


@router.get("/emails")
def list_unprocessed(db: Session = Depends(get_db)):
    result = crud.agent_list_unprocessed(db)
    logger.info("agent operation=list count=%s", len(result))
    return result


@router.get("/emails/{email_id}")
def read_email(email_id: int, db: Session = Depends(get_db)):
    try:
        result = crud.agent_get_email(db, email_id)
        logger.info("agent operation=read email_id=%s", email_id)
        return result
    except crud.AccessDenied:
        raise _not_found()

@router.post("/emails/{email_id}/reply", status_code=201)
def reply(
    email_id: int,
    body: AgentReply,
    db: Session = Depends(get_db),
):
    try:
        result = crud.agent_reply(db, email_id, body.body)
        logger.info(
            "agent operation=reply email_id=%s result_id=%s",
            email_id,
            result["id"],
        )
        return result
    except crud.AccessDenied:
        raise _not_found()
    except (crud.InvalidRecipient, crud.InvalidMessage) as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.post("/emails/{email_id}/processed", status_code=204)
def mark_processed(email_id: int, db: Session = Depends(get_db)):
    try:
        crud.agent_mark_processed(db, email_id)
        logger.info("agent operation=processed email_id=%s", email_id)
    except crud.AccessDenied:
        raise _not_found()

class ForwardRequest(BaseModel):
    # Reject recipient overrides and content injection.
    model_config = {"extra": "forbid"}


class DeliveryResponse(BaseModel):
    id: int
    to: str


@router.post(
    "/emails/{email_id}/forward",
    status_code=201,
    response_model=DeliveryResponse,
)
def forward(
    email_id: int,
    body: ForwardRequest,
    db: Session = Depends(get_db),
):
    """Forward received content to the predefined attacker. Request body: {}."""
    try:
        result = crud.agent_forward(db, email_id)
        logger.info(
            "agent operation=forward email_id=%s result_id=%s",
            email_id,
            result["id"],
        )
        return result
    except crud.AccessDenied:
        raise _not_found()
    except (crud.InvalidRecipient, crud.InvalidMessage) as e:
        raise HTTPException(status_code=422, detail=str(e))
