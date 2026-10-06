# Changelog

What changed in each step, in plain words.

## Prescription speed-ups, follow-up days, medicine labels, stock switches (2026-10-06)

**Faster prescription (check-up screen)**
- **Quick dosage**: type `222` in M-N-N and it becomes `2-2-2` (101 -> 1-0-1, 010 -> 0-1-0). You can still type
  anything, e.g. `1/2-0-1/2`. Also works for a medicine's default dose.
- **Medicine days**: 3 / 5 / 7 / 15 / 30 / 60 / 90 / 180 days or any number. Every medicine without its own days
  gets them. The **Follow-up** is set to the same days automatically - but you can change the follow-up on its
  own (e.g. medicines 180 days, follow-up 30 days); changing the follow-up never changes the medicine days.
  "Make same" puts them together again. The same bar is in the Follow-up section. One Undo step for all.
- **Qty** for each medicine is worked out (e.g. 2-2-2 x 30 days = 180 tablets; 2 g x 1-0-1 x 30 days = 120 g)
  until you type your own.
- **Last prescription** card: the patient's previous medicines with **Continue all** or **Continue** for one.
  They are copied into today's prescription to change freely; the old prescription is never changed.

**Medicines**: new types Tablet, Injection, Drops, Powder / sachet (and units vial, ampoule, sachet); new fields
Strength, Medicine code (SKU, with "Extra product details") and Notes. Pack type is always shown.

**Medicine labels** (Additional settings -> Medicine labels, off at the start): a **Labels** button on the
prescription, in the pharmacy dispense popup, after giving medicines and on Sales. Three formats - Compact
50x25 mm, Standard 75x50 mm, Detailed 100x70 mm - with the clinic's default chosen in Additional settings.
Morning / Noon / Night boxes, days and instructions in the patient's language. One switch per optional field
(patient, quantity, times, expiry, batch, price, QR code, doctor, Rx / bill no., date, clinic name).

**Medicine stock switches** (Additional settings -> Medicine stock, ON at the start = how it worked before):
batch tracking, expiry tracking, purchase price, selling price / MRP, supplier management. Switching one off
hides it everywhere (batch off = automatic batch per expiry month). Pharmacy bills need selling price / MRP.
Stock tracking itself is still the "Pharmacy and stock" module in Settings -> Modules.

Existing patients, prescriptions, medicines and stock are unchanged (only new, optional fields were added).
Built on the Git branch `feature/rx-followup-labels` in small steps.

## Step 6: OPD billing, bill preview, OPD dashboard (2026-10-05)

**OPD bill (out-patient)**
- **Fees & services** (menu, admin): each doctor's *New case* fee, *Follow-up* fee and how many days a follow-up
  counts (e.g. 15). A **Services & charges** list (procedures, Panchakarma, tests, certificates) with prices,
  GST % (usually 0 - ask your CA), SAC code and a branch's own price. 8 SAMPLE services with made-up prices.
- **At check-in**: after the token message, *Next: OPD bill* opens the bill with the right fee already filled
  (New case or Follow-up, from the patient's last visit to that doctor). Take cash / UPI / card or *Pay later*.
- **After the check-up**: the doctor clicks **Rs OPD bill** on the check-up screen and adds procedures or other
  charges to the **same** OPD bill. Doctors only add charges; reception collects the money.
- The **Appointments** list and the **Queue** show each patient's bill: *Bill* / *Paid* / *Due Rs*.
- **Billing** (menu): all OPD and pharmacy bills of the day with a filter, payments, cancel (credit note) and the
  day closing. *New OPD bill* for a patient without an appointment.
- Bill numbers: `MAIN/OP/2026-27/00001` (OPD) and `MAIN/PH/...` (pharmacy), new series each April.
- A bill with only GST-free items prints as **BILL OF SUPPLY**, with GST as **TAX INVOICE** (confirm with your CA).
  OPD bills say "OPD BILL (Out-patient)", the consultant and the token.

**Medicines: separate or one combined bill** - your choice in **Additional settings -> Billing**:
off = the pharmacy makes its own bill (default); on = medicines are added to the patient's OPD bill.

**Confirm and preview on the same screen**
- Every bill shows a **Please confirm** box (what will be billed and what money is received) before saving.
- Bills open in a **preview popup** on the same screen (no new browser tab): paper A4 / A5 / thermal 80 mm,
  Download, Print. Looking at the preview is not counted as a print.

**Dashboard in OPD words**: *My OPD today* for doctors (Waiting, With me now, Seen, Total, Next patients),
*Clinic OPD today* for the front desk, new cases vs follow-ups, and today's OPD / pharmacy collection and
what is still to collect.

**IPD** (admitted patients, beds, discharge) is not built - it is kept for a later step; bills already have an
OPD/IPD type so it can be added without changing old bills.

Built on the Git branch `feature/opd-billing` in small steps (each can be undone on its own).

## Additional settings: optional extra features (2026-10-05)

The pharmacy extras added today are now **optional**. A new menu item **Additional settings** (organization
admin only) has one ON/OFF switch per extra, for the whole clinic group. All are **off** at the start, so a new
clinic sees the simple pharmacy and turns on only what it needs.

Always there (with the Pharmacy module on): To dispense, Stock by batch (with corrections and history),
Purchases, Suppliers.

Switches: Pharmacy bills / payments / printing - Discounts (needs bills) - Sales returns - Sell loose - Racks and
shelf locations - Barcodes and scanning - Detailed purchase entry - Opening stock - Returns to supplier -
Stock alerts - Stock ledger screen - Physical stock check - Extra product details.

Switching off only **hides** a feature: nothing saved is deleted. Without bills, "Give" just gives the medicines
and lowers the stock (as in the first version). The server also refuses a switched-off feature.

This work was done on the Git branch `feature/optional-pharmacy-features` in small steps, each of which can be
undone on its own.

## Pharmacy stock, inventory and billing (2026-10-05)

**Products** (Medicines screen): generic name, category, pack type and size, units per pack, "sell loose"
(e.g. single tablets), selling price, barcode.

**Stock by batch**: every batch keeps its own batch no., manufacture and expiry month, purchase rate, MRP,
selling price, GST and supplier. Medicines are given from the batch that expires first (FEFO).

**Racks and shelves**: make racks (A, B, C...) in **Racks & suppliers**; give each medicine a rack, shelf and box
on the **Stock** tab. The location is shown when dispensing, in stock checks and on the stock list.

**Purchases**: supplier, supplier invoice no. and date, freight; per line: batch, barcode, mfg / expiry, quantity,
**free quantity**, purchase rate (without GST), discount, GST, MRP, selling price. Scan a barcode to add a line.
**Opening stock** for the stock you already have. **Return to supplier** from a batch.

**Stock ledger**: every movement with the running balance - opening, purchase, free, sale, sale return,
supplier return, damaged, expired, correction, stock check.

**Alerts**: out of stock, low stock (your level per medicine), expiring within 90 days, expired - on the Stock
tab and on the Dashboard.

**Stock check** (physical verification): count a rack or everything; the differences are corrected and recorded.

**Dispense and bill** in one step: choose batches (FEFO pre-selected), scan, loose units, discount per line or on
all, take payment (cash / UPI / card / pay later). A **pharmacy bill** is made (number like
`MAIN/PH/2026-27/00001`, a new series each April). **Bills** tab: day totals and cash in hand, take payment,
cancel, print (A4, A5, 80 mm thermal; reprints say DUPLICATE COPY), UPI QR code.

**Sales returns**: tick the medicines brought back (sellable ones go back to stock, damaged ones do not); a
**credit note** is made and the refund recorded. Bills are never deleted.

**Settings -> Branch details**: address, GSTIN, drug licence no. and UPI ID printed on bills.

Decisions: loose sale = yes (units per pack); over-the-counter sale without prescription = skipped for now;
pharmacy bills are a separate "PH" series, ready to be combined with the clinic bill in Step 6; purchase orders
later. **GST rates and bill wording must be confirmed with your CA.**

## Pharmacy - first version (2026-10-04)

Built from docs/FEATURES.md section G as a **first draft for the owner to correct**.
- New **Pharmacy** menu (pharmacist, admin). The module is on by default (Settings -> Modules).
- **To dispense**: the day's final prescriptions of this branch. Dispense gives the medicines from the batch with
  the **earliest expiry** (FEFO); expired batches are never offered; you cannot give more than is in stock;
  free-text medicines are shown but not taken from stock. Status: To give / Partly given / Given.
- **Stock**: one row per medicine with available packs, nearest expiry, *Soon* / *Expired* / *Low* tags,
  a per-branch **low-stock level**, the batches inside, **Correct** (with a required reason) and the full
  **stock history** (every + and -).
- **Purchases**: enter a supplier invoice (batch, expiry month, quantity, purchase rate, MRP); stock goes up.
- **Suppliers** list. New permission "Add purchases and suppliers, correct stock" (pharmacist and admin).
- Not yet: branch-to-branch transfer (waits for multi-branch), billing of dispensed medicines (Step 6).
- 8 new automated tests.

## Step 5 - Medicines and prescriptions (2026-10-04)

**Medicines screen** (pharmacist, admin; doctors can look)
- Classical medicines (AFI / API name and reference) and Patent & Proprietary brands (manufacturer, link to the
  classical equivalent), with Gujarati and Hindi names and synonyms. Search finds any name, synonym or ingredient.
- Dosage form, composition, pack size, Ayush licence no., HSN, GST %, price, the usual dose (dose, unit,
  M-N-N, when, anupana) and safety flags (Schedule E1, metals / bhasma, pregnancy, child).
- **Version history**: every change is kept; old prescriptions keep exactly what was prescribed.
- **Branch price** and **In use** switch per branch.
- **Import from Excel or CSV** with a preview first (nothing saved until you confirm) and a template file.
- 23 **SAMPLE** medicines (orange tag) - a pharmacist must verify them. The 3 brands are made up.

**Prescription (Rx) on the check-up screen**
- Search and add medicines; dose, M-N-N, when, anupana are filled from the medicine; add duration and instructions.
- **Safety warnings** (fixed rules, not AI): Schedule E1, metals, long courses, pregnancy (red if the patient is
  pregnant / breastfeeding, a reminder for women 15-49), children under 12, allergies, the same medicine twice.
- **Disease-wise templates**: Save as template / Apply template (matching diagnosis first).
- **Repeat** an earlier prescription from Previous check-ups. Free-text medicines are allowed.
- Autosave, undo / redo work for the prescription too. Completing the visit makes it **final** for the pharmacy.

**Design tidy-up**
- One spacing scale everywhere (12 px between blocks, 8 px between buttons); no extra-large buttons on pages.

**Tests:** 15 new tests (medicines, import, versions, prescriptions, safety rules, templates); all pass.

## Clean-up: one database, sample data (2026-10-04)

- **All old test data was deleted** and replaced by clean **sample data**: clinic "Ayurveda Clinic", one
  "Main Branch", 6 staff (owner, 2 doctors, receptionist, therapist, pharmacist), 5 sample patients and
  today's sample appointments. No more "(Demo)" labels. New password for all sample users: **`Ayur@2026`**.
- Only **one database** now: PostgreSQL in Docker. Removed the no-Docker version (`start-without-docker.bat`,
  the `backend/.venv` folder, 93 MB) and its separate file database, plus two empty folders.
- Fixed: the automated tests had saved 16 test files into the real patient-file storage. They were removed,
  and tests now always use a temporary folder.
- Guides updated (logins, one branch, no-Docker sections removed).

## Step 4 completed - requirement check, autosave, undo/redo (2026-10-04)

**Checked against docs/FEATURES.md and docs/BUILD_STEPS.md (Step 4).** These parts were missing and are now built:
- **Templates editable by the admin** (new **Check-up templates** screen): questions, answers, Gujarati/Hindi text,
  Prakriti scoring (each answer counts for Vata, Pitta or Kapha), switch on/off, add new templates.
  Every change makes a new **version**; old check-ups always show the questions they were filled with.
- **Symptom scores** (0-10 per complaint) and a **Progress** table over the visits (better / worse / same).
- **Before / after photos** in the check-up (private, audit-logged), with a side-by-side before/after view.

**New**
- **Undo / Redo** on the check-up (buttons, Ctrl+Z, Ctrl+Y; Ctrl+S saves at once).
- **Stronger autosave**: if saving fails (e.g. network), the change stays marked "Not saved!" and is retried
  automatically; two saves never run at the same time.
- **Autosave of the patient registration / edit form**: a reload no longer loses the typing. The draft is kept only in
  that browser tab and deleted on logout (privacy on shared computers).

**OPD flow re-checked** (walk-in -> token -> check-up -> complete -> appointment done) and fixed:
- A check-up can no longer be opened for an appointment on a later date.
- The Prakriti badge in the header updates as soon as the questionnaire is saved.
- On small screens the appointment buttons stay visible (pinned on the right).

**Tests:** 5 more automated tests (95 in total), all pass.

## Step 4 - Check-up screen and Ayurveda templates (2026-10-04)

**What you can do now** (layout based on the Healthray check-up screen)
- New **Check-up** menu for doctors: today's patients on the left; click one to open the check-up.
  The appointment moves to "With doctor"; **Complete visit** marks it done.
- Top: patient name, ID, age, token, **allergy alert**, known conditions and the patient's **Prakriti**.
- Section buttons: Summary, Complaints, History & notes, Vitals, **Ashtavidha Pariksha**, **Dashavidha Pariksha**,
  **Agni & daily habits**, **Prakriti questionnaire** (live Vata / Pitta / Kapha score), Diagnosis, Advice, Follow-up.
  A gold dot shows which sections are filled in.
- Complaints, diagnoses (Ayurvedic names; optional NAMASTE / ICD codes) and advice use **search + quick-pick chips**;
  you can also type your own.
- **Saves by itself** a moment after typing stops.
- **Previous check-ups** (from all branches) on the right; the patient file has a new **Check-ups** tab.
- Doctors can start a check-up without an appointment.

**Safety**
- All check-up notes are stored **encrypted**. Opening a check-up is written to the audit log
  (but the medical text itself is never copied into the log).
- Front desk, therapist and pharmacist cannot read check-ups.
- Templates are data (editable), with versions, so old check-ups always show what was asked then.

**Tests:** 11 new automated tests; all backend tests pass.

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
