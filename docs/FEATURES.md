# Feature List — v1.0.1 (draft, waiting for doctor confirmation)

Phases: **P1** = first version (MVP, multi-branch ready) · **P2** = second version · **P3** = future.
When the doctor confirms, update this file and the version number.

## A. Foundation (P1)
- Multi-branch, multi-doctor structure: Organization → Branch → Rooms → Staff.
- Patients at organization level: one ID, full history at any branch.
- Doctors at several branches, with a schedule per branch.
- Roles: Admin, Doctor, Receptionist, Therapist, Pharmacist, (Patient later).
- Branch-scoped permissions and custom roles.
- Masters central; price and stock per branch.
- Modular monolith, API-first, PostgreSQL; India-region hosting later.

## B. Patients and appointments (P1)
- Doctor-wise slots, walk-in tokens and a queue screen.
- Registration: patient ID (UHID), history, allergies, current allopathic medicines, documents, vitals (BP, pulse, weight, BMI).
- DPDP consent, purpose-wise, in Gujarati/Hindi/English.
- Cancel and reschedule appointments.

## C. Ayurvedic assessment and EMR (P1)
- Prakriti questionnaire with Vata/Pitta/Kapha scoring (saved permanently).
- Vikriti, Agni, Koshta, Sara, Satva, Bala.
- Ashtavidha Pariksha (Nadi, Mutra, Mala, Jihva, Shabda, Sparsha, Drik, Akriti) as quick-select fields.
- Chief complaints, history and diagnosis (optional NAMASTE / ICD codes).
- Visit timeline, progress tracking, symptom scores, before/after photos.

## D. Prescription and medicine master (P1)
- Classical medicines (official AFI/API name) and Patent & Proprietary brands, kept separate; brand linked to classical equivalent.
- Search by Sanskrit, English, Hindi and regional synonyms.
- Dose, anupana (vehicle), timing (before/after food) and duration.
- Disease-wise prescription templates.
- Schedule E1, bhasma, pregnancy, child and allergy warnings.
- Version history, so formulary amendments don't change old prescriptions.

## E. Billing and invoices (P1)
- Consultation, medicines and therapies on one bill.
- GST fields; invoice series per branch and per financial year.
- Cash, UPI and card; UPI QR on the bill.
- Discounts, advances, refunds and credit notes; invoices are never deleted.
- Daily cash closing.

## F. PDF and print (P1)
- Prescription, bill, receipt, Prakriti report, diet chart, therapy plan, consent forms, medical/fitness certificates, case/discharge summary, follow-up card.
- A4, A5 and thermal (80mm/58mm).
- Branch-wise letterhead, Gujarati/Hindi/English, doctor signature, QR verification.
- Share by WhatsApp or email; "DUPLICATE COPY" watermark on reprints.
- Print templates editable from the admin panel.
- Password-protected PDF option for sensitive reports.

## G. Pharmacy and inventory (P2)
- Dispense directly from the prescription; stock reduces automatically.
- Batch, expiry, low-stock alerts, purchases and suppliers.
- Branch-to-branch stock transfer.

## H. Panchakarma and therapy (P2)
- Therapy master; Purvakarma, Pradhanakarma, Paschatkarma stages.
- Room and therapist scheduling with no double booking.
- Session tracking (oil used, quantity, notes, patient response), packages (e.g. 7/21-day) and consent.

## I. Diet and lifestyle (P2)
- Dosha-wise and disease-wise pathya/apathya, dinacharya, ritucharya and yoga/pranayama templates.
- Printable or shareable on WhatsApp.

## J. Communication (P2)
- SMS/WhatsApp appointment confirmations, reminders, follow-up alerts and PDF sharing.

## K. Reports and dashboard (P1 basic, P2 advanced)
- Collection: daily, monthly, yearly (cash/UPI/card separately).
- Income by doctor, branch and therapy.
- GST, stock, expiry, new vs repeat patients, missed follow-ups.
- Branch comparison for the owner.
- PDF and Excel export; large reports built in the background.

## L. Customization and feedback (P1)
- Custom fields, form builder, templates and masters — editable by staff without a developer.
- "Suggest a feature" button on every screen (text/voice note + automatic screenshot), voting, "What's new" screen.
- Feature flags: test a new feature in one branch first.

## M. Security and compliance (P1 onwards)
- 2FA, auto-logout, role and branch access.
- TLS, encryption at rest and extra encryption of sensitive fields.
- Audit log of who viewed, changed, printed or shared what.
- Data masking, daily encrypted backups and restore tests.
- DPDP: consent, patient rights requests, grievance officer, breach plan (full deadline 13 May 2027).
- CERT-In logging, VAPT before launch, ISO 27001 later.
- Data Processing Agreement for clinics.

## N. AI features (P1 / P2 / P3)
AI only suggests; the doctor always makes the final decision.
- **[P1] AI scribe:** doctor speaks in Gujarati/Hindi/English; AI drafts the case sheet; doctor checks and saves.
- **[P1] Patient summary:** 5-line history summary before the consultation.
- **[P2] Prakriti/Vikriti help:** dosha score suggestion from answers and notes.
- **[P2] Prescription suggestions:** from the clinic's own templates and past prescriptions.
- **[P2] Safety check:** allopathic interactions, Schedule E1, bhasma, pregnancy, child, allergy and dose warnings.
- **[P2] Diet chart:** personalised by Prakriti, disease and season, in Gujarati; doctor edits.
- **[P2] WhatsApp AI chatbot:** booking and FAQs in Gujarati/Hindi (no diagnosis).
- **[P2] OCR:** read old reports and prescriptions from photos.
- **[P2] AI follow-up:** "How are you feeling now?" messages; alert the doctor based on replies.
- **[P2] Panchakarma auto-scheduling.**
- **[P3] Pharmacy forecasting:** demand, expiry-first use, auto reorder list.
- **[P3] Reports in plain language:** ask a question, get a report or chart.
- **[P3] Alerts and analytics:** unusual discounts/cash/stock, treatment outcomes, no-show and drop-out prediction.
- **Rules:** AI suggestion and doctor's final decision both logged; separate AI consent; de-identify data; no training on clinic data; per-branch on/off and cost limit.
- **Technical:** separate AI service layer (speech-to-text, OCR, LLM) so providers can be swapped.

## O. Future (P3)
- Patient mobile app and online payment.
- Teleconsultation (per AYUSH telemedicine guidelines).
- ABDM/ABHA integration.
- IPD: beds, rooms, discharge.
- SaaS subscription if sold to other clinics.

## Notes
- DPDP and GST settings to be confirmed with a lawyer and CA before launch.
- Medicine master and Schedule E1 dispensing rules to be reviewed by a qualified Ayurveda pharmacist.
- AI stays a helper for the doctor. Software that assists diagnosis/treatment may come under CDSCO's Software as a Medical Device rules in future — get regulatory advice before launch.
