# Build Steps — copy-paste prompts for Claude Code

Build the software one step at a time. Each step below has a prompt you can paste into
Claude Code in VS Code, and a short list of things to check afterwards.

## Before you start (one time only)

1. Install these on your Windows PC:
   - **Git** — saves versions of your code (https://git-scm.com/download/win)
   - **Docker Desktop** — runs the database and app (https://www.docker.com/products/docker-desktop/).
     During setup, keep **"Use WSL 2"** ticked. Restart the PC after installing.
   - **VS Code** — you already have it.
2. Open Docker Desktop once and wait until it says "Engine running".
3. Put this folder (`ayurveda-clinic`) somewhere simple, e.g. `C:\Projects\ayurveda-clinic`.
4. In VS Code: **File → Open Folder** → choose `ayurveda-clinic`.
5. Open Claude Code in VS Code. It reads `CLAUDE.md` automatically, so it already knows the plan.
6. Paste the prompt for **Step 1** below.

Later (Step 10 only): install **Ollama** for Windows (https://ollama.com/download) for free local AI.

## Tips

- Do **one step per conversation**. Start a new Claude Code conversation for each step.
- If you see an error, copy the full error text and paste it to Claude Code with "fix this".
- After each step works, ask Claude Code: **"Commit this step to git with a clear message."**
  Then you can always go back if something breaks later.
- If you don't understand something, ask: **"Explain this to me in simple words."**
- Use only demo/fake patient data until the software is finished and secured.

---

## Phase 1 (P1) — first version

### Step 1 — Foundation
```
Build Step 1 (Foundation) as described in CLAUDE.md and docs/FEATURES.md section A.
Include:
- docker-compose.yml with PostgreSQL (pgvector image), Django backend, React (Vite) frontend, Mailpit.
- start.bat, stop.bat, logs.bat, reset-demo-data.bat for Windows, plus .env.example and .gitattributes.
- Django apps: common (base model with UUID, timestamps, created_by/updated_by, soft delete),
  organizations (Organization, Branch, Room, feature flags), accounts (custom User, Role,
  permissions catalog, per-branch role assignment, doctor branch schedules), audit (audit log).
- JWT login, rate-limited; 2FA by OTP for doctors/admins using the console SMS provider; auto-logout on idle.
- Branch scoping with the X-Branch-ID header.
- React app with Ant Design: login page, main layout with menu, branch switcher, language switcher
  (English/Gujarati/Hindi), dashboard placeholder, screens to manage branches, rooms, staff and roles,
  and an audit log screen for admins.
- seed_demo command: 1 organization, 2 branches, demo users for each role (print their logins).
- Tests for login, branch access and permissions.
- All beginner guide files listed in CLAUDE.md section 11, and CHANGELOG.md.
When finished, tell me in simple words how to start it and what to click to test it.
```
**Check:** double-click `start.bat` → browser opens → log in as admin → switch branch → change language to Gujarati → add a room.

### Step 2 — Patients
```
Build Step 2 (Patients) from docs/FEATURES.md section B (registration part) following CLAUDE.md.
Patient at organization level with UHID, demographics, contact, photo, medical history, allergies,
current allopathic medicines, uploaded documents (local storage adapter), vitals per visit (BP, pulse,
weight, height, auto BMI). Purpose-wise DPDP consent screen in English/Gujarati/Hindi with consent
history and withdrawal. Patient search, masked phone numbers in lists, audit logging of every view.
Update the guide files and CHANGELOG.
```
**Check:** register a demo patient, see them from the other branch, withdraw a consent, see the audit log entry.

### Step 3 — Appointments and queue
```
Build Step 3 (Appointments) from docs/FEATURES.md section B following CLAUDE.md.
Doctor-wise slots from branch schedules, booking, walk-in tokens, cancel/reschedule, check-in,
and a live queue screen per branch/doctor (can be shown on a TV). Prevent double booking.
Confirmation messages go through the click-to-chat WhatsApp adapter and console SMS adapter.
Update the guide files and CHANGELOG.
```
**Check:** book, check in, see the patient in the queue, click the WhatsApp link.

### Step 4 — Ayurvedic assessment and EMR
```
Build Step 4 (Assessment and EMR) from docs/FEATURES.md section C following CLAUDE.md.
Visit/consultation screen for doctors. Prakriti questionnaire stored as editable master data
(questions and scoring editable by admin), Vata/Pitta/Kapha score with a chart, Vikriti, Agni,
Koshta, Sara, Satva, Bala, Ashtavidha Pariksha quick-select fields, chief complaints, history,
diagnosis (optional NAMASTE/ICD code fields), visit timeline, symptom scores and before/after photos.
Seed a sample Prakriti questionnaire clearly marked "SAMPLE — doctor to replace".
Update the guide files and CHANGELOG.
```
**Check:** open a checked-in patient, fill Prakriti, see the score chart, save a diagnosis, see the timeline.

### Step 5 — Medicines and prescriptions
```
Build Step 5 (Medicine master and prescriptions) from docs/FEATURES.md section D, following the
medicine rules in CLAUDE.md section 8. Classical vs Patent & Proprietary medicines, synonyms search,
branch-level price/active overrides, Excel/CSV import for the medicine list, prescription screen
(dose, anupana, timing, duration), disease-wise templates, rule-based safety warnings
(Schedule E1, bhasma, pregnancy, child, allergy), version history.
Seed about 20 common SAMPLE medicines marked "SAMPLE — pharmacist to verify".
Update the guide files and CHANGELOG.
```
**Check:** import a small CSV, prescribe from a template, see a pregnancy warning for a flagged medicine.

### Step 6 — Billing
```
Build Step 6 (Billing) from docs/FEATURES.md section E following CLAUDE.md section 9.
Invoice with consultation, medicines and therapy lines; configurable GST rates; invoice numbers per
branch per financial year generated safely; cash/UPI/card payments; static UPI QR via the payment
adapter; discounts, advances, refunds and credit notes (never delete invoices); daily cash closing.
Update the guide files and CHANGELOG.
```
**Check:** bill a visit, pay by UPI QR (mark paid), cancel with a credit note, run daily closing.

### Step 7 — PDF and print
```
Build Step 7 (PDF and print) from docs/FEATURES.md section F following CLAUDE.md section 10.
Add Redis + Celery to docker-compose. WeasyPrint with Noto Sans Gujarati/Devanagari fonts.
Templates in backend/templates/documents/ for prescription, invoice, receipt, Prakriti report,
consent form, certificate and follow-up card. A4, A5, thermal 80mm/58mm. Branch letterhead,
doctor signature image, QR verification page, DUPLICATE COPY watermark, WhatsApp share link,
audit log for print/download/share. Explain in SMALL_CHANGES.md how to edit a template.
Update the guide files and CHANGELOG.
```
**Check:** print a Gujarati prescription on A5 and a receipt on 80mm; reprint shows DUPLICATE COPY; scan the QR.

### Step 8 — Basic reports and dashboard
```
Build Step 8 (Basic reports) from docs/FEATURES.md section K (P1 basic part) following CLAUDE.md.
Dashboard with today's patients, collection and queue. Reports: daily/monthly collection by payment
mode, income by doctor and branch, new vs repeat patients, missed follow-ups, GST summary.
Filters by branch and dates, export to PDF and Excel. Respect permissions.
Update the guide files and CHANGELOG.
```
**Check:** open the dashboard; export the monthly collection to Excel.

### Step 9 — Customization and feedback
```
Build Step 9 (Customization and feedback) from docs/FEATURES.md section L following CLAUDE.md.
Custom fields for patients and visits configurable by admin, editable dropdown masters,
"Suggest a feature" button on every screen (text, optional voice note, automatic screenshot,
current screen and branch), voting, an admin list of suggestions, and a "What's new" screen.
Update the guide files and CHANGELOG.
```
**Check:** add a custom field and see it on the patient form; submit a suggestion.

### Step 10 — AI foundation, AI scribe, patient summary
```
Build Step 10 (AI) from docs/FEATURES.md section N, the [P1] items only, following CLAUDE.md
sections 5 and 13. Create the ai app with provider adapters (ollama, fake), STT adapter
(faster-whisper local, fake), versioned prompt files, de-identification, AI consent check,
AI audit table, per-branch on/off. AI scribe: record audio in the browser, transcribe, draft a
structured case sheet, doctor accepts/edits/rejects. Patient summary before consultation.
If Ollama is not running, show "AI is offline" and keep everything else working.
Recommend which Ollama and Whisper models suit my PC — first ask me my RAM and graphics card.
Update the guide files and CHANGELOG.
```
**Check:** with Ollama running, record a short demo consultation; review and accept the draft.

### Step 11 — Security review
```
Do Step 11: a full security and DPDP review of the project against CLAUDE.md section 7.
List any gaps in simple words, then fix them. Add patient rights request screens
(view/correct/erase with retention rules), grievance contact settings, automatic daily database
backup to a local folder with a restore script, and a breach-response checklist in docs/.
Update the guide files and CHANGELOG.
```

---

## Phase 2 (P2) — after Phase 1 is in use

| Step | Prompt to paste |
|---|---|
| 12 Pharmacy | `Build Step 12 (Pharmacy and inventory) from docs/FEATURES.md section G following CLAUDE.md.` |
| 13 Panchakarma | `Build Step 13 (Panchakarma and therapy) from docs/FEATURES.md section H following CLAUDE.md.` |
| 14 Diet | `Build Step 14 (Diet and lifestyle) from docs/FEATURES.md section I following CLAUDE.md.` |
| 15 Communication | `Build Step 15 (Communication) from docs/FEATURES.md section J using the free adapters in CLAUDE.md section 5.` |
| 16 Advanced reports | `Build Step 16 (Advanced reports) from docs/FEATURES.md section K (P2 part) following CLAUDE.md.` |
| 17 More AI | `Build Step 17: the [P2] AI items from docs/FEATURES.md section N following CLAUDE.md sections 5 and 13.` |

Add "Update the guide files and CHANGELOG." to the end of each.

## Moving to paid services later

When you're ready, tell Claude Code for example:
```
Switch AI to the paid Claude API. Add a claude provider to the AI adapter, read the key from .env,
add a monthly cost limit, and explain what I need to do step by step. Don't send real patient data
until de-identification and consent checks are confirmed working.
```
Do the same for WhatsApp Business API, SMS, Razorpay and cloud hosting, one at a time.
