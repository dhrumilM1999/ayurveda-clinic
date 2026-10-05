# Start here (Windows)

This guide shows how to install, start, stop and log in to the clinic software on your Windows PC.

## 1. Install once

1. **Docker Desktop**: https://www.docker.com/products/docker-desktop/
   - During setup keep **"Use WSL 2"** ticked. Restart the PC afterwards.
   - Open Docker Desktop once and wait until the bottom-left says **Engine running**.
2. **Git**: https://git-scm.com/download/win. It saves versions of your work.
3. **VS Code**: you already have it.

> **Folder location tip:** this project is now in `D:\xampp\htdocs\ayurveda`. That works.
> XAMPP's Apache is **not** used, though. The `.htaccess` file stops Apache from showing these
> files. If you like, move the folder to a simple place such as `C:\Projects\ayurveda-clinic`
> (stop the app first).

## 2. Start the software

Double-click **`start.bat`** in the project folder.

- The **first time**, it downloads a lot. This can take **5–15 minutes**. Later starts take under a minute.
- It creates your settings file `.env` (a copy of `.env.example`).
- When ready, it opens **http://localhost:5173** in your browser.

## 3. Log in (sample users, made-up data)

The software starts with **sample data** for practice: clinic "Ayurveda Clinic", one "Main Branch",
the staff below and 5 sample patients. All names and phone numbers are made up.
Change the clinic name and address on the **Settings** screen.

The password for every sample user is **`Ayur@2026`**

| Username | Who | OTP needed? |
|---|---|---|
| `admin` | Clinic Owner (all access) | Yes |
| `doctor1` | Dr. Asha Mehta (Mon-Sat 10-13, Mon-Fri 17-20) | Yes |
| `doctor2` | Dr. Ravi Patel (Mon-Sat 10-14) | Yes |
| `reception1` | Nita Shah, receptionist | No |
| `therapist1` | Kiran Joshi, therapist | No |
| `pharmacist1` | Meena Desai, pharmacist | No |

**OTP (one-time password):** doctors and admins type a 6-digit code after the password.
No real SMS is sent yet. You can find the code in two places:
- on the login screen, in a yellow box ("Development mode: your OTP is …"), and
- in **`logs.bat`**: look for `SMS (console, not really sent)`.

## 4. Things to try (Step 1 check)

1. Log in as `admin` and enter the OTP.
2. (Only if you switched on **Settings -> Use more than one branch** and added a branch:
   switch branch using the drop-down at the top.)
3. **Change language** to ગુજરાતી (top right). The screen text changes.
4. Go to **Rooms** → **Add room** → save.
5. Go to **Audit log**. Your login and the new room are listed there.
6. Log out, then log in as `reception1`. The menu is smaller, because a receptionist has fewer permissions.
7. Leave the screen untouched for 15 minutes. You are logged out automatically.

### Step 2 check (patients)

1. Log in as `reception1` → **Patients**: 5 sample patients are listed (mobile numbers masked).
2. **Register patient**: type mobile `9811000002`. "Existing patients" warns that this is Sunita Shah.
   Change the number, fill the name, age and gender, tick a condition, add an allergy, then **Register patient**.
3. The new patient gets an ID like `AY26-000006`. A red allergy box shows at the top.
4. **Vitals** tab → **Record vitals** (BMI is calculated). **Consent** tab → withdraw SMS consent.
5. **Medical history** tab: the receptionist sees "Only doctors can see…". Log in as `doctor1` to see everything.
6. Log in as `admin` → open the patient → **Activity** tab: every view and change is listed.

> **One branch for now:** the software works with the Main Branch only. When you open a second branch:
> `admin` -> Settings -> **Use more than one branch**, then add it on the Branches screen.

### Step 3 check (appointments and queue)

1. Log in as `reception1` -> **Appointments**. Today has 2 sample walk-ins (tokens #1 and #2).
2. **Book appointment**: search `Aarav`, choose the doctor and a date when the doctor sits
   (Dr. Asha: Monday-Saturday 10:00-13:00, Monday-Friday 17:00-20:00). Free times are buttons; booked times are crossed out.
   Click a time -> **Book**. The message to the patient is shown, with a green **Send on WhatsApp** button
   (it opens WhatsApp with the text ready; nothing is sent until you press Send there).
3. Try to book the same time for another patient: it is refused (no double booking).
4. Row menu **...** -> **Reschedule** (pick a new time) or **Cancel appointment**.
5. **Walk-in**: pick a patient and doctor -> **Give token**. The patient gets the next token number.
6. **Queue**: one card per doctor. **Call next** finishes the current patient and calls the next token.
7. **TV screen** (on the Queue screen): full screen for the waiting room - press F11. It shows only the token
   and a short name like "Ramesh P.". Move the mouse to the top to see **Exit TV screen**.
8. Open a patient -> **Appointments** tab: their visits, with **Book appointment**.
9. The SMS text is only "logged", not really sent: run `logs.bat` and look for `SMS (console`.
   Patients without SMS/WhatsApp consent (Consent tab) get no messages.

> To add today's sample appointments again, run in the VS Code terminal:
> `docker compose exec backend python manage.py seed_demo --add-sample-appointments`

> **Where is my data?** In Docker's storage boxes (volumes), not in this folder.
> See [HOW_IT_WORKS.md](HOW_IT_WORKS.md#where-is-my-data).

### Step 4 check (check-up screen)

1. Log in as `doctor1` (needs the OTP) -> **Check-up**. Today's patients are on the left.
   (Or as `reception1`: **Appointments** -> **Walk-in** first, so there is a patient waiting.)
2. Click a patient. The appointment turns "With doctor". The top shows allergies and known conditions.
3. **Complaints**: click chips (e.g. *Knee pain*) or type your own and press Enter. Add duration and severity.
4. **Ashtavidha / Dashavidha / Agni & daily habits**: click the answers.
5. **Prakriti questionnaire**: answer the questions; the Vata / Pitta / Kapha score fills in as you go.
6. **Diagnosis** (Ayurvedic names, optional NAMASTE / ICD code), **Advice**, **Follow-up** (after 7 / 15 / 30 days).
7. Everything saves by itself ("Saved" at the top). **Summary** shows the whole check-up. **Complete visit** finishes it.
8. Open the same patient again later: **Previous check-ups** on the right. The patient file has a **Check-ups** tab.
9. Log in as `reception1`: there is no Check-up menu (front desk cannot read medical notes).
10. **Undo / Redo**: the arrow buttons at the top of the check-up, or Ctrl+Z / Ctrl+Y. Ctrl+S saves at once.
11. **Score** (0-10) on each complaint -> **Progress** shows the scores over the visits (better / worse).
12. **Photos**: add *Before* / *During* / *After* photos; once there is a before and a later photo, they show side by side.
13. As `admin`: **Check-up templates** -> **Edit** a template, change a question, **Save** -> version 2.
14. **Patients -> Register patient**: type a name, then press F5 (reload). The form comes back ("Your unsaved form
    was restored"). It is kept only in that browser tab and is removed on logout.

### Step 5 check (medicines and prescriptions)

1. Log in as `pharmacist1` or `admin` -> **Medicines**: 23 SAMPLE medicines (orange "SAMPLE" tag = pharmacist must verify).
   Search by any name, e.g. `Withania` finds Ashwagandha, `ત્રિફળા` finds Triphala.
2. **Edit** a medicine, change the price, save; the **history** button shows version 1 -> 2.
3. **In use** switch: off = hidden from prescriptions in this branch only.
4. **Import** -> **Download template** -> fill it in Excel -> drop the file. You first see a **preview**
   (nothing saved), then click **Import**.
5. Log in as `doctor1` -> **Check-up** -> a patient -> **Rx (medicines)**: search a medicine; dose, times a day
   (morning-noon-night, e.g. 1-0-1), when, anupana come from the medicine. Add the duration.
6. Warnings appear automatically: e.g. *Arogyavardhini Vati* -> Schedule E1 and metals warnings;
   a child or a pregnant patient gets a red warning; an allergy that matches the medicine gets a red warning.
7. **Save as template** (e.g. for Amlapitta) and **Apply template** next time (★ = matches today's diagnosis).
8. In **Previous check-ups** open an old visit -> **Repeat these medicines**.
9. **Complete visit**: the prescription becomes *final* (ready for the pharmacy).

### Step 6 check (OPD billing)

1. Log in as `admin` -> **Fees & services**: check the fees of the sample doctors (made up: Rs 300 new case,
   Rs 150 follow-up within 15 days) and the SAMPLE services. Change them to your real fees.
2. **Appointments** -> **Check in** a patient -> in the token message click **Next: OPD bill**. The consultation fee
   is filled (*New case* or *Follow-up*). Choose Cash -> **Create OPD bill** -> **Yes**. The bill opens on the screen:
   try A4 / A5 / Thermal 80 mm and **Print**.
3. The appointment row now shows **Rs Paid**. Open the check-up (row menu -> Open check-up) -> **Rs OPD bill** ->
   add a service (e.g. Agnikarma) -> *Pay later* -> **Add to bill**. The row shows **Due Rs 500**.
4. **Billing** -> click the bill -> **Take payment**. Try **Cancel bill** on a test bill: a credit note is made.
5. **Dashboard**: see Waiting / With doctor / Seen, new cases vs follow-ups and today's collection.
   Log in as `doctor1` to see *My OPD today* and *Next patients*.
6. Optional: **Additional settings -> Billing -> Medicines on the OPD bill** to give one combined bill.

### Pharmacy and billing check

0. Log in as `admin` -> **Additional settings** -> switch on the extras you want to try (or **Turn all on**).
   With everything off you get the simple pharmacy: To dispense, Stock, Purchases, Suppliers.
1. **Settings -> Branch details**: check the address, add a GSTIN, drug licence no. and a UPI ID (made-up for now).
2. **Pharmacy -> Racks & suppliers**: **Add rack** (code `A`, 5 shelves). **Suppliers** -> add one.
3. **Purchases -> Add purchase**: supplier, invoice no., then a line: medicine, batch, mfg and expiry month,
   quantity, free quantity, rate without GST, MRP. The total with GST shows at the bottom. **Save**.
   Already have stock? Use **Opening stock** instead.
4. **Stock**: the medicine shows the new quantity (bought + free). Click the pencil under **Location** -> rack A,
   shelf 3. Type a **Low-stock level**. Click **+** to see batches (Correct, Return to supplier) and the clock for
   the history.
5. A doctor completes a check-up with an Rx -> **To dispense** -> **Dispense**: tick medicines, change batch or
   quantity, add a discount, choose Cash / UPI / Card / Pay later -> **Give & bill**. Print the bill.
6. **Bills**: the day's totals; open a bill to take payment, print or show the UPI QR code.
7. **Sales & returns -> Return**: tick the medicine, Sellable or Damaged -> a credit note is made.
8. **Stock check -> Start stock check**: type what you count -> **Complete check**: differences are corrected.
9. **Stock ledger**: pick a medicine to see every + and - with the balance. The **Dashboard** shows stock alerts.

## 5. Other addresses

| What | Address |
|---|---|
| The app | http://localhost:5173 |
| Backend API | http://localhost:8000/api/v1/ |
| Django admin (technical admin site, user `admin`) | http://localhost:8000/admin/ |
| Test email inbox (Mailpit) | http://localhost:8025 |

## 6. Stop, logs, reset

| File | What it does |
|---|---|
| `stop.bat` | Stops the app. **Your data is kept.** |
| `logs.bat` | Shows live messages and errors (and login OTPs). Press Ctrl+C to stop watching. |
| `reset-demo-data.bat` | **Deletes all data** and creates fresh sample data. You must type `YES`. Works only while `DEMO_MODE=true` in `.env`. |

## 7. Use only made-up data for now

Until the software is finished and secured (Step 11), **do not enter real patients**.
