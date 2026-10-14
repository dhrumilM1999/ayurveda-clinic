# Panchakarma and therapy

For clinics that give Panchakarma and other therapies (Abhyanga, Shirodhara, Basti, Virechana ...). The doctor makes a
**therapy plan** for a patient, the front desk or therapist **books the sessions**, and the therapist **records** each
session (oil used, how the patient felt).

## Turn it on

1. Log in as the owner → **Settings → Modules** → switch on **Panchakarma and therapy** for the branch.
2. A new menu item **Panchakarma** appears for the owner, doctor, receptionist and therapist.
3. First time: open it → **Therapies** tab → **Add the starting list** (27 common therapies in English, Gujarati
   and Hindi). Change names, minutes, usual oil or hide what you do not use.

## The three tabs

| Tab | What it is for |
|---|---|
| **Sessions** | The day's sessions with time, patient, therapy, therapist, room. Buttons: Start, Record and finish, Did not come, Cancel. |
| **Therapy plans** | Patient plans (e.g. "Virechana course"). Open one to see progress and to **Book sessions**. |
| **Therapies** | The clinic's list of therapies (stage, minutes, usual oil, price). |

## Day by day

1. **Doctor / front desk:** Therapy plans → **New therapy plan** → choose the patient, name the plan, add therapies with
   the number of sessions (and tick that the patient agreed).
2. Open the plan → **Book sessions** → pick the days, the start time, a therapist and a room.
   - The same therapist or room is **never booked twice** at the same time (a clear message says who is busy).
   - You cannot book more sessions than planned; raise the number in the plan first.
3. **Therapist:** Sessions tab (today) → **Start** → **Record and finish**: oil/material, quantity (ml), how the patient
   felt, notes. When every planned session is done the plan becomes **Completed**.
4. A patient who did not come: **Did not come** (the slot is shown as missed, book another day).

## Good to know

- Stages: **Purvakarma** (preparation), **Pradhanakarma** (main procedure), **Paschatkarma** (after-care), other.
- The price of a therapy comes from **Services & charges** (Fees & services). Link a therapy to a service in the
  Therapies tab; the plan then shows an estimated total. Billing still happens on the OPD bill as before.
- The therapist's own notes (oil used, response, notes) are stored encrypted like the doctor's notes.
- Nothing is deleted; cancelling a plan cancels its booked sessions and keeps the done ones.
- Therapists see only: Dashboard, Patients, Appointments, Panchakarma, Queue, Rooms (no billing).

## For the person who edits files

- Starting therapies: `backend/apps/therapy/catalog.py` (**SAFE TO EDIT**: name, Gujarati, Hindi, stage, minutes, oil).
- Words on screen: `frontend/src/i18n/{en,gu,hi}.json` under `therapy`.
- Screens: `frontend/src/pages/therapy/` (**ASK FIRST**). Rules (no double booking): `backend/apps/therapy/services.py`.
