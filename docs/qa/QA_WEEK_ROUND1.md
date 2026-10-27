# QA round 1 (2026-10-26): the clinic day as the doctor, the front desk and the pharmacy

How it was tested: a sample week was filled (10-20 booked patients a day, 27 Oct to 7 Nov, `python manage.py seed_week_appointments`),
then the real screens were driven like a clinic day: front desk checks patients in, the doctor writes a full check-up
(complaints, notes, vitals, diagnosis, medicine, lab test, advice, follow-up), completes it, prints, takes the fee, the
pharmacy gives the medicine. Every screen was also opened as every role, in English / Gujarati / Hindi, on a desktop and on a phone,
looking for API errors, console errors, raw translation keys and layout that scrolls sideways.

## Bugs found and fixed
| # | What was wrong | Fixed |
|---|---|---|
| 1 | The prescription preview defaulted to A5 and showed a big empty space where the letterhead should be (the clinic letterhead picture worked on A4 only). | The picture now also prints on A5 (same page at 70 %). |
| 2 | The "Ayurveda case sheet" prescription (the design in use) left out the **tests advised** and the **quantity** of the medicine. | Both are printed now. |
| 3 | The handwritten-prescription page (digital pad) still used the software's old letterhead, not the clinic's letterhead picture. | It uses the clinic's letterhead picture. |
| 4 | **The same patient (same name and same mobile) could be registered twice** without any question. The history would split in two. | A question appears: open the existing patient, or register anyway (a different person). |
| 5 | **Complete visit** on an empty check-up marked the appointment done without a word. | It asks first ("Nothing is written. Complete anyway?"). |
| 6 | On a phone the menu took a fifth of the screen and many screens scrolled sideways (appointments, stock, reports, medicine list, billing). | The menu is hidden behind the menu button on a phone; nothing scrolls sideways. |
| 7 | "1 patients" on the calendar. | "1 patient". |
| 8 | Handwritten prescription pictures were not in the patient's history. | New patient tab "Handwritten prescriptions": latest first, with the check-up date, page number and a link to the check-up. |

## Small improvements made while testing as a doctor
- The **reason for the visit** (written at booking) shows inside the check-up, with an "Add as complaint" button.
- After a check-up is completed: **Print prescription** and **Next patient: <name>** buttons.

## Checked and fine
- Booking: Sunday, a time the doctor does not sit, the past, a taken slot, the same patient twice in a day: all refused with a clear sentence.
- Check-up data saves (complaints, vitals, diagnosis, medicine, lab test, advice, follow-up date) and the appointment becomes done.
- Pharmacy: stock goes down by the right amount, the bill lands on the OPD bill, payment is recorded; a confirmation is asked before giving.
- Who can see what: reception, therapist and pharmacist cannot open check-ups, documents, lab tests, audit or error logs; the medical history is hidden from them; phone numbers are masked in lists.
- No raw translation keys and no layout break in Gujarati or Hindi; no API errors on any screen for any role.

## Still to watch (not bugs)
- Full mobile number is visible on a patient's detail page for the therapist and the pharmacist (masked in lists). Say if it should be masked there too.
- Sample "QA" patients (Qatest Patient, ID 50 and 51) are in the demo data.
