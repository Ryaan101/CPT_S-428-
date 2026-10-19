# API reference

Base URL `http://localhost:8000`. Errors are JSON `{"detail": ...}`.

## Auth (user login, JWT)
| Method | Path | Notes |
|---|---|---|
| POST | /auth/login | `{email, password}` returns `{access_token, user, inbox_path}` |
| POST | /auth/logout | revokes the token |
| GET | /auth/me | the caller's own account and private profile |
| POST | /auth/register | always 403 |

## Mail (user JWT, own mailbox only)
Send `Authorization: Bearer <access_token>`.

| Method | Path | Notes |
|---|---|---|
| GET | /mail/inbox, /mail/sent | newest first; each item includes `body`, `body_html`, `is_html`, public sender and recipient |
| GET | /mail/contacts | the other account(s), the only valid recipients |
| POST | /mail/send | `{to, subject, body, body_html?}` returns 201 and the email |
| GET | /mail/{id} | also marks it read if you are the recipient |
| POST | /mail/{id}/reply | `{body, body_html?}`; always addressed to the original sender |
| DELETE | /mail/{id} | hides it on your side only, returns 204 |

Rules: `to` must be an existing wemail account and not yourself (422 otherwise). Subject max 255
characters, body max 100,000, HTML max 200,000. A message needs a non-empty body or `body_html`.
`body_html` is stored exactly as received. For HTML mail with an empty `body`, the server fills
`body` with a plain-text preview; the raw HTML remains the source of truth. A missing email and an
email that belongs to someone else both return 404.

## Agent (AGENT_TOKEN, target mailbox only)
Send `Authorization: Bearer <AGENT_TOKEN>`. A user JWT is rejected here and the agent token is
rejected on /mail.

| Method | Path | Used by | Notes |
|---|---|---|---|
| GET | /agent/context | operator | the target's profile, placed in the system prompt; no tool exposes it |
| GET | /agent/emails | operator | unprocessed inbox: `[{id, from, subject}]` |
| GET | /agent/emails/{id} | tool `read_email` | `{id, from, subject, is_html, content}`; for HTML mail `content` is the raw HTML |
| POST | /agent/emails/{id}/reply | tool `reply` | `{body}` plain text; recipient is always the original sender; marks it processed |
| POST | /agent/emails/{id}/processed | operator | mark handled when no reply was sent |

There is no route for sending to an arbitrary address and no forward route.
