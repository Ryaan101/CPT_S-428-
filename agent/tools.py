"""Tools exposed to the agent. These are the ONLY two actions it can take.

Both go through the backend's /agent/* API (see agent/client.py). Neither can read the
user profile, so the profile only reaches the model through the system prompt
(see agent/prompts.py). reply() takes no recipient: the backend always sends it to the
original sender of the email being answered.

Only "not found" and "invalid" API errors are shown to the model as tool results. Anything
else (server down, bad token) raises, so the harness records an error instead of a quiet
"no leak".
"""
from .client import AgentApiError


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def read_email(client, email_id):
    """Return an email as received: sender, subject, and the raw content.

    For HTML mail the content is the raw HTML source, with tags, comments and
    attributes intact.
    """
    email_id = _as_int(email_id)
    if email_id is None:
        return "ERROR: email_id must be an integer"
    try:
        e = client.get_email(email_id)
    except AgentApiError as err:
        if err.status in (404, 422):
            return "ERROR: no such email"
        raise
    return f"From: {e['from']}\nSubject: {e['subject']}\n\n{e['content']}"


def reply(client, email_id, body):
    """Send a reply from the mailbox owner back to the original sender of an email."""
    email_id = _as_int(email_id)
    if email_id is None:
        return "ERROR: email_id must be an integer"
    try:
        out = client.reply(email_id, body)
    except AgentApiError as err:
        if err.status in (404, 422):
            return f"ERROR: {err.detail}" if err.status == 422 else "ERROR: no such email"
        raise
    return f"Reply sent to {out['to']}"


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_email",
            "description": "Read an email in the inbox by id. Returns the sender, subject, and raw content as received.",
            "parameters": {
                "type": "object",
                "properties": {"email_id": {"type": "integer"}},
                "required": ["email_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reply",
            "description": "Send a reply to the original sender of an email.",
            "parameters": {
                "type": "object",
                "properties": {"email_id": {"type": "integer"}, "body": {"type": "string"}},
                "required": ["email_id", "body"],
            },
        },
    },
]

DISPATCH = {"read_email": read_email, "reply": reply}
