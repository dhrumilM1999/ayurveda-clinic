# Folder map

**SAFE TO EDIT** = you can change it yourself (follow the comments at the top of the file).
**ASK FIRST** = ask Claude Code before changing it. A mistake here can break the app or lose data.

## Project root

| Path | What it is | |
|---|---|---|
| `CLAUDE.md` | The project brief that Claude Code reads | ASK FIRST |
| `README.md` | Short introduction | SAFE TO EDIT |
| `CHANGELOG.md` | What changed in each step | SAFE TO EDIT |
| `start.bat` / `stop.bat` / `logs.bat` / `reset-demo-data.bat` | Double-click helpers | SAFE TO EDIT (messages only) |
| `start-without-docker.bat` | Starts the app without Docker (Python + Node, file database, demo only) | SAFE TO EDIT (messages only) |
| `.env` | **Your settings and secrets** (created by start.bat). Never share it. | SAFE TO EDIT (carefully) |
| `.env.example` | Template for `.env` with safe demo values | ASK FIRST |
| `docker-compose.yml` | Describes the 4 containers | ASK FIRST |
| `.gitattributes`, `.gitignore`, `.htaccess` | Technical housekeeping | ASK FIRST |
| `docs/` | These guide files | SAFE TO EDIT |

## backend/ (Django, Python)

| Path | What it is | |
|---|---|---|
| `backend/config/settings.py` | Main backend settings | ASK FIRST |
| `backend/config/urls.py` | Top-level address map | ASK FIRST |
| `backend/requirements.txt` | List of Python packages | ASK FIRST |
| `backend/apps/common/` | Shared building blocks (base model, soft delete, adapters) | ASK FIRST |
| `backend/apps/organizations/` | Organization, branches, rooms, feature switches | ASK FIRST |
| `backend/apps/organizations/features_catalog.py` | List of modules that can be switched on/off per branch | **SAFE TO EDIT** |
| `backend/apps/organizations/management/commands/seed_demo.py` | Demo data (fake names, rooms, timings) | **SAFE TO EDIT** |
| `backend/apps/accounts/` | Staff users, roles, login, OTP, doctor schedules | ASK FIRST |
| `backend/apps/accounts/permissions_catalog.py` | **All permissions** and the starting permissions of each role | **SAFE TO EDIT** |
| `backend/apps/audit/` | Audit log | ASK FIRST |
| `backend/apps/patients/` | Patients, vitals, documents, consent | ASK FIRST |
| `backend/apps/patients/consent_catalog.py` | Starting consent wording (EN/GU/HI) — **sample, lawyer to check** | **SAFE TO EDIT** |
| `backend/apps/common/masters_catalog.py` | Starting values of every dropdown list (title, blood group, conditions...) | **SAFE TO EDIT** |
| `backend/apps/common/fields.py` | Encryption of medical notes | ASK FIRST |
| `backend/apps/notifications/` | SMS and WhatsApp (click-to-chat) adapters | ASK FIRST |
| `backend/apps/appointments/` | Appointments, walk-in tokens, queue | ASK FIRST |
| `backend/apps/emr/` | Check-ups (visits), Ayurveda exam templates | ASK FIRST |
| `backend/apps/emr/templates_catalog.py` | **Starting check-up templates**: Ashtavidha, Dashavidha, Agni & habits, Prakriti questions (EN/GU/HI) | **SAFE TO EDIT** |
| `backend/apps/appointments/messages_catalog.py` | **SMS/WhatsApp text** for booking, change, cancel, token (EN/GU/HI) | **SAFE TO EDIT** |
| `backend/apps/*/migrations/` | Database change history. **Never edit old files here.** | ASK FIRST |
| `backend/apps/*/tests/`, `backend/conftest.py` | Automated tests | ASK FIRST |
| `backend/templates/documents/` | Print/PDF templates (from Step 7) | **SAFE TO EDIT** |

## frontend/ (React, TypeScript)

| Path | What it is | |
|---|---|---|
| `frontend/src/config/clinic.ts` | **App name, colours, logo, default language** | **SAFE TO EDIT** |
| `frontend/src/config/menu.tsx` | **Left menu items** | **SAFE TO EDIT** |
| `frontend/src/i18n/en.json`, `gu.json`, `hi.json` | **All screen text** in English, Gujarati and Hindi | **SAFE TO EDIT** |
| `frontend/src/styles.css` | Small global styles | **SAFE TO EDIT** |
| `frontend/public/logo.svg` | The logo | **SAFE TO EDIT** (replace the file) |
| `frontend/src/pages/` | One file per screen (`pages/patients/` = patient screens, `pages/appointments/` = appointments and queue) | ASK FIRST |
| `frontend/src/pages/consult/` | The check-up screen | ASK FIRST |
| `frontend/src/pages/appointments/QueueDisplayPage.tsx` | TV screen: `REFRESH_SECONDS`, `NEXT_COUNT` at the top | **SAFE TO EDIT** (those two lines) |
| `frontend/src/layout/` | The frame: menu, top bar | ASK FIRST |
| `frontend/src/auth/` | Login, branch choice, auto-logout | ASK FIRST |
| `frontend/src/api/` | Talking to the backend | ASK FIRST |
| `frontend/src/App.tsx` | List of screens (routes) | ASK FIRST |
| `frontend/package.json` | List of JavaScript packages | ASK FIRST |
| `frontend/vite.config.ts` | Development server settings | ASK FIRST |
| `frontend/scripts/check-translations.mjs` | Checks the 3 language files match | ASK FIRST |
