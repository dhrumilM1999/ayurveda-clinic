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
| `.env` | **Your settings and secrets** (created by start.bat). Never share it. | SAFE TO EDIT (carefully) |
| `.env.example` | Template for `.env` with safe practice values | ASK FIRST |
| `docker-compose.yml` | Describes the 4 containers | ASK FIRST |
| `start-share.bat` / `docker-compose.share.yml` | Share mode: open the app from a phone on the same Wi-Fi | ASK FIRST |
| `demo-video/` | Demo videos (kept on the PC only, not in Git) and their English / Gujarati / Hindi captions | SAFE TO EDIT |
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
| `backend/apps/organizations/features_catalog.py` | Modules switched on/off per branch, and the optional **additional features** per organization (`ADDITIONAL_FEATURES`) | **SAFE TO EDIT** |
| `backend/apps/organizations/management/commands/seed_demo.py` | Sample data (made-up names, rooms, timings) | **SAFE TO EDIT** |
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
| `backend/apps/medicines/` | Medicine list, versions, branch price, Excel import | ASK FIRST |
| `backend/apps/medicines/sample_catalog.py` | The 23 SAMPLE medicines for a new clinic (**pharmacist to verify**) | **SAFE TO EDIT** |
| `backend/apps/prescriptions/` | Prescriptions and prescription templates | ASK FIRST |
| `backend/apps/pharmacy/` | Stock by batch, racks, purchases, returns, stock checks, dispensing, stock ledger | ASK FIRST |
| `backend/apps/billing/` | Bills (invoices), payments, credit notes, bill numbers, PDF printing, UPI link; `opd.py` = OPD bill rules (fees, new case / follow-up) | ASK FIRST |
| `backend/apps/billing/sample_services.py` | The SAMPLE services & charges for a new clinic | **SAFE TO EDIT** |
| `backend/apps/reports/` | Dashboard numbers in OPD words (`/dashboard/today/`); `reports.py` = the Reports figures, `exports.py` = Excel / PDF download | ASK FIRST |
| `backend/apps/documents/` | Print-outs (prescription, certificate, follow-up card, Prakriti report), QR "genuine?" check, WhatsApp share | ASK FIRST |
| `backend/apps/documents/words.py` | Words on print-outs in EN/GU/HI and the Prakriti guidance | **SAFE TO EDIT** |
| `backend/apps/prescriptions/safety.py` | **Prescription safety rules** (fixed rules, not AI) | ASK FIRST |
| `backend/apps/emr/templates_catalog.py` | **Starting check-up templates**: Ashtavidha, Dashavidha, Agni & habits, Prakriti questions (EN/GU/HI) | **SAFE TO EDIT** |
| `backend/apps/appointments/messages_catalog.py` | **SMS/WhatsApp text** for booking, change, cancel, token (EN/GU/HI) | **SAFE TO EDIT** |
| `backend/apps/*/migrations/` | Database change history. **Never edit old files here.** | ASK FIRST |
| `backend/apps/*/tests/`, `backend/conftest.py` | Automated tests | ASK FIRST |
| `backend/templates/documents/` | Print/PDF templates. `invoice.html` = OPD / pharmacy bill and credit note, `medicine_label.html` = medicine labels, `report.html` = Reports PDF | **SAFE TO EDIT** |
| `backend/apps/pharmacy/labels.py` | Medicine labels: which fields, sizes (`FORMATS`), words in GU/HI (`WORDS`) | ASK FIRST |

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
| `frontend/src/pages/consult/VisitWorkspace.tsx` | Check-up autosave and undo: `AUTOSAVE_MS`, `RETRY_MS`, `UNDO_STEPS` at the top | **SAFE TO EDIT** (those lines) |
| `frontend/src/pages/medicines/` | Medicines screen, import, version history | ASK FIRST |
| `frontend/src/pages/consult/PrintMenu.tsx` | The Print menu and certificate form on the check-up screen | ASK FIRST |
| `frontend/src/pages/VerifyPage.tsx` | Public "Is this document genuine?" page (QR code) | ASK FIRST |
| `frontend/src/pages/billing/` | Billing screen and the OPD bill popup | ASK FIRST |
| `frontend/src/pages/FeesServicesPage.tsx` | Fees & services screen | ASK FIRST |
| `frontend/src/pages/ReportsPage.tsx` | Reports screen. The `REPORTS` list at the top says which permission each report needs and which totals show as big numbers | ASK FIRST |
| `frontend/src/components/BillPreview.tsx` | PDF popup for bills and medicine labels (paper / format, print, download) | ASK FIRST |
| `frontend/src/utils/dosage.ts` | Quick dosage (222 -> 2-2-2), quantity working-out, the quick day choices (`DAY_CHOICES`) | **SAFE TO EDIT** (`DAY_CHOICES`) |
| `frontend/src/pages/consult/DaysBar.tsx` | Medicine days / follow-up days bar on the check-up screen | ASK FIRST |
| `frontend/src/pages/pharmacy/` | Pharmacy screen: dispense, sales & returns, bills, stock, purchases, stock check, ledger, racks & suppliers | ASK FIRST |
| `frontend/src/pages/consult/RxSection.tsx` | The prescription part of the check-up | ASK FIRST |
| `frontend/src/pages/AdditionalSettingsPage.tsx` | The Additional settings screen (optional extra features) | ASK FIRST |
| `frontend/src/pages/TemplatesPage.tsx` | The Check-up templates editing screen | ASK FIRST |
| `frontend/src/utils/formDraft.ts` | Keeps unsaved forms in the browser tab (autosave of the patient form) | ASK FIRST |
| `frontend/src/pages/appointments/QueueDisplayPage.tsx` | TV screen: `REFRESH_SECONDS`, `NEXT_COUNT` at the top | **SAFE TO EDIT** (those two lines) |
| `frontend/src/layout/` | The frame: menu, top bar | ASK FIRST |
| `frontend/src/auth/` | Login, branch choice, auto-logout | ASK FIRST |
| `frontend/src/api/` | Talking to the backend | ASK FIRST |
| `frontend/src/App.tsx` | List of screens (routes) | ASK FIRST |
| `frontend/package.json` | List of JavaScript packages | ASK FIRST |
| `frontend/vite.config.ts` | Development server settings | ASK FIRST |
| `frontend/scripts/check-translations.mjs` | Checks the 3 language files match | ASK FIRST |
