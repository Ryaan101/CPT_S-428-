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

## D3, Part 1 (baseline)
| File | Change | Why |
|---|---|---|
| `backend/app/crud.py` | Added `import re` and appended `agent_search_emails`. Nothing existing edited. | Read-only lookup of earlier received mail for the new `search_mailbox` tool. Bound to the target's received, undeleted mail; sent mail and the other mailbox never appear. |
| `backend/app/routers/agent.py` | Added `GET /agent/search?q=` and the `Query` import; logs the number of matches, never the query. | Route for the new tool. Same agent token as the other routes. |
| `agent/` | New `web.py` (closed local web). `tools.py`, `client.py`, `prompts.py`, `config.py` extended: two tools, a canary line, a per-model ID table, `MAX_STEPS` 8. | New vectors need new channels. |
| `harness/` | New `payloads.py` (bundle folders) and `report.py`. `run_trials.py`, `detect.py`, `backends.py` extended: canary per trial, earlier emails delivered first and marked processed, payload hashes in the metadata, scripted offline models that use all four tools. | Part 1 requirements. Single-file payloads and the D2 commands still work. |
| `attacks/d3/` | New: three vectors and three matching controls. | The three injection vectors. |
| `tests/` | New `test_tools.py`; new tests in `test_agent_api.py`, `test_detect.py`, `test_harness.py` (51 to 68 tests). | Cover the search route, the hermetic web, the canary and each vector reaching the agent. |
| `results/reference/` | Regenerated the two D2 mock summaries; added `d3-mock-refuse` and `d3-mock-comply`. | Reference counts for the offline controls. |

