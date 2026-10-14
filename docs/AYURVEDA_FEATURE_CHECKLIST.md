# Ayurveda clinic / hospital: feature checklist (for comparing with Healthray)

How to read: **Built** = works today. **Partly** = a first version exists. **Not yet** = missing. **Later** = the owner
said "not now" (see CLAUDE.md section 14). The "Suggested" column is my advice on the order, to discuss.

Reference for the left column: the Healthray OPD screen the owner shared (layout only; no patient data was copied).

## A. The doctor's OPD screen (what the screenshot shows)

| Healthray screen element | Ours | Status | Suggested |
|---|---|---|---|
| Left list "Today's appointments" with date picker, Today / All, search | Appointment list with day picker, search, filter chips with counts | **Built** (2026-10-08) | - |
| Card: time, token, New / Follow-up chip, source (walk-in / booked), due amount | Same: New patient / Follow-up, Walk-in / Booked, waiting minutes, due amount | **Built** | - |
| Walk-in / Teleconsult tabs | Walk-in and booked only | **Later** (teleconsultation is out of scope) | - |
| Patient strip: ID, age, sex, reference, city, due, deposit | ID, age, sex, allergies, known conditions, token, Prakriti tag | **Partly** (no deposit / advance, no city or reference on the strip) | Add city, referred-by, advance deposit (small) |
| Buttons: Bill, Allergy, Reminder, Patient report, Graph | Bill, Print menu (Rx, detailed, case sheet, certificate, follow-up card, Prakriti report), vitals table, Progress (symptom scores) | **Partly** | Add vitals graph, one-click reminder (WhatsApp link) |
| Buttons: Admit, Send order, + Appt, + Patient | Check-up without appointment; follow-up date in the check-up | **Partly** | "+ Appointment" shortcut from the check-up |
| AI Scribe | Planned (module switch exists, not built) | **Not yet** | After the core is stable; doctor must accept / edit / reject |
| Tabs: Summary, Rx, Follow-up, History, Diagnosis, Provisional diagnosis, Advice, Observation, Investigation, Referred to, Images, Comment, Drug | Summary, Complaints, History & notes, Vitals, Ashtavidha, Dashavidha, Agni & habits, Prakriti, Progress, Photos, Diagnosis (provisional / final), Rx, Advice, Follow-up | **Built** (Ayurveda versions) | Investigation orders and "Referred to" are missing |
| Prescription / complaints / vitals summary bars | Summary tab | **Built** | - |
| Drug history, previous weight, BMI, BSA | Medications on the patient file, BMI | **Partly** | - |

## B. Ayurveda-specific (what a general EMR does not have)

| Need | Status | Notes |
|---|---|---|
| Ashtavidha Pariksha (Nadi, Mutra, Mala, Jihva, Shabda, Sparsha, Drik, Akriti) | **Built** | Editable template |
| Dashavidha Pariksha, Agni and daily habits | **Built** | Editable templates |
| Prakriti questionnaire with Vata / Pitta / Kapha score, Prakriti report | **Built** | Sample questions: the doctor should replace them |
| Dosha / Vikriti status, Srotas, Dhatu, Mala assessment sheet | **Partly** | The "Ayurveda case sheet" print has the Agni to Srotas lines; no stored dosha scoring beyond Prakriti |
| Ayurvedic diagnosis list (Amlapitta, Sandhivata ...) with ICD / NAMASTE code | **Partly** | List built; code field exists, official NAMASTE / ICD-11 TM2 list not loaded |
| Classical medicines with AFI reference, Schedule E1 / metals / pregnancy warnings | **Built** | About 150 classical and 3 brands; to be verified by a pharmacist |
| Homeopathy medicines (optional) | **Built** | 818 entries (30C / 200C / 1M, mother tinctures, biochemic) |
| Anupana, timing, dose forms (churna, vati, kwatha, asava, taila ...) | **Built** | - |
| Pathya-apathya (diet and lifestyle advice), diet chart | **Partly** | Advice chips exist; a proper diet chart module is **Not yet** (switch exists) |
| Panchakarma and therapy plans (Vamana, Virechana, Basti, Nasya, Raktamokshana, Shirodhara, Abhyanga) | **Not yet** | Permissions and a module switch exist; no scheduling, therapist or room booking, no session notes, no therapy packages. **Highest-value next module** |
| Therapy room / therapist scheduling, session count tracking, package billing | **Not yet** | Part of the Panchakarma module |
| In-house medicine preparation, raw herb stock, batch of preparations | **Not yet** | Only finished-medicine stock today |
| Yoga / lifestyle plan, exercise log | **Not yet** | Low priority |
| Follow-up cards, follow-up reminders (due list) | **Partly** | Follow-up date and card built; automatic reminder list and WhatsApp reminder not yet |
| Patient photos (before / after) for skin and wound cases | **Built** | Photos tab |
| Medical certificate, fitness, leave | **Built** | Verifiable QR code |

## C. Front desk, billing and pharmacy

| Need | Status |
|---|---|
| Registration with duplicate warning, photo, family contact, referral source, DPDP consent in 3 languages | **Built** |
| Plain number patient IDs | **Built** (2026-10-08) |
| Appointments (slots from doctor timings), walk-in tokens, queue screen, waiting-room TV screen | **Built** |
| Online enquiry from the website, follow-up list | **Built** (2026-10-08, optional) |
| OPD bill (consultation + services), GST fields, UPI QR, cash / UPI / card, day closing, credit notes | **Built** |
| Pharmacy bill, batch / expiry stock, purchases, returns, barcode, labels, stock check | **Built** (counter sale and labels are on the `feature/pharmacy-stock-labels` branch, not merged yet) |
| Separate switches for OPD bill and pharmacy bill | **Built** (2026-10-08) |
| Advance deposit, packages, memberships, discount approval | **Not yet** |
| Insurance / TPA / AYUSH schemes, estimates | **Not yet** |
| Reports (collection, doctor-wise income, new vs repeat, missed follow-ups, GST) | **Partly**: the screen is on branch `feature/step8-reports`, not merged yet |

## D. Hospital (IPD) and platform

| Need | Status |
|---|---|
| IPD: admission, bed and ward board, nursing notes, discharge summary, diet orders | **Later** (explicitly not now) |
| Laboratory / radiology orders and results | **Not yet** (a simple "investigation advised" list would be small) |
| ABHA / ABDM integration | **Later** |
| Patient app / portal, online payment (Razorpay) | **Later** |
| Roles per branch, audit log, 2FA for doctors and admins, masked phone, encrypted history | **Built** |
| Multi-branch, one organisation, branch pricing and stock | **Built** (off by default, one-branch mode) |
| Branding per clinic (name, logo, letterhead print pad) | **Built** (2026-10-07) |
| Backups, hosting, SaaS billing | **Later** |

## Suggested order for the next steps

1. Merge the finished branches (reports screen, counter sale and labels) so everything is in one place.
2. **Panchakarma and therapy module** (plans, sessions, therapist and room schedule, packages).
3. Reminder list (follow-ups, due payments) with WhatsApp click-to-chat.
4. Doctor screen extras: vitals graph, investigation advised, referred-to, "+ Appointment" shortcut, advance deposit.
5. Diet chart and pathya templates.
6. AI scribe, only after the above, with the doctor accepting every line.
