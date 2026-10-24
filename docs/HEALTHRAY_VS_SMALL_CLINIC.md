# Healthray (multi-specialty) vs our small Ayurveda clinic software

Healthray is made for hospitals and many specialities. A small Ayurveda clinic needs only a part of it.
(Healthray's inside screens need a login, so this list is from its public pages and from what we saw earlier. It is a guide, not a full audit.)

## Already in our software
| Need | Where |
|---|---|
| Appointments, walk-ins, token, waiting list | Appointments, Check-up screen |
| Calendar of free / booked days | Calendar (new) |
| Patient file, history, documents, photos | Patients |
| Ayurvedic assessment (Prakriti, Nadi etc.), templates | Check-up |
| Prescription in 3 languages, print / PDF, handwriting pad | Check-up, Prescription |
| Lab tests advised + report upload + print on prescription | Lab tests section (new) |
| Panchakarma / therapy plan and sessions | Therapy |
| Pharmacy stock, labels, barcode, counter sale, expiry alerts | Pharmacy |
| One OPD bill (fee + medicines + therapy), UPI QR, doctor or reception takes payment | Billing |
| Roles, audit log, consent, backups | Admin |

## Worth adding later for a small clinic (in this order)
1. **WhatsApp / SMS reminders** for appointment and follow-up (free click-to-chat first).
2. **Vitals graph** (weight, BP, sugar over time) in the patient file.
3. **Advance / package payment** (e.g. Panchakarma package paid in advance).
4. **Diet chart** (pathya-apathya) printable per patient.
5. **Simple reports**: daily collection, new vs follow-up patients, medicines sold.
6. **Lab tests screen** to rename / switch off tests (API is ready).

## Not needed for a small clinic (skip)
- IPD beds, ward, OT, nursing notes
- Insurance / TPA, cashless claims
- Teleconsultation and video
- Many pharmacy stores, central purchasing
- ABHA / ABDM integration (only if the government asks)
- Lab machine (LIS) connection, radiology (PACS)
- Multi-hospital dashboards and HR / payroll

## Short answer
Our software already covers the daily work of one small clinic. From Healthray, only items 1 to 5 above are really useful. Everything else is for hospitals.
