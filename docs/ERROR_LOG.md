# Error log (for the owner)

**Where:** left menu, **Error log** (same people who can open the Audit log: the owner / admins).

## What it shows
Everything that went wrong for any user, from the moment they logged in:

| Level | Meaning | Example |
|---|---|---|
| **Error** | Something broke | Server crash, a screen that crashed, the server could not be reached |
| **Warning** | An action was refused | "You do not have permission" |
| **Notice** | A mistake in what was typed | Duplicate name, wrong value |

Each line shows: **time, who, which branch, which page, what happened, how many times, and a short code**.
The same problem happening again is counted on one line ("Times"), so the list stays short.

Press a line to open it:
- **What the person did before it** – the last pages they opened and what the screen asked the server (no typed text, no patient data).
- **Technical detail** – for a server crash, the full technical message.
- **Copy for Claude** – copies everything in plain text. Paste it in the chat with Claude and it can be fixed.
- **Mark solved** and a short note. Lines are never deleted.
- **This login** (link under the user's name) – shows everything from that one login.

## The short code
When the server crashes, the user sees a message with a code (for example `E51F3642`).
Ask them to read out the code; search it in the Error log to find the exact line.

## What is NOT stored
Typed text, form contents, the part of a web address after `?`, passwords, tokens.

## For the programmer (Claude)
- Server errors: `backend/apps/common/exception_handler.py` writes every crash / refusal.
- Screen errors: `frontend/src/errorLog/` (trail, global catch, crash page) → `POST /api/v1/error-logs/report/`.
- Table: `ErrorLog` in `backend/apps/audit/models.py`; writer: `backend/apps/audit/error_log.py`.
- Tests: `backend/apps/audit/tests/test_error_log.py`.
