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

### No Docker yet? Use `start-without-docker.bat`

This uses Python and Node, which are already on this PC, and a simple file database
(`backend\local.sqlite3`) in place of PostgreSQL. It's fine for trying the app with demo data.
- Double-click **`start-without-docker.bat`**. The first time, it downloads packages (a few minutes).
- Two black windows open, "Clinic BACKEND" and "Clinic SCREENS". **Keep them open** while you work.
- **To stop:** close those two windows.
- To start over with fresh demo data: stop it, delete `backend\local.sqlite3`, and start again.
- The Docker way (`start.bat`) remains the proper setup for later (real database, email inbox).

## 3. Log in (demo users, fake data)

The password for every demo user is **`Ayur@Demo2026`**

| Username | Who | Branches | OTP needed? |
|---|---|---|---|
| `admin` | Owner / organization admin | All branches | Yes |
| `doctor1` | Doctor | Ahmedabad + Vadodara | Yes |
| `doctor2` | Doctor | Vadodara | Yes |
| `branchadmin` | Branch admin | Vadodara | Yes |
| `reception1` | Receptionist | Ahmedabad | No |
| `therapist1` | Therapist | Ahmedabad | No |
| `pharmacist1` | Pharmacist | Ahmedabad | No |

**OTP (one-time password):** doctors and admins type a 6-digit code after the password.
No real SMS is sent yet. You can find the code in two places:
- on the login screen, in a yellow box ("Development mode: your OTP is …"), and
- in **`logs.bat`**: look for `SMS (console, not really sent)`.

## 4. Things to try (Step 1 check)

1. Log in as `admin` and enter the OTP.
2. **Switch branch** using the drop-down at the top (Ahmedabad ↔ Vadodara).
3. **Change language** to ગુજરાતી (top right). The screen text changes.
4. Go to **Rooms** → **Add room** → save. Switch branch: that room is not shown in the other branch.
5. Go to **Audit log**. Your login and the new room are listed there.
6. Log out, then log in as `reception1`. The menu is smaller, because a receptionist has fewer permissions.
7. Leave the screen untouched for 15 minutes. You are logged out automatically.

### Step 2 check (patients)

1. Log in as `reception1` → **Patients**: 5 demo patients are listed (mobile numbers masked).
2. **Register patient**: type mobile `9811000002`. "Existing patients" warns that this is Sunita Shah.
   Change the number, fill the name, age and gender, tick a condition, add an allergy, then **Register patient**.
3. The new patient gets an ID like `AY26-000006`. A red allergy box shows at the top.
4. **Vitals** tab → **Record vitals** (BMI is calculated). **Consent** tab → withdraw SMS consent.
5. **Medical history** tab: the receptionist sees "Only doctors can see…". Log in as `doctor1` to see everything.
6. Log in as `admin` → open the patient → **Activity** tab: every view and change is listed.

> Already had the app running before Step 2? `start-without-docker.bat` updates the database
> automatically. To also get the 5 demo patients, run in the VS Code terminal:
> `backend\.venv\Scripts\python backend\manage.py seed_demo --add-demo-patients`

> **One branch for now:** the software shows only the main branch (Ahmedabad demo). The Vadodara demo
> branch is still there, hidden. To see it: `admin` -> Settings -> **Use more than one branch**.

### Step 3 check (appointments and queue)

1. Log in as `reception1` -> **Appointments**. Today has 2 demo walk-ins (tokens #1 and #2).
2. **Book appointment**: search `Aarav`, choose the doctor and a date when the doctor sits
   (Dr. Asha: Monday-Friday 10:00-13:00 in Ahmedabad). Free times are buttons; booked times are crossed out.
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

> To add today's demo appointments again on an existing database, run in the VS Code terminal:
> `docker compose exec backend python manage.py seed_demo --add-demo-appointments`

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
| `reset-demo-data.bat` | **Deletes all data** and creates fresh demo data. You must type `YES`. Works only while `DEMO_MODE=true` in `.env`. |

## 7. Use only fake data

Until the software is finished and secured (Step 11), **do not enter real patients**.
