# Ayurveda Clinic Software — Project Brief for Claude Code

Read this file fully before doing any work in this project. Also read:
- `docs/FEATURES.md` — the full feature list (what to build)
- `docs/BUILD_STEPS.md` — the order to build it in

## 1. Who you are working with

- The owner runs Ayurveda clinics in Gujarat, India. They are **not a programmer**.
- Explain things in simple English. Avoid jargon; when you must use a technical word, explain it in one line.
- The owner wants to make small changes themselves. So every step must leave behind clear
  guide files and "SAFE TO EDIT" comments (see section 11).
- Before any big or hard-to-undo decision (deleting data, changing the database design,
  adding a paid service, changing the tech stack), stop and ask the owner first.
- At the end of each step, tell the owner in plain words: what was built, how to see it in
  the browser, and what to test.

## 2. What we are building

Clinic management software for Ayurveda clinics:
- **Multi-branch** (one clinic group, many branches) and **multi-doctor** from day one.
- Simple to use in version 1, but designed so it can grow to many branches, and maybe be sold
  to other clinics later (SaaS). Design data so this is possible, but don't build SaaS
  billing now.
- Patient flow: Appointment → Registration/check-in → Ayurvedic assessment → Diagnosis & plan →
  (Prescription / Panchakarma / Diet & lifestyle) → Billing → Follow-up (revisit loops back to
  assessment).

## 3. Fixed tech stack (do not change without asking)

| Part | Choice |
|---|---|
| Backend | Python 3.12, Django 5, Django REST Framework |
| Auth | JWT (djangorestframework-simplejwt), Argon2 password hashing |
| Frontend | React + TypeScript + Vite |
| UI library | Ant Design |
| Translations | react-i18next — English, Gujarati, Hindi |
| Database | PostgreSQL 16 + pgvector (Docker image `pgvector/pgvector:pg16`) |
| Background jobs | Celery + Redis (add when first needed, e.g. PDFs/reminders) |
| PDF | WeasyPrint (HTML templates → PDF), with Gujarati/Hindi fonts (Noto Sans Gujarati/Devanagari) |
| Run everything | Docker Compose |

## 4. Development computer: Windows, localhost only

- The owner uses **Windows + VS Code + Docker Desktop (WSL2)**. No cloud or hosting yet.
- Everything must start with one command: `docker compose up` (and a double-click `start.bat`).
- Provide Windows `.bat` scripts in the project root: `start.bat`, `stop.bat`, `logs.bat`,
  `reset-demo-data.bat`. They must print friendly messages and open the browser.
- Windows gotchas you must handle:
  - Use file-watch **polling** (Vite `server.watch.usePolling: true`; Django's default
    StatReloader is fine) so code changes reload inside Docker.
  - Add `.gitattributes` with `* text=auto eol=lf` (and `*.bat text eol=crlf`) so shell
    scripts don't break.
  - Don't rely on `.sh` entrypoint scripts; put startup commands in `docker-compose.yml`.
  - Keep `node_modules` inside the container (anonymous volume), not on the Windows disk.
- URLs: frontend `http://localhost:5173`, backend API `http://localhost:8000/api/v1/`,
  Django admin `http://localhost:8000/admin/`.
- Vite proxies `/api` to the backend, so no CORS problems in development.
- Hosting later will be AWS Mumbai (ap-south-1). Keep the app cloud-ready (settings from `.env`,
  files behind a storage adapter), but don't build any cloud setup now.

## 5. Free services now, paid later (provider adapters)

**Rule: never add a paid service or paid API unless the owner explicitly asks.**
Every external service goes behind an adapter (a small Python interface with one class per
provider). The provider is picked by a setting in `.env`, so moving to paid later is a one-line
change plus an API key.

| Service | `.env` setting | Free provider (build now) | Paid provider (later, only when asked) |
|---|---|---|---|
| AI language model | `AI_PROVIDER=ollama` | Ollama running locally on Windows (`http://host.docker.internal:11434`) | claude / openai / gemini / sarvam |
| Speech-to-text | `STT_PROVIDER=whisper_local` | faster-whisper (local) | sarvam / google |
| OCR | `OCR_PROVIDER=tesseract` | Tesseract with `guj`, `hin`, `eng` | cloud OCR |
| WhatsApp | `WHATSAPP_PROVIDER=click_to_chat` | `https://wa.me/<number>?text=<message>` links; staff tap Send | WhatsApp Business API |
| SMS | `SMS_PROVIDER=console` | Log to console / save in DB (no real sending) | DLT-registered SMS gateway |
| Email | `EMAIL_PROVIDER=mailpit` | Mailpit test inbox in Docker (`http://localhost:8025`) | real email service |
| Payments | `PAYMENT_PROVIDER=static_upi` | UPI QR from `upi://pay?pa=<VPA>&pn=<name>&am=<amount>&tn=<invoice no>`; staff marks paid | Razorpay |
| File storage | `STORAGE_PROVIDER=local` | Local folder (Docker volume) | AWS S3 |

- Every adapter must also have a `fake` provider used in automated tests.
- If Ollama isn't running, AI features must fail gracefully ("AI is offline") — the rest of the
  app must keep working.

## 6. Architecture rules

- **Modular monolith**: one Django project, one Django app per module, in `backend/apps/`:
  `common`, `organizations`, `accounts`, `audit`, `patients`, `appointments`, `emr`,
  `medicines`, `prescriptions`, `billing`, `documents` (PDF/print), `pharmacy`, `therapy`,
  `diet`, `notifications`, `reports`, `ai`, `feedback`. Apps talk to each other through
  services/functions, not by reaching into each other's internals.
- **API-first**: all features go through REST APIs under `/api/v1/`. The React app (and a
  future mobile app) only uses these APIs.
- **Data ownership**:
  - Organization → Branches → Rooms → Staff.
  - **Patients belong to the organization** (one patient ID, full history at any branch).
  - **Visits, appointments, invoices, stock belong to a branch.**
  - Doctors can work at several branches, with a schedule per branch.
  - Masters (medicines, therapies, diet templates, questionnaires) are defined at organization
    level; branches can override price, stock and active/inactive.
- **Every main table** has: UUID primary key, `organization` (and `branch` where relevant),
  `created_at`, `updated_at`, `created_by`, `updated_by`, and **soft delete** (`is_deleted`,
  `deleted_at`). Never hard-delete medical, billing or audit records.
- **Branch scoping**: the frontend sends the current branch in an `X-Branch-ID` header. A
  shared permission class checks the user is allowed in that branch and filters querysets.
  Org admins can see all branches.
- **Roles & permissions**: permission codes like `patients.view`, `billing.create` live in one
  catalog file. Roles (Admin, Doctor, Receptionist, Therapist, Pharmacist) are data, editable
  in the admin screen. A user gets a role **per branch**.
- **Feature flags**: modules (e.g. Panchakarma, AI scribe) can be switched on/off per branch.
- **Database indexes** on `organization_id`, `branch_id`, and date fields used in lists.
- **Dropdown values come from master tables**, never hardcoded lists.
- Settings and secrets only in `.env` (provide `.env.example` with safe demo values).

## 7. Security & Indian compliance (must follow in every step)

- DPDP Act 2023 + DPDP Rules 2025 (full obligations from 13 May 2027):
  - Purpose-wise patient consent at registration (treatment, SMS/WhatsApp, AI processing,
    research), shown in English/Gujarati/Hindi; record when and how consent was given or withdrawn.
  - Screens to handle patient requests: view, correct, erase (erase must respect legal
    medical-record retention — mask instead of delete), and a grievance contact.
- **Audit log**: record who viewed, created, changed, printed, exported or shared any patient
  record — user, branch, time, IP, what changed. Audit logs are append-only.
- Login: strong passwords, rate-limited login, short-lived access tokens, auto-logout on idle,
  2FA (OTP) for doctors and admins (in development, OTP is shown via the `console` SMS provider).
- Least-privilege: e.g. therapist cannot see billing; pharmacist sees prescriptions, not full history.
- Mask sensitive data in lists (phone `98XXXXXX21`). Don't store Aadhaar numbers.
- Encrypt highly sensitive fields at the application level where practical.
- Protect against OWASP Top 10 (Django/DRF defaults, validation on every input, no raw SQL
  with string formatting).
- **Use only fake/demo patient data in development.** Provide a `seed_demo` command.
- Never send real patient data to any cloud AI. With local Ollama, data stays on the PC.

## 8. Medicine rules

- Two kinds: **Classical** (official name from Ayurvedic Formulary of India / Ayurvedic
  Pharmacopoeia of India, with reference) and **Patent & Proprietary** (brand, manufacturer,
  composition). A brand can link to its classical equivalent.
- Search by Sanskrit, English, Hindi, Gujarati synonyms.
- Fields: dosage form (churna, vati, kashaya, arishta, asava, taila, ghrita, bhasma, lehya…),
  composition, reference, manufacturer, Ayush licence no., HSN code, GST rate.
- Safety flags: Schedule E1, contains metals/bhasma, pregnancy caution, child caution.
  Show warnings when prescribing. These are **fixed rules in code, not AI**.
- Version history on formulations, so old prescriptions keep what was prescribed.

## 9. Billing rules

- One invoice can combine consultation, medicines and therapies.
- GST fields: GSTIN, HSN/SAC, CGST/SGST/IGST, place of supply. (Tax rates must be configurable;
  the owner will confirm them with their CA.)
- Invoice numbers: per branch, per financial year (April–March), sequential, never duplicated
  — generate them safely inside a database transaction.
- Cancelling or refunding creates a credit note; the original invoice is never deleted.
- Payment modes: cash, UPI, card. Daily cash closing per branch.

## 10. PDF & print rules

- All documents are HTML templates rendered to PDF on the server: prescription, invoice,
  receipt, Prakriti report, diet chart, therapy plan, consent form, certificates, follow-up card.
- Paper sizes: A4, A5, thermal 80mm and 58mm.
- Branch-wise letterhead (logo, address, footer), language per patient, doctor signature image,
  QR code to verify the document, "DUPLICATE COPY" watermark on reprints.
- WhatsApp share uses the click-to-chat adapter (link with message) for now.
- Templates must be easy to edit (see section 11).

## 11. Beginner-friendly rules (very important)

The owner will make small changes directly. So:
- Keep and update these guide files in `docs/` (create them in Step 1, update after every step):
  - `START_HERE_WINDOWS.md` — install, start, stop, log in, demo users, step by step.
  - `HOW_IT_WORKS.md` — plain-language explanation of frontend, backend, database, Docker
    (use simple analogies).
  - `FOLDER_MAP.md` — what every folder/file is for, marked **SAFE TO EDIT** or **ASK FIRST**.
  - `SMALL_CHANGES.md` — recipes: change clinic name/logo/colours, change Gujarati/Hindi text,
    edit a print template, add a role or permission, add a menu item, add a dropdown value,
    add a simple field (with migration).
  - `TROUBLESHOOTING.md` — common errors and fixes on Windows/Docker.
  - `GLOSSARY.md` — tech words explained in one line each.
  - `CHANGELOG.md` (project root) — what changed in each step, in plain words.
- Put things the owner may change in clearly named places:
  - `frontend/src/config/clinic.ts` — app name, colours, logo path, default language.
  - `frontend/src/i18n/{en,gu,hi}.json` — all screen text. **Never hardcode text in components.**
  - `backend/apps/accounts/permissions_catalog.py` — permission list.
  - `backend/templates/documents/` — print/PDF templates.
- Add a short comment at the top of each editable file: `SAFE TO EDIT: <what you can change here>`.
- Write code that is plain and readable over clever.

## 12. Code quality

- Write tests for each step (pytest or Django tests for backend; at least type-check and
  build for frontend). Run them before saying a step is done.
- Always create Django migrations for model changes and never edit old migrations.
- Keep API responses consistent; paginate lists; validate all input with serializers.
- Use English for code; translations for screen text.
- Don't install new packages without saying why in one line.

## 13. AI rules

- AI only **suggests**. The doctor must Accept / Edit / Reject before anything is saved.
  AI never writes a prescription by itself.
- Save both the AI suggestion and the doctor's final version, with the prompt version and model
  name, in an `ai` audit table.
- Check the patient's AI consent before any AI call.
- Remove name, phone, address before sending text to any AI provider; put them back after.
- Prompts live in versioned template files, not inside code.
- Per-branch on/off switch and (for paid providers later) a monthly cost limit.
- Slow AI jobs run in the background (Celery).

## 14. Not now (out of scope until the owner asks)

Cloud hosting, paid APIs, mobile app, teleconsultation, ABDM/ABHA integration, IPD (beds),
SaaS subscriptions, ISO 27001 work. Design data so these can be added later.
