# Changes to existing code

Everything below changed a file that was already in the repo. All other files are new.

## Repo-wide
- **Line endings:** files were committed with Windows (CRLF) endings. They are now LF, and
  `.gitattributes` (`* text=auto`) lets Git convert per platform. This is a one-time commit that
  touches every file; review the commits after it for the real changes.
- **`.gitignore`:** added `.pytest_cache/` and `results/runs/`.
- **`README.md`:** your plan is kept at the top; run instructions, harness commands and layout were appended.

## Backend
| File | Change | Why |
|---|---|---|
| `models.py` | Added `Email.processed` (bool, default False). | The agent needs to know which emails it has already handled. |
| `config.py` | Added `AGENT_TOKEN`, `DEV_AGENT_TOKEN` and the three length limits. | Separate credential for the agent process; size limits for messages. |
| `crud.py` | Added imports (`HTMLParser`, config limits). Appended: `send_email`, `reply_to_email`, `mark_read`, `delete_email`, `list_contacts`, `html_to_text`, and the agent functions (`agent_context`, `agent_list_unprocessed`, `agent_get_email`, `agent_reply`, `agent_mark_processed`). Nothing existing was edited. | Sending, replying and deleting did not exist. Authorization stays in this one layer, as your module docstring requires. Recipients are validated here, HTML is stored verbatim. |
| `security.py` | `SECRET_KEY` default moved into a named constant `DEV_SECRET_KEY`. Behavior is identical. | So `main.py` can warn when the development default is in use. |
| `seed.py` | `init_db()` now also calls `_ensure_processed_column()`; the three sample emails are seeded with `processed=True`. | A teammate's existing `wemail.db` would crash without the new column, because `create_all` never alters tables. Existing and sample mail is history, so the agent must not answer it. |
| `main.py` | Included the `mail` and `agent` routers; startup logs a warning if default secrets are in use. | Wiring for the new routes. |
| `routers/auth.py` | Unchanged. | |

## Frontend
| File | Change | Why |
|---|---|---|
| `package.json`, `package-lock.json` | Added `vue-router` 4.4.5 (exact pin). | Pages for inbox, sent, email and compose. |
| `main.js` | Installs the router. | |
| `App.vue` | Now only the shell: top bar when logged in, plus `<RouterView>`. The login form and health badge moved to `views/LoginView.vue`; token storage and session logic moved to `auth.js`. Behavior is unchanged. | A single-page component cannot hold four pages, and every page needs the login state. |
| `api.js` | Existing functions untouched. `parse()` now turns FastAPI validation errors (a list) into readable text instead of `[object Object]`. Added mail calls. | 422 errors from `/mail/send` are lists. |
| `style.css` | Existing rules untouched; mail UI styles appended. | |
| `README.md` | Layout section and a short note on safe rendering. | |
