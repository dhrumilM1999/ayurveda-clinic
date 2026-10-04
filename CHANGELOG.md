# Changelog

What changed in each step, in plain words.

## One-branch mode (2026-10-04)

- New switch **Settings -> Use more than one branch** (owner only). It is **off** now: the app works with the
  main branch only, without the branch picker or the Branches menu. Branch data is kept, so turning it on later
  just shows everything again.
- Guide: how to look at the database with the free DBeaver program (docs/HOW_IT_WORKS.md, "Where is my data?").

## Step 3 - Appointments and queue (2026-10-04)

**What you can do now**
- **Appointments** screen: one day at a time (arrows to move days), filter by doctor and status, search.
- **Book appointment**: choose patient, doctor and date; free times come from the doctor's schedule.
  Booked times are crossed out. **The same doctor can never be booked twice for the same time**
  (checked on screen and locked in the database), even across branches.
- **Walk-in**: the patient gets the next **token number** for that doctor straight away.
- **Check in** (on the day) gives a token too. Then **Start** -> **Done**. Also **Reschedule**, **Cancel**
  (with reason) and **Did not come**. Appointments are never deleted.
- **Queue** screen: per doctor - who is with the doctor, who is waiting (in token order), **Call next**.
  Updates itself every 15 seconds.
- **TV screen** for the waiting room: big tokens and short names only ("Ramesh P.") for privacy.
- Messages: on booking, change, cancel and check-in, an SMS is "sent" through the free console adapter
  (shown in `logs.bat`), and a **Send on WhatsApp** button opens WhatsApp with the message ready (free click-to-chat).
  Messages go **only to patients who gave SMS/WhatsApp consent**, in the patient's language.
- The patient file has a new **Appointments** tab. The dashboard shows today's appointments and waiting count.
- The Appointments module can be switched off per branch (Settings -> Modules); the menu then hides it.

**Other fixes**
- Booking/reschedule popups no longer close by pressing Esc or clicking outside (no lost typing).
- Fixed: login stopped working after an update because the backend had stopped; a restart fixed it
  (see TROUBLESHOOTING.md).
- Removed 38 stray files that had been saved to git by mistake.
- Guide: new "Where is my data?" section in docs/HOW_IT_WORKS.md.

**Tests:** 22 new automated tests for appointments; all backend tests pass.

## Compact design (2026-10-04)

- Smaller headings and text (13px), less empty space, shorter buttons and table rows, so more fits on one screen.
- Popups now have a coloured title bar, a compact middle and a light footer with the buttons.
- Card titles are small, with a gold bar on the left.
- To adjust sizes later: `frontend/src/styles.css` (spacing, heading sizes) and `frontend/src/theme.ts` (`fontSize`, `controlHeight`).

## Docker set up (2026-10-03)

- The app now runs in Docker with the real PostgreSQL database: double-click `start.bat`, stop with `stop.bat`.
- Fixed: the database lock that stops anyone changing or deleting audit-log entries now works on PostgreSQL
  (tested: direct changes in the database are refused).
- All 55 automated tests pass on PostgreSQL too.

## Step 2 — Patients (2026-10-03)

**What you can do now**
- **Register patients** (Patients → Register patient). Each gets an ID like **AY26-000001**
  (prefix + year + running number; change the prefix on the Settings screen).
- Form sections (based on the Healthray form): photo (upload or camera), name, father/husband name,
  surname, age *or* date of birth, gender, blood group, language, contact and address, referred by,
  emergency contact, VIP / free-of-charge.
- **Duplicate check**: while you type a mobile number or full name, matching patients appear on the right.
- **Medical history**: condition check-boxes (diabetes, BP, thyroid, ...), allergies, current allopathic
  medicines, and past / family / surgical history notes (stored encrypted, visible only to doctors).
- A **red allergy alert** at the top of every patient file.
- **Vitals** (BP, pulse, weight, height, SpO₂, temperature) with automatic BMI.
- **Documents**: upload old reports and prescriptions (PDF or photo, up to 10 MB). Only doctors can open
  them; every view and download is recorded.
- **Consent (DPDP)**: purpose-wise (treatment, SMS/WhatsApp, AI, research) in English, Gujarati and Hindi;
  give or withdraw at any time; full history. The consent wording is **SAMPLE text for a lawyer to check**.
- **Search** by name, mobile number or patient ID. Lists show masked mobile numbers (98XXXXXX21).
- **Activity tab**: who opened, changed or downloaded the patient's file.

**Behind the scenes**
- Patients belong to the organization, so they can be seen from every branch. Patients are never deleted.
- Dropdown values (title, blood group, relation, conditions, ...) are stored in the database (master
  lists) with Gujarati and Hindi labels. Starting values: `backend/apps/common/masters_catalog.py`.
- New permission "Record vitals" (given to Admin, Doctor and Receptionist).
- Patient photos and documents are kept in a private folder and are never shown as public links.
- Insurance / TPA, Aadhaar / national ID, religion and income are left out on purpose (not needed for
  treatment; DPDP says collect only what is needed).
- 55 automated tests pass (20 new for patients).

## Step 1 — Foundation (2026-10-03)

**What you can do now**
- New look: forest-green and turmeric-gold theme on a cream background, Indian-designed fonts for
  Gujarati (Hind Vadodara) and Hindi (Hind), a split-screen login page, a greeting banner on the dashboard,
  and polished menus, tables and cards. The fonts work offline.
- No Docker yet? `start-without-docker.bat` runs the app with Python + Node and a simple file database (demo only).
- After logging out, the next person starts on the dashboard.
- Start everything with one double-click (`start.bat`). Stop with `stop.bat`. See messages with `logs.bat`.
  Start over with fresh demo data with `reset-demo-data.bat`.
- Log in with username and password. Doctors and admins also enter a 6-digit OTP. In development the
  OTP appears on screen and in the logs; no real SMS is sent.
- Get logged out automatically after 15 minutes without use.
- Switch between branches and between English, ગુજરાતી and हिन्दी.
- Manage **branches**, **rooms** (and room types), **staff** (with a role per branch and password reset),
  **roles & permissions** (tick boxes), **doctor schedules** (per branch, no overlapping times),
  **clinic settings** and **module switches per branch**.
- See the **audit log**: logins, failed logins, OTPs and every change, with user, branch, time and IP.

**Behind the scenes**
- Backend: Django + REST API under `/api/v1/`. Frontend: React + Ant Design. Database: PostgreSQL (pgvector image).
- Every main table has a random ID, created/updated time and person, and soft delete.
- The audit log cannot be changed or deleted (blocked in code and by a database trigger).
- Login protection: Argon2 passwords, strong-password rules, 5 tries per minute per username,
  15-minute login tokens, logout cancels the token.
- The SMS adapter has `console` and `fake` providers. It's ready to plug in a paid gateway later.
- Demo data: 1 organization, 2 branches (Ahmedabad, Vadodara), rooms, 7 demo users, doctor timings.
- 35 automated backend tests (login, OTP, rate limit, branch access, permissions, audit, soft delete).
  The frontend passes the type check, the build and the translation check.
- Guide files in `docs/`.
