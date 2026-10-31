# Changelog

What changed in each step, in plain words.

## main and production joined (2026-10-31)
- The **main** and **production** branches now hold the same code: all clinic work from main, and all live-server work from production (server setup, backups, security, the real clinic profile).
- Login code (OTP) now has **one switch**, `REQUIRE_2FA` (the old name `LOGIN_OTP_ENABLED` is gone). It stays **off on your PC** and is **on by default on a live server**; `.env.production.example` sets it to 0 until e-mail or SMS works.
- Two packages come along from production: **Django REST Framework 3.17.2** (fixes two published security problems) and **gunicorn** (the web server used on the live server only).

## Lists update by themselves (2026-10-31)
- The **Check-up list** (waiting / booked / done counts and patients), the **Appointments** list, the **Queue**, **Give medicines** and the **Dashboard** now ask the server again every few seconds (check-up list 5 s, queue 6 s, appointments 8 s, give medicines 8 s, dashboard 20 s). A new appointment or a completed check-up appears **without pressing refresh**.
- It waits while the browser tab is hidden, refreshes at once when you come back, never sends a new request while the last is still running, and if the server does not answer the list on the screen simply stays as it was (no flicker, no error pop-ups).
- No new package and no Redis needed. Instant push (the same second) would need Redis and a live connection; every few seconds is enough for a clinic.
- Code: `frontend/src/api/liveRefresh.ts` and `useLiveRefresh.ts` (with tests). Frontend only.

## Check-up list colours and counts, Send Order as a switch, Menstrual history template (2026-10-31)
- **Today's appointments** (top of the Check-up list): four round counts, All / Waiting / Booked / Done. Tap one to filter.
- Each patient in the list is **coloured**: waiting = amber, booked but not arrived = blue, done = green (no longer faded). Waiting patients come first, then booked, then done.
- **Send Order** (lab order slip) is now an Additional setting, **off by default**, because no lab is connected. Switch it on in Additional settings -> Prescription.
- New check-up template **Menstrual history (Artava)** with cycle, flow, pain, clots and discharge, in English, Gujarati and Hindi. It is added **switched off**; switch it on in Check-up templates when needed. Other Healthray templates (Homeopathy, Ophthal, Antenatal, Admit/IPD) were left out on purpose.
- Frontend plus one template; no database change.

## Check-up header tools: + Appt, + Patient, Send Order, Patient Report, Graph (2026-10-30)
Looked at Healthray first (layout only), then built five buttons in the check-up header:
- **+ Appt**: book an appointment for this patient without leaving the check-up.
- **+ Patient**: opens the new patient form in a new browser tab (the check-up stays open and keeps saving).
- **Graph**: the patient's vital signs (weight, pulse, temperature, BP, SpO2, breathing, BMI) as small line charts; tick what to show, pick 1 month to all. Drawn by our own code, no new package.
- **Patient Report**: pick two dates and the parts (complaints, history, examination, diagnosis, medicines, tests, advice, next visit): all check-ups in those dates, newest first, all branches. Opening it is written to the audit log (without the medical text). Medicines only for people who may see prescriptions.
- **Send Order**: tick the tests advised at this check-up (or search and add one), write the lab name, mark Urgent, **Print order**: a lab test order slip (A5/A4, in the patient's language, numbered `.../LO/...`, with the QR check). The patient's earlier tests and their report status are listed beside it. New document type `lab_order` (Settings, PDF settings has it too), template `backend/templates/documents/lab_order.html`.
- Backend: `GET /visits/report/`, `GET /documents/lab-order/<visit>/?tests=&lab=&urgent=`. One new migration (documents 0005, only the list of document kinds).

## Stock in tablets on the check-up screen, therapy price from the Therapies screen (2026-10-29)
- The medicine search and the prescription lines now show loose stock in tablets (for example "975 tablets"), the same as the pharmacy screens.
- On the Therapies screen, type a price and the therapy is added to Services & charges and linked for you (only when it has no price yet). Needed for "Bill each finished therapy session".
- Branches `feature/therapy-billing-reminders-sora` and `feature/walkin-after-register-stock-units` were merged into main.

## Left menu: thin strip, opens on hover (2026-10-30)
- The left menu is now a **thin strip of icons**. When the mouse is over it, it opens to full width and floats over the page (the page does not move). When the mouse leaves, it closes.
- The toggle button at the top still opens it fully and keeps it open (the page moves aside, as before). Press again to go back to the thin strip. The choice is remembered on this computer.
- The widths are at the top of `frontend/src/layout/MainLayout.tsx` (MENU_WIDE, MENU_THIN). Frontend only.

## Earlier check-ups below the check-up, full width (2026-10-30)
- On the Check-up screen the patient's earlier check-ups (last visit, history, older visits) moved from the right side to **below the check-up**, and the check-up itself now uses the **full width**. Older check-ups are rows; click one and it **opens right below the row** (no pop-up window), click again to close (as in the Healthray reference). Frontend only.

## Walk-in after registering, patient can come any time, Dose box switch, stock in tablets (2026-10-29)

- **New patient registered -> "Walk-in (Give token)" straight away.** After saving a new patient a small window offers Walk-in, Book appointment or Open patient file. The patient file's Appointments tab also has a **Walk-in** button now.
- **A patient can come at any time:** someone booked for 4 pm who walks in at 11 am is no longer refused ("already has an appointment"): the booking is checked in (one visit, one token). Someone already waiting is still told so. Follow-up or check-up on a different day than the written date was always possible; nothing blocks it.
- **Dose box is switched off by default** (Additional settings -> Prescription -> "Dose box on each medicine in the check-up"). The medicine line shows times a day (1-0-1), when, anupana, days and quantity. The medicine's usual dose (Medicines screen) is still kept, used to work out the quantity, and printed. Switch it on to bring the box back.
- **Stock in tablets for loose medicines.** A medicine with "Can be sold loose" and "units per pack" (for example a jar of 1000 tablets) shows its stock in tablets: give 25 and it reads **975 tablets** (the pack count is in the tooltip) on the Stock screen, and in the batch pick-lists of Dispense and Counter sale. For this the Additional setting "Sell loose (part of a pack)" must be on and the medicine must have units per pack.
- Tests first: new backend tests (walk-in with a booking, stock in units) and a front-end test for the stock text.

## Therapy billing and WhatsApp reminders as switches, Sora font, refund warning (2026-10-28)

Both new features are **off by default**. The owner (or the doctor) switches them on in **Settings -> Additional settings**, so each clinic decides.

- **"Bill each finished therapy session on the OPD bill"** (group Billing, needs OPD bills). When the therapist finishes a session, its price (the service linked to the therapy in Services & charges) is added to that patient's OPD bill of the day (the bill is made if there is none). One bill per patient per day; finish -> undo -> finish again never adds the line twice. A therapy with no price linked is never added.
- **"WhatsApp reminders for appointments and therapy sessions"** (group Reminders). The WhatsApp button on a booked appointment due today or tomorrow now sends a "Reminder: ..." text, and the therapy Sessions list gets a WhatsApp button. Same free click-to-chat as before (staff press Send); only for patients who agreed to messages; English, Gujarati and Hindi. Texts: `backend/apps/appointments/messages_catalog.py` ("reminder") and `backend/apps/therapy/messages_catalog.py`.
- **Sora font for headings and the clinic name** (free, SIL Open Font Licence; file and licence in `frontend/public/fonts`). Body text stays Satoshi. To go back, change `fonts.heading` in `frontend/src/config/clinic.ts`.
- **Refund warning on "Cancel bill":** if the refund way (cash/UPI/card) is more than came in by that way (paid by UPI, refund in cash), a yellow note says so. It is a warning only (giving cash back for a UPI payment is normal at a counter), and the day closing shows it.
- The fixed words of the **bill itself stay English** on purpose (tax paper). Prescription, case sheet, therapy plan, follow-up card, certificates and Prakriti report already print in the patient's language.
- Tests first: new backend tests for the therapy bill, both reminders; new front-end test for the refund check.

## Check-up opens any time, follow-up date highlighted, keyboard shortcuts (2026-10-28)

- **Opening a check-up no longer changes the appointment:** no automatic "With doctor" and no token for a patient who has not arrived. The doctor can open any check-up any time. The status changes only with the Check in / Start / Done buttons; finishing the check-up of a patient who was never checked in checks them in (token) and marks the visit done. The green "With doctor" tag in the check-up header is removed.
- **Follow-up date is highlighted:** an orange "Next visit: Wed, 04-11-2026 - in 7 days" badge in the check-up header and on the Follow-up section (stronger when it is within 3 days, red when it is already past).
- **Keyboard shortcuts.** Check-up: Ctrl+S save, Alt+1..9 / Alt+0 sections, Alt+M find a medicine, Alt+P print, Ctrl+Enter complete, Alt+N next patient, / search the list, ? help. Appointments list: n book, w walk-in, t today, [ ] previous / next day, / search, ? help. A button with a ? icon shows the list. Keys are in `shortcuts.ts` of each screen.
- **No "With doctor" status at all any more.** Booked -> Waiting -> Done. The Start button, the "With doctor" filter, tag, dashboard tile and pill, and the "With doctor" block of the Queue screen are gone; the Queue and the TV show the waiting line in token order with "Next" on the first. Old records of that status show as Waiting.
- **A later day's check-up can be opened and written in advance** (it belongs to that day; it cannot be completed before the day).
- **Patient history straight away:** on the check-up screen the side panel shows the written medical history and the last check-up open (complaints, diagnosis, medicines, advice, next visit) with "Repeat these medicines" - no click needed.
- **Shorter billing:** check-in and walk-in go straight to the OPD bill (token and message result on top, no extra windows); the plain consultation fee collected in full is saved with one click (no "Please confirm"); a changed price, discount, extra service or part payment still asks.
- **Tests first:** new backend tests for the status rules and the first front-end tests (`npm test`, vitest) for the shortcut keys and the follow-up highlight.

## Full-day QA with real-life patients: fixes and safety improvements (2026-10-27)

- **Certificates could not be made** (server error). Fixed: the certificate number is now taken inside one transaction. A new test runs it the way the real server does.
- **Therapist list:** only people whose role has the new permission **"Carry out therapy sessions" (therapy.perform)** can be chosen as the therapist. The Therapist role has it; the receptionist, doctor and owner do not (give it on the Roles screen if the doctor does therapy too).
- **Pharmacy dispense window** now shows the doctor's safety warnings again (pregnancy, child, metals, E1, allergy), so the pharmacist sees them too.
- **New medicine flag "Sugar / jaggery / honey base"** (set for lehya, asava and arishta): a warning when the patient is diabetic. Set on the Medicines screen like the other flags.
- **Medicine search forgives the last letter** (Rasnasaptaka finds Rasnasaptak Kwatha).
- **More starting diagnoses and complaints:** Mutrashmari (kidney stone), Mutrakrichchra, Manyastambha, Vatarakta, and more; complaints Flank pain, Blood in urine, Nausea, Swelling, Morning stiffness. They are added automatically on start.
- **Check-up screen on a phone** was two columns that scrolled sideways: now the list sits on top and the check-up below it.
- **Prescription (Ayurveda case sheet design) in Gujarati and Hindi:** Symptoms, Diagnosis, Advice / Pathya, Next visit, Name, Age/Sex, Date, Wt. and the lines Agni ... Srotas are printed in the patient's language (edit them in `backend/apps/documents/words.py`).
- **Error log** shows plain words (not "ErrorDetail(...)") for refused requests.

## Late appointments and therapy sessions can be moved or cancelled (2026-10-27)

- **Appointments:** a booked appointment whose day or time has gone by shows an orange "Time passed" tag, with **Reschedule** and **Cancel** buttons right on the row (on a phone they are in the ... menu). An appointment marked "Did not come" can now also be rescheduled (it becomes "Booked" again) or cancelled.
- **Dashboard "Needs your attention"** (front desk and doctor): the next 5 appointments, patients whose time passed and who have not arrived (with a link to move or cancel), how many seen patients are not billed yet, and late therapy sessions. Pharmacist and therapist do not see it.
- **Check-up:** typing a complaint, diagnosis or advice that is already in the list (double Enter) is ignored. **Therapy:** a session of a later day cannot be started or finished today (the buttons are hidden and the server refuses).
- **Walk-ins** are listed by the time they were entered (not at the bottom). **Billing day summary** shows what was returned on cancelled bills next to the bills total.
- **Therapy sessions:** a session whose time has gone by, or which was marked "Did not come", has **Reschedule** (new day, time, therapist, room) and **Cancel**. The busy-therapist / busy-room check still applies. Nothing is deleted; every move is in the audit log.

## Pharmacy: safer stock-in and supplier dues (2026-10-25)

- **Expiry date is required** for every batch while expiry tracking is on.
- **Total on the supplier invoice:** type it when you enter a purchase; the software compares it with its own total and shows the difference. More than Rs 1 difference must be accepted with "save anyway"; the purchase list shows what the invoice says.
- **Double clicks:** the same purchase (no invoice number) within 5 minutes, or the same counter sale within 15 seconds, is refused.
- **Supplier dues (new tab):** for medicines bought on credit. Shows what you owe each distributor, what is late (credit days from the supplier), payments (cash / UPI / bank / cheque), part payments, "paid now" while buying, goods sent back as credit, the opening balance, and a full account per supplier. A wrong payment is reversed (never deleted). Only people who can receive stock see it.
- Guide: `docs/PHARMACY_FLOW_AND_SPEC_CHECK.md`.

## Error log, calendar, lab tests (2026-10-24)

- **Error log** (new menu item for the owner): every server error, screen crash, lost connection and refused action, with who, where, how many times, a short code and the steps the person took before it. "Copy for Claude" copies it in plain text. See `docs/ERROR_LOG.md`.
- **Saving no longer shakes the check-up screen:** the "Saved / Unsaved changes" note has a fixed size, so the buttons beside it stay still; the Save button shows a spinner while saving.
- **Lab tests:** the doctor advises tests, adds the report later, and the tests print on the prescription.
- **Calendar:** month view of free and booked days.
- Branch note: this work is on branch `fix/clinic-flow-lab-qa`; `feature/panchakarma` is back to Panchakarma only.

- **Day chips** (medicine days and follow-up): 120 and 150 days added, so the choices are 3, 5, 7, 15, 30, 60, 90, 120, 150, 180 and a custom box.

## Prescribe, give, bill: one tested clinic day (2026-10-24)

- A new full-day test runs the whole flow with every role (front desk, doctor, pharmacist, owner): `apps/common/tests/test_full_day.py`.
- **The doctor sees the pharmacy stock while prescribing:** "In stock: n", "Only n left" or "Not in stock" next to each medicine.
- **Pharmacy queue** shows "n not in stock" for a prescription; the line says "Out of stock"; the rest can be given and the missing one stays open.
- **New alert "Asked for, not in stock"** (Pharmacy, Stock and the dashboard): medicines doctors wrote in the last 30 days that the shelf does not have.
- **Walk-in:** a "Bill the consultation" button right after the token.
- **Medicines on the one OPD bill** is now on by default; the dashboard says so.
- Pharmacy basics now on for a new clinic: stock alerts, opening stock, sales returns, supplier returns, stock check, stock ledger, pharmacy reports.
- Guide for the doctor and staff: `docs/CLINIC_DAY.md`.

## Handwritten prescription with the digital pad (2026-10-24)

- New **Handwriting** button on the check-up screen: write on the iScribe pad (or tablet pen / touch / mouse), see it live,
  press Save. The software keeps the handwriting AND one combined picture (letterhead + patient line + handwriting + QR + signature)
  on that patient's check-up. Print it like any prescription; the pharmacist sees the pages while giving medicines.
  See `docs/HANDWRITING_PAD.md`. New table `HandwrittenPrescription`, new library `pypdfium2` (turns the PDF page into a picture).
- The letterhead on A5 prints no longer lets a long address run under the doctor's name.
## Going live on a server (2026-10-17)

Everything needed to put the software on one Ubuntu server with free HTTPS (guide: `docs/GO_LIVE.md`, tick list: `docs/GO_LIVE_CHECKLIST.md`):
- `docker-compose.prod.yml` + `deploy/Caddyfile`: Caddy (automatic HTTPS, the screens as ready-made files, security headers), the backend run by gunicorn as a normal user, and the database that is **not reachable from the internet**. Only ports 80 and 443 are open. No Redis/Celery/Mailpit (the app does not use them yet).
- `.env.production.example` and `deploy/make-env.sh` (makes the secrets for you, never prints them).
- `create_clinic` command: creates the first clinic, branch and owner login with **no demo data**.
- Backups: `deploy/backup.sh` (14 daily + 8 weekly, checked, with a log, optional copy off the server with rclone/scp), `deploy/restore.sh` (with a safe `--test` practice mode), nightly systemd timer.
- `deploy/server-setup.sh` (firewall, fail2ban, automatic security updates, Docker, swap), `deploy/update.sh` (backup first, `--rollback`), `deploy/status.sh`.
- `create_clinic --profile clinic_profiles/vednath.json` creates the real clinic (Vednath Ayurved, Adajan) with Dr. Grishm Shingala as owner and doctor, and her timings. Git branch `production` is for the server; demo data is saved outside the project for local testing.
- The backend image has a new "production" version (the PC keeps using the old one). `gunicorn` was added to `requirements.txt` (the web server for the live site).

## Safe for the live server (2026-10-17)

See `docs/SECURITY_LIVE.md`. In short:
- Debug is **off unless `DJANGO_DEBUG=1`**. In live mode the software refuses to start with the sample secret key, no encryption key, a `*` host, or login codes that cannot be delivered.
- HTTPS settings (`DJANGO_HTTPS=1`), safe browser headers, no caching of patient data, admin address moved (`ADMIN_URL`) with a login limit, no browsable API.
- Doctors/admins' login code can go by **e-mail** (`TWO_FACTOR_METHOD=email`) or be switched off temporarily (`REQUIRE_2FA=0`); the code is never on screen or in the log in live mode.
- Logs hide tokens, passwords, OTPs and database values; PDFs only use embedded pictures.
- Resetting a staff password logs that person out everywhere.
- Demo commands refuse to run on the live server. New command `check_production_ready` (PASS / WARN / FAIL list).
- Security fix in a library: Django REST framework 3.17.2. New tests walk every API address.

## Testing "by mistake" cases (2026-10-15)

About 150 new tests for wrong input, double clicks, the wrong option and the wrong person (`docs/MISTAKE_PROTECTION.md`).
Problems found and fixed:
- Giving the same medicine twice from one prescription (double click on "Give") sold the stock twice. Now refused.
- A bill line with a negative price or a discount over 100% was accepted. Now refused.
- A follow-up date before the check-up (wrong year) was accepted. Now refused.
- An admin could switch off their own account or the last admin. Now refused.
- Adding a service with an existing name, a wrong id in a link, or a hidden control character in a search crashed the server (500). Now a clear message.
- A completed check-up could not be reopened after a mistaken "Complete visit". New **Re-open check-up** (until the pharmacy gives medicines); a prescription line that was already given can no longer be removed or changed.
- When the server was off, lists looked empty ("No patients yet"). They now say "Could not load this list" with Try again.

## Undo for small mistakes (2026-10-15)

- A small **Undo** (back-arrow) button for wrong clicks: on the **Appointments** row it goes back one step (Waiting
  to Booked, With doctor to Waiting, Done back, Did not come, Cancelled back to Booked); a booking made by mistake can
  be removed from the row menu ("Undo this booking", no message goes to the patient). On the **Panchakarma sessions**
  list it takes a session back (Done to In progress, In progress to Booked, Did not come / Cancelled to Booked); what
  the therapist already wrote is kept.
- Limits (so nothing odd happens later): within **60 minutes** of the last change, never after the check-up is finished
  (re-open the check-up instead), and a walk-in has no earlier step (cancel it). Nothing is deleted, every undo is in
  the audit log. Bills are not touched.

## Search while you type (2026-10-15)

- Every search box now shows results **while you type** (about 0.3 second after you stop). No need to press Enter
  (Enter still works, and the little x clears the box and shows everything again). A small spinner shows while it
  searches. Old, slower answers can never replace newer ones, and Gujarati/Hindi typing waits until the letter is finished.
- Screens: Patients, Appointments, Medicines, Pharmacy (Bills, Stock, Sales, Purchases), Online enquiries, Therapy plans,
  Staff, Branches, Audit log, and the patient / medicine pick-lists (booking, prescription, counter sale).
- Patient search: every word may match a name part, the patient ID or part of the mobile number ("bhavin 456").
  Medicine search: names that start with what you typed come first.
- The audit log now records a patient search at most once every 5 seconds per user, so typing does not flood it.
- Code: one shared piece, `frontend/src/components/LiveSearch.tsx`. See docs/SMALL_CHANGES.md "How search works".
## Translate button: English -> Gujarati and Hindi (2026-10-15)

- A **Translate** button next to the English / Gujarati / Hindi boxes of medicines, services, therapies and check-up
  templates (name, description, every question and answer). It fills Gujarati and Hindi as a suggestion you can edit.
- Free and private: it uses Ollama on your PC. Without Ollama it says "AI is offline" and nothing else breaks.
  Setup in `docs/SMALL_CHANGES.md`. No database change, no new package.

## PDF settings: one screen for how every print-out looks (2026-10-15)

- **New screen "PDF settings"** (left menu, for the admin). Change colour, text size, paper, margin, the letterhead,
  an extra top / bottom line, signature box, QR code, DUPLICATE COPY, language and doctor registration number for all
  documents at once (General tab) or for one document only (Prescription, Follow-up card, Prakriti report,
  Certificate, Therapy plan, OPD bill, Pharmacy bill, Credit note, Medicine label, Stock label, Reports). On bills you
  can also hide the HSN / batch / GST columns and add terms and conditions and a thank-you line.
- **Live preview** on the right: the real PDF made by the server with your changes before you save. It uses your newest
  real record (this is written to the audit log) or a clearly fictional sample. Switch paper, language and "show as
  reprint". **Save** applies it to real print-outs; **Back to default** removes your changes in the open tab.
- With more than one branch you can set "All branches" or "Only this branch". The branch wins.
- The print windows now open with the paper you chose for that document.
- Nothing changes until you edit something: the starting values are the old look. The Ayurveda case sheet stays one
  fixed A4 page (it follows colour, logo, signature, QR and DUPLICATE, not text size or margin).
- Database: one new small table (`documents_printsetting`) that stores only the things you changed.
  Old tables are untouched. See `docs/SMALL_CHANGES.md` -> "Change how all PDFs look".
## Pharmacy reports and held bills (2026-10-15)

- Compared our pharmacy with Healthray Pharmacy (see `docs/PHARMACY_HEALTHRAY_COMPARE.md`). We already had most small-clinic
  features (alerts, reorder level, batches and expiry, counter sale, returns, ledger, stock check), so only the gaps were built.
- New **Reports** tab in the Pharmacy: *What to buy* (medicines at or below their reorder level, with a suggested quantity),
  *Daily pharmacy report* (bills, discount, returns, cash / UPI / card received, purchases), *Top selling*, *Slow / non-moving*,
  *Margin* and *GST of pharmacy bills*. Switch: Additional settings -> "Pharmacy reports" (off by default).
- Counter sale: **Hold** a bill and resume it later (kept in this browser only). Switch: "Hold a counter bill" (off by default).
- No database change. Not built on purpose: supplier dues / purchase payments (needs new fields - owner to decide),
  multi-store transfer, insurance, purchase orders.

## Ayurveda case sheet: 7 medicines fit, English labels (2026-10-11)

- Each medicine now takes two lines (name and dose, then Morning-Noon-Night boxes, days and how to take it), so up to
  7 medicines with notes, advice and the next visit fit above the QR code and signature. Before, a busy prescription
  could run under the signature or be cut off at the bottom of the page without any warning.
- The headings and the check-up lines are now in English: Symptoms, Diagnosis, Advice / Pathya, Next visit, and
  Agni ... Srotas. Change the words in `backend/apps/documents/words.py` (SAFE TO EDIT).
- The Date underline no longer runs past the right edge of the page.

## Panchakarma and therapy (2026-10-15)

- **New module** (Settings, Modules, switch on "Panchakarma and therapy"): a list of therapies (27 starting ones in
  English, Gujarati and Hindi), patient therapy plans with the number of sessions of each therapy, booking sessions
  with a therapist and a room (never double booked), and the therapist's record of each session (oil, quantity, how
  the patient felt). Receptionists can book; therapists see only what they need. See `docs/PANCHAKARMA.md`.
- Merged earlier branches into one: pharmacy stock labels and counter sale, and the Reports screen.

## Clinic v2 (2026-10-08)

- **Patient IDs are plain numbers** (1, 2, 3 ...): no leading zeros, no year. Existing patients were renumbered in the
  order they were registered. An optional prefix in Settings still works (AY -> AY44).
- **One doctor:** Dr. Grishm Shingala (demo data and timings 9-1 and 5-8, closed Sunday). Command `use_single_doctor`
  moves other doctors' records to him and switches them off.
- **Billing switches** in Additional settings: **OPD bills** and **Pharmacy bills**, both ON by default. Off: the related
  buttons, the OPD collection card and (if both are off) the Billing menu are hidden; nothing is deleted.
- **Doctor's appointment list** (Check-up screen): day picker with previous/next day, search, filter chips with counts
  (All, Waiting, With doctor, Booked, Done), New patient / Follow-up tag, Walk-in / Booked tag, waiting minutes, due amount.
- **Online enquiry** (new, optional, Additional settings): a public form for the clinic website (`/enquiry`, three
  languages, spam control, consent) and an **Online enquiry** screen for the front desk (status, notes, call, WhatsApp,
  register patient). See `docs/ONLINE_ENQUIRY.md`.

## Print sizes: half-A4 (A5) fixed (2026-10-07)

- A normal prescription (up to about 9 medicines) now stays on **one half-A4 (A5) page**. Before, the last medicines
  went onto a second page because "1 tsp" and "15 days" wrapped onto two lines. The medicine table is tighter on A5/A6.
- The **Ayurveda case sheet** used to print on a full A4 sheet even when half-A4 was chosen. Now it shrinks to fit
  half-A4 (one page, same layout). Other sizes still print on A4.
- New tests keep these sizes from breaking again (`apps/documents/tests/test_print_sizes.py`).

## More demo data (2026-10-07)

- **Medicine catalog:** about 130 more generic Ayurvedic medicines and 818 homeopathy medicines (remedies in potencies
  such as 30C / 200C / 1M, mother tinctures, the 12 biochemic salts, ointments). New medicine kind **Homeopathy**, shown
  only when **Additional settings -> Homeopathy medicines** is on (off by default). Command: `add_medicine_catalog`.
- **Demo patients:** `seed_demo_journey` creates 36 fictional patients and walks each through registration, the
  check-up, prescription, OPD bill, payment and pharmacy sale, so the dashboard, queue, reports and history have data.
- All entries are samples for a pharmacist / doctor to verify; no real patient data.

## Branding follows the clinic (2026-10-07)

- The clinic's **own name and logo** (Settings -> Clinic details) now show in the left menu, on the login screen
  (also on a phone), on the waiting-room TV screen, on the bill-verify page and in the browser tab. Nothing about a
  clinic is written in the code any more, so each clinic has its own look.
- A wide logo sits on a white plate so it stays readable on the dark green. Without a logo, the default leaf and the
  clinic name are shown as before.
- New public pages for the login screen (they show only the clinic name and logo): `/api/v1/branding/` and
  `/api/v1/branding/logo/`.
- Changing the name or logo in Settings updates every screen at once.

## Ayurveda case sheet prescription - like our own pad (2026-10-07)

- New **Prescription design** (Settings -> Branch details): **Ayurveda case sheet (A4)**, one A4 page laid out like the
  clinic's printed pad: clinic name / logo and the line under it, doctor with qualification and reg. no., clinic phone,
  green timings bar with the holiday note, Name / Age-Sex / Date / Wt, लक्षण and निदान, the अग्नि ... स्रोतस lines
  (filled from the check-up when answered, otherwise blank for writing), Rx with Morning-Noon-Night boxes, advice,
  next visit, QR code, signature, shloka, services band and address.
- The clinic's details from its pad were filled in (name, subtitle, address, phone, timings, Sunday closed, services,
  shloka). Change them any time in Settings.
- With **Print on our pre-printed pad** switched on, the top and bottom are left blank for the pad's own printing.

## Detailed prescription, pre-printed pad, clinic logo (2026-10-06)

- **Detailed prescription** (Check-up -> Print): the whole check-up on paper - vitals, allergies, known conditions,
  other medicines, complaints with how long, history notes, every examination form (Ashtavidha, Dashavidha, Agni...),
  Prakriti result, diagnoses with codes - then the medicines, advice and next visit. A4 or A5, English / Gujarati /
  Hindi, Download (PDF export) and Print. Same Rx number and QR code as the normal prescription. Only staff who may
  see the full medical history can print it.
- **Pre-printed pad** (Settings -> Branch details -> Prescription paper): when switched on, prescriptions print no
  letterhead of their own and leave blank space at the top (default 45 mm) and bottom (20 mm) of every page for the
  clinic's own printed pad. Measure the pad and change the mm.
- **Clinic logo** (Settings -> Clinic details): upload / change / remove (PNG or JPG). Switches for where it
  prints: prescriptions, certificates and reports, and bills and receipts (bills now show the logo too).
## Pharmacy stock labels, scan to bill, counter sale (2026-10-06)

- **Pharmacy stock labels** (Additional settings, new switch): labels for medicine packs on the shelf - medicine,
  strength, pack, MRP, GST %, batch, expiry and a **barcode**. No patient details. Small 50 x 25 mm or large
  75 x 50 mm. Print from Stock -> a batch -> **Labels** (one per pack). A batch without a barcode gets a clinic code.
- **Scan to bill**: scanning a label at the pharmacy adds that exact batch with its price and GST.
  - In a prescription sale, a scanned medicine that is not on the prescription is added to the same bill.
  - New **Counter sale** tab (new switch) for walk-in customers without a prescription: scan or search, optional
    name and mobile, cash / UPI / card / pay later, bill and print. Shows in Sales with a "Counter sale" tag;
    returns work as usual.
- **Schedule E1** medicines are never sold without a doctor's prescription (fixed rule).
- The old labels are now called **Patient medicine labels** and are switched off for this clinic (switch them on
  again in Additional settings if wanted). Nothing was deleted.
- Database: a sale may now have no prescription (counter sale); customer name and mobile were added.
  Existing sales are unchanged.
- New package: `python-barcode` (draws the barcodes).
## Step 8: Reports (2026-10-06)

- New **Reports** screen (left menu) with six reports, for any dates (quick choices: Today, Yesterday, This month,
  Last month, This financial year):
  - **Collection**: money received by Cash / UPI / Card, refunds and net, day-wise or month-wise. Same figures as
    the daily closing.
  - **Income by doctor**: consultation, services & therapy, medicines, round off, billed (after returns), received
    and still due. Pharmacy bills count for the doctor who wrote the prescription.
  - **Income by branch**: the same per branch (shows only with more than one branch).
  - **New vs repeat patients**: check-ups, patients, new cases, follow-ups and repeat %, day-wise or month-wise.
  - **Missed follow-ups**: follow-up date passed and the patient has not come back (any branch). Phones masked.
  - **GST summary**: per HSN / SAC code and GST rate: taxable value, CGST, SGST, minus credit notes. Check with your CA.
- **Excel** and **PDF** download of every report. Every download (and every look at Missed follow-ups) is in the
  audit log.
- **Branch choice**: this branch, another branch you work in, or All branches.
- **Permissions**: "See reports" plus the data's own permission (bills / appointments / patients) in each branch.
  Admin and Doctor have Reports at the start; give it to others on the Roles screen.
- The **Dashboard** already shows today's patients, collection and queue (built in Steps 3 and 6).
- Not done yet: Excel / PDF headings are in English only; very large reports in the background (later, Step 16);
  stock and expiry reports are on the Pharmacy screen.

## Share mode and demo video captions (2026-10-06)

- **`start-share.bat`**: double-click to open the clinic software from a phone or another laptop on the **same
  Wi-Fi**. It prints the address to type on the phone. Only the screens are opened to the Wi-Fi; `start.bat`
  goes back to private mode (this PC only).
- **`demo-video/`**: English, Gujarati and Hindi captions for the demo video. The video files themselves are kept
  only on the PC (too big for Git).

## Step 7: print-outs - prescription, certificates, follow-up card, Prakriti report (2026-10-06)

- **Print menu** on the check-up screen: Prescription (A5 or A4), Follow-up card (A6), Prakriti report,
  Medical / fitness certificate, and **Share prescription on WhatsApp** (as text, only with the patient's
  message consent). Unsaved changes are saved first; everything opens in a popup on the same screen with paper
  size and language (the patient's language by default: English / Gujarati / Hindi).
- **Letterhead** on every print-out: clinic logo and name, branch address and phone, doctor's qualification and
  registration no., the doctor's **signature image** (Staff -> the doctor -> Signature) and a footer line
  (Settings -> Branch details).
- **Prescription**: today's vitals, complaints, diagnosis, medicines with Morning / Noon / Night boxes, days,
  quantity, instructions, diet & lifestyle advice, next visit. Numbered MAIN/RX/2026-27/00001 at the first print.
- **Certificates**: medical (rest from - to) or fitness (fit from); numbered MAIN/MC/...; never deleted, only
  cancelled.
- **QR code** on each print-out opens a public page "Is this document genuine?" (number, date, clinic, doctor,
  patient initials - no medical details). Cancelled certificates show as cancelled.
- **DUPLICATE COPY** from the second print; looking at the preview is not counted. Every view, print and share
  is in the audit log.
- Bills and receipts: thermal **58 mm** as well as 80 mm.
- Not done yet: background jobs (Celery / Redis) - PDFs are made in under a second, so they are not needed yet;
  they will come with SMS / WhatsApp reminders. Editing templates from the screen (they are files for now).

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

## Stock alert on WhatsApp, practice robot, reports, Satoshi font
- Medicines with 5 packs or fewer are "low" (change STOCK_LOW_DEFAULT in .env). The Stock screen has a button
  "Send stock alert on WhatsApp": it opens WhatsApp with the message typed (number: STOCK_ALERT_WHATSAPP in .env); you press Send.
- `start-bot.bat`: a practice robot that sees today's sample patients like a real clinic day (check-in, fee, check-up, prescription, medicines).
- Reports: financial year picker, month-wise summary, GST to pay, sales and purchase registers, bills not paid.
- Satoshi font in the app and on all print-outs; dashboard shortcut buttons.
- Software brand renamed from AyuSutra to **Klinvexa**, new lotus + pulse mark (no letters). The clinic logo is no longer in the menu (it stays on the dashboard greeting box and on print-outs). See docs/BRANDING.md.
