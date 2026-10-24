# Ayurveda Clinic Management Software --- Full QA Checklist

**Purpose:** End-to-end quality assurance checklist for the Ayurveda
clinic management software described in `CLAUDE.md`, including the
owner's additional pharmacy and prescription requirements.

**Project baseline from `CLAUDE.md`** - Backend: Python 3.12, Django 5,
Django REST Framework - Authentication: JWT
(`djangorestframework-simplejwt`), Argon2 password hashing - Frontend:
React + TypeScript + Vite, Ant Design - Languages: English, Gujarati,
Hindi (`react-i18next`) - Database: PostgreSQL 16 + pgvector - Runtime:
Docker Compose on Windows + Docker Desktop/WSL2; local development
first - Flow: Appointment → Registration/check-in → Ayurvedic assessment
→ Diagnosis & plan → Prescription / Panchakarma / Diet & lifestyle →
Billing → Follow-up - Organization model: organization → branches →
rooms/staff; patients belong to the organization; visits, appointments,
invoices and stock belong to a branch - Out of scope unless explicitly
approved: cloud hosting, paid APIs, mobile app, teleconsultation,
ABDM/ABHA integration, IPD beds, SaaS subscriptions, ISO 27001 work

## How to use this checklist

-   Mark a test **\[x\]** only after running it and checking the
    expected result.
-   Use fake/demo data only in development and QA. Never use real
    patient data in development tests.
-   Record a defect ID and evidence for every failed test.
-   **Not tested is not the same as passed.** Use `BLOCKED` or `NOT RUN`
    where appropriate.
-   Do not run destructive tests on production or a database containing
    real patient data.
-   Confirm the actual implementation before treating any item as
    implemented. A checklist item is a requirement to verify, not proof
    that the feature already exists.
-   Before a major database, architecture, paid-service or data-deletion
    decision, stop and ask the owner.
-   For any model change, verify a new migration exists; do not edit an
    old migration.
-   Run tests in an isolated test environment and review the results
    before approving fixes.

## Test record template

For each test, record: - **Test ID:** - **Date / tester:** -
**Environment / branch / commit:** - **Status:** PASS / FAIL / BLOCKED /
NOT RUN - **Actual result:** - **Evidence / log / screenshot:** - **Bug
ID / severity:** - **Retest result:**

## Severity guide

-   **P0 --- Critical:** Patient data exposure or cross-organization
    access, data loss/corruption, unsafe unauthorized prescription
    actions, duplicate financial transactions, production secrets
    exposed, or backup cannot be restored.
-   **P1 --- High:** Major workflow broken, incorrect stock/financial
    totals, wrong patient/branch association, prescription/PDF
    materially incorrect, or important security control missing.
-   **P2 --- Medium:** Feature partially broken with a workaround,
    incorrect report/filter, translation issue affecting use, or
    repeated UI problem.
-   **P3 --- Low:** Cosmetic issue or minor usability problem with no
    material data/security impact.

------------------------------------------------------------------------

# 1. Repository, setup and developer workflow

-   [ ] **SET-001** Verify the repository structure matches the
    documented architecture, and identify the actual implemented apps
    and frontend modules.
-   [ ] **SET-002** Confirm the fixed tech stack is used; any proposed
    stack change is presented to the owner before implementation.
-   [ ] **SET-003** Verify `.env.example` contains safe demo values and
    no real credentials.
-   [ ] **SET-004** Verify secrets are loaded from environment
    configuration and are not hardcoded.
-   [ ] **SET-005** Verify `docker compose up` starts the required local
    services from a clean setup.
-   [ ] **SET-006** Verify `start.bat`, `stop.bat`, `logs.bat`, and
    `reset-demo-data.bat` exist and print clear messages; test reset
    only on disposable demo data.
-   [ ] **SET-007** Verify frontend URL `http://localhost:5173`, API
    base `/api/v1/`, Django admin `http://localhost:8000/admin/`, and
    Mailpit `http://localhost:8025` where configured.
-   [ ] **SET-008** Verify Vite polling reload works inside Docker on
    Windows.
-   [ ] **SET-009** Verify `.gitattributes` uses LF for text and CRLF
    for `.bat` files.
-   [ ] **SET-010** Verify `node_modules` is kept in the intended
    container volume and not accidentally mounted from the Windows host.
-   [ ] **SET-011** Verify startup does not depend on undocumented `.sh`
    entrypoint scripts.
-   [ ] **SET-012** Verify documented commands work in Windows
    PowerShell/Command Prompt as described.
-   [ ] **SET-013** Verify the app starts after Docker restart and gives
    understandable errors when a required service is unavailable.
-   [ ] **SET-014** Verify a clean Git status, understandable commit
    history, and a documented rollback approach before risky work.
-   [ ] **SET-015** Verify guide files exist and are updated:
    `START_HERE_WINDOWS.md`, `HOW_IT_WORKS.md`, `FOLDER_MAP.md`,
    `SMALL_CHANGES.md`, `TROUBLESHOOTING.md`, `GLOSSARY.md`, and root
    `CHANGELOG.md`.
-   [ ] **SET-016** Verify editable files contain accurate
    `SAFE TO EDIT` comments and dangerous changes are marked
    `ASK FIRST`.

# 2. Authentication, accounts and sessions

-   [ ] **AUTH-001** Valid user credentials allow login.
-   [ ] **AUTH-002** Invalid username/password is rejected with a safe,
    understandable message.
-   [ ] **AUTH-003** Login is rate-limited after repeated failed
    attempts.
-   [ ] **AUTH-004** Passwords are stored using Argon2 hashing;
    plaintext passwords are never stored or logged.
-   [ ] **AUTH-005** JWT access tokens expire according to the
    configured short lifetime.
-   [ ] **AUTH-006** Refresh-token behavior and logout/revocation
    behavior match the documented security design.
-   [ ] **AUTH-007** Idle sessions automatically log out after the
    configured idle period.
-   [ ] **AUTH-008** Password reset/change works and invalidates
    sessions/tokens as designed.
-   [ ] **AUTH-009** Admin and doctor 2FA/OTP flow is tested;
    development OTP is shown only through the console provider as
    documented.
-   [ ] **AUTH-010** Disabled/inactive users cannot sign in or continue
    using protected APIs.
-   [ ] **AUTH-011** API endpoints reject missing, malformed, expired
    and tampered tokens.
-   [ ] **AUTH-012** Authentication errors do not reveal whether a
    sensitive account exists.
-   [ ] **AUTH-013** Logout prevents further use according to the
    token/session design.
-   [ ] **AUTH-014** User profile and password endpoints validate inputs
    and enforce permissions.

# 3. Organization, branches, rooms and staff

-   [ ] **ORG-001** Create, view and edit an organization.
-   [ ] **ORG-002** Create, view and edit multiple branches under one
    organization.
-   [ ] **ORG-003** Create and manage rooms for the correct branch.
-   [ ] **ORG-004** Assign staff to the intended organization and
    branch.
-   [ ] **ORG-005** A doctor can be assigned to more than one branch.
-   [ ] **ORG-006** Doctor schedules can differ by branch.
-   [ ] **ORG-007** Patient identity is organization-wide and the
    patient can be seen at different branches with the same patient ID.
-   [ ] **ORG-008** Visits, appointments, invoices and pharmacy stock
    are associated with the correct branch.
-   [ ] **ORG-009** Organization-level medicine, therapy, diet and
    questionnaire masters can be overridden at branch level only for
    allowed fields.
-   [ ] **ORG-010** Branch-level price, stock and active/inactive
    overrides do not unintentionally change another branch.
-   [ ] **ORG-011** Current branch is sent in the `X-Branch-ID` header
    where required.
-   [ ] **ORG-012** Invalid, missing or unauthorized branch IDs are
    rejected safely.
-   [ ] **ORG-013** Organization admin can see permitted branches; other
    roles see only their assigned branches.
-   [ ] **ORG-014** Branch switching refreshes lists, dashboards,
    permissions and branch-specific settings correctly.
-   [ ] **ORG-015** Date/time, invoice numbering and reports remain
    scoped to the correct branch.
-   [ ] **ORG-016** Deactivating a branch or staff member preserves
    historical records and does not orphan records.

# 4. Roles, permissions and branch scoping

-   [ ] **PERM-001** Permission codes are defined in the central
    permission catalog.
-   [ ] **PERM-002** Roles are data-managed and can be configured
    through the admin screen as intended.
-   [ ] **PERM-003** Users receive role assignments per branch.
-   [ ] **PERM-004** Admin can perform only the actions allowed by the
    configured role.
-   [ ] **PERM-005** Doctor can access assigned clinical workflows but
    not unauthorized organization settings.
-   [ ] **PERM-006** Receptionist can manage permitted patient
    registration and appointments but cannot access restricted
    clinical/billing data.
-   [ ] **PERM-007** Therapist cannot see billing information unless
    explicitly granted permission.
-   [ ] **PERM-008** Pharmacist can access permitted
    medicine/prescription and pharmacy functions but not the patient's
    full clinical history unless explicitly authorized.
-   [ ] **PERM-009** Hiding a button in the frontend is not the only
    security control; the API also denies unauthorized actions.
-   [ ] **PERM-010** Direct API calls with another branch ID are
    rejected unless the user is authorized for that branch.
-   [ ] **PERM-011** Cross-organization list, detail, search, export and
    update requests return no unauthorized data.
-   [ ] **PERM-012** Permission changes take effect as designed without
    requiring unsafe manual database edits.
-   [ ] **PERM-013** Permission checks apply to PDF, print, export and
    share actions, not only normal screen views.
-   [ ] **PERM-014** Soft-deleted records do not leak through search,
    APIs or reports unless an authorized audit view is intended.

# 5. Patient registration and patient records

-   [ ] **PAT-001** Register a new patient with valid required
    information.
-   [ ] **PAT-002** Required fields, lengths, formats and date values
    are validated by the backend.
-   [ ] **PAT-003** Patient IDs are unique within the intended
    organization and are not duplicated by concurrent registrations.
-   [ ] **PAT-004** Search patients by patient ID, name and supported
    phone search.
-   [ ] **PAT-005** Patient phone numbers are masked in lists,
    e.g. `98XXXXXX21`, where appropriate.
-   [ ] **PAT-006** Patient demographic details can be corrected by
    authorized staff and changes are audited.
-   [ ] **PAT-007** Duplicate-patient detection warns staff and supports
    safe resolution without silently merging records.
-   [ ] **PAT-008** A patient's complete history is available across
    authorized branches of the same organization.
-   [ ] **PAT-009** A patient from another organization cannot be
    accessed by changing a URL, UUID or API parameter.
-   [ ] **PAT-010** Patient profile shows correct visits, assessments,
    prescriptions, therapies, diet plans, invoices and follow-ups
    according to permissions.
-   [ ] **PAT-011** Archive/soft-delete preserves legally required
    medical history.
-   [ ] **PAT-012** Medical records are never hard-deleted through
    ordinary application flows.
-   [ ] **PAT-013** Patient list pagination, sorting, filtering and
    empty states work correctly.
-   [ ] **PAT-014** Search handles Gujarati, Hindi and English
    names/synonyms where supported.
-   [ ] **PAT-015** Patient import/export, if implemented, is
    permission-controlled and audited.
-   [ ] **PAT-016** Concurrent edits do not silently overwrite important
    patient changes.

# 6. Consent, privacy requests and grievance handling

-   [ ] **CONS-001** Registration records separate consent for
    treatment, SMS/WhatsApp, AI processing and research.
-   [ ] **CONS-002** Consent text is available in English, Gujarati and
    Hindi.
-   [ ] **CONS-003** Consent records include when and how consent was
    given.
-   [ ] **CONS-004** Patient consent withdrawal is recorded with
    date/time and method.
-   [ ] **CONS-005** Withdrawing optional AI consent prevents subsequent
    AI processing requiring that consent.
-   [ ] **CONS-006** Withdrawing SMS/WhatsApp consent prevents relevant
    promotional/reminder communication according to the configured
    policy.
-   [ ] **CONS-007** Staff can handle patient requests to view, correct
    and erase data.
-   [ ] **CONS-008** Erasure requests respect applicable medical-record
    retention rules; mask/restrict where deletion is not permitted
    rather than hard-delete required records.
-   [ ] **CONS-009** Grievance contact/details are available to patients
    or staff as designed.
-   [ ] **CONS-010** Consent and privacy-request actions are audited.
-   [ ] **CONS-011** Consent state is checked on the backend, not just
    the frontend.
-   [ ] **CONS-012** QA report records which legal/compliance items
    require review by a qualified Indian legal/compliance professional;
    do not claim legal compliance solely because tests pass.

# 7. Appointment, check-in and patient flow

-   [ ] **APT-001** Create an appointment for an existing patient.
-   [ ] **APT-002** Register a new patient as part of the
    appointment/check-in workflow where supported.
-   [ ] **APT-003** Assign the correct doctor, branch, date, time and
    room if applicable.
-   [ ] **APT-004** Prevent or clearly warn about conflicting
    appointments for the same doctor/time.
-   [ ] **APT-005** Support appointment status changes: booked, waiting,
    in progress, completed and cancelled where implemented.
-   [ ] **APT-006** Today's queue displays the correct branch, doctor
    and status.
-   [ ] **APT-007** Reschedule and cancellation preserve history and are
    audited.
-   [ ] **APT-008** A cancelled appointment is not treated as an active
    appointment.
-   [ ] **APT-009** Doctor availability and schedules are checked per
    branch.
-   [ ] **APT-010** Date filters work at day/month/year boundaries.
-   [ ] **APT-011** Concurrent booking attempts do not create unintended
    duplicate/conflicting appointments.
-   [ ] **APT-012** Appointment workflow links to the correct patient
    assessment and visit.
-   [ ] **APT-013** Follow-up/revisit returns the patient to a new
    assessment while preserving prior visit history.

# 8. Ayurvedic assessment, diagnosis and care plan (EMR)

-   [ ] **EMR-001** Start a clinical visit for the correct patient and
    branch.
-   [ ] **EMR-002** Save and reopen Ayurvedic assessment information
    without losing data.
-   [ ] **EMR-003** Diagnosis and care plan are linked to the correct
    visit.
-   [ ] **EMR-004** Assessment history from earlier visits remains
    available to authorized clinicians.
-   [ ] **EMR-005** Clinical fields validate lengths, dates and required
    values.
-   [ ] **EMR-006** Draft and final states behave as designed; unsaved
    work is not presented as final.
-   [ ] **EMR-007** Edits to clinical notes are audited with
    user/time/change information.
-   [ ] **EMR-008** Only authorized clinical roles can create or edit
    assessments/diagnoses.
-   [ ] **EMR-009** Reopening a past visit does not accidentally
    overwrite a newer visit.
-   [ ] **EMR-010** Clinical content is displayed and printed in the
    selected language where supported.

# 9. Medicine master and Ayurvedic medicine safety

-   [ ] **MED-001** Medicine master distinguishes Classical medicines
    from Patent & Proprietary medicines.
-   [ ] **MED-002** Classical medicine includes the official name and
    reference to the applicable Ayurvedic Formulary/Pharmacopoeia
    source.
-   [ ] **MED-003** Patent & Proprietary medicine stores brand,
    manufacturer and composition.
-   [ ] **MED-004** A brand can link to its classical equivalent where
    configured.
-   [ ] **MED-005** Search works using Sanskrit, English, Hindi and
    Gujarati synonyms where entered.
-   [ ] **MED-006** Dosage form supports configured forms such as
    churna, vati, kashaya, arishta, asava, taila, ghrita, bhasma and
    lehya.
-   [ ] **MED-007** Composition, reference, manufacturer, AYUSH licence
    number, HSN and GST rate are stored and validated where applicable.
-   [ ] **MED-008** Safety flags can represent Schedule E1,
    metals/bhasma, pregnancy caution and child caution.
-   [ ] **MED-009** Safety warnings are generated from fixed application
    rules, not solely by AI.
-   [ ] **MED-010** Warnings are visible at the prescribing point and
    cannot be silently lost in the normal workflow.
-   [ ] **MED-011** Authorized users can edit medicine masters;
    unauthorized roles cannot.
-   [ ] **MED-012** Formulation version history is retained.
-   [ ] **MED-013** Old prescriptions continue to show the
    formulation/version actually prescribed at that time.
-   [ ] **MED-014** Inactive medicines are not offered for new
    prescriptions unless an explicit permitted workflow exists.
-   [ ] **MED-015** Master values are loaded from database/master tables
    rather than hardcoded dropdown arrays.

# 10. Prescription creation, dosage and follow-up defaults

-   [ ] **RX-001** Create a prescription for the correct patient, visit
    and doctor.
-   [ ] **RX-002** Add, edit, reorder and remove medicine lines before
    finalizing, according to permissions.
-   [ ] **RX-003** Verify the requested dosage shorthand: entering `222`
    displays `2-2-2` when that format is selected.
-   [ ] **RX-004** Dosage formatting handles supported patterns and does
    not transform unrelated medicine names or text.
-   [ ] **RX-005** Invalid or ambiguous dosage input is flagged instead
    of silently misinterpreted.
-   [ ] **RX-006** Medicine strength, dosage form, route, timing,
    frequency, duration and instructions remain associated with the
    correct medicine.
-   [ ] **RX-007** Follow-up day presets include 3, 5, 7, 15, 30, 60, 90
    and 180 days plus a custom option.
-   [ ] **RX-008** Selecting a follow-up preset sets the initial/default
    value for both follow-up and medicine duration fields as requested.
-   [ ] **RX-009** Doctor can change follow-up timing independently
    after the default is applied.
-   [ ] **RX-010** Doctor can change medicine duration independently
    after the default is applied.
-   [ ] **RX-011** Changing one field after initialization does not
    unexpectedly overwrite the other field.
-   [ ] **RX-012** Custom day values are validated and retained.
-   [ ] **RX-013** Prescription draft, save, edit, finalize and print
    flows work as designed.
-   [ ] **RX-014** Editing a saved prescription does not create
    duplicate medicine lines or duplicate stock movements.
-   [ ] **RX-015** Final prescription identifies patient, doctor, branch
    and visit correctly.
-   [ ] **RX-016** Only authorized roles can finalize or modify
    prescriptions.
-   [ ] **RX-017** Each added optional detail can be enabled/disabled
    according to the requested UI behavior; OFF fields do not silently
    submit stale values.
-   [ ] **RX-018** Label format options show the chosen format
    consistently on screen and print/PDF.
-   [ ] **RX-019** Prescription history is preserved and edits are
    audited.
-   [ ] **RX-020** Medicine safety warnings appear for relevant flags.
-   [ ] **RX-021** Prescription can be printed/shared only by authorized
    users and each action is audited.
-   [ ] **RX-022** Prescription data remains correct when switching
    languages or refreshing the page.

# 11. Pharmacy and batch-wise inventory

> Inventory tracking and advanced pharmacy details may be optional.
> Verify each feature's branch/organization setting. Do not force
> optional tracking on clinics that have disabled it.

## 11A. Product and stock setup

-   [ ] **PHARM-001** Create a product with product name, generic name,
    manufacturer and category.
-   [ ] **PHARM-002** Store dosage/form or pack type and pack size where
    configured.
-   [ ] **PHARM-003** Store batch number, manufacturing date and expiry
    date.
-   [ ] **PHARM-004** Store supplier, supplier invoice number and
    invoice date.
-   [ ] **PHARM-005** Store purchase quantity and free quantity
    separately.
-   [ ] **PHARM-006** Store purchase price, MRP and selling price
    separately.
-   [ ] **PHARM-007** Store GST, HSN, barcode, minimum-stock level and
    rack/shelf location where enabled.
-   [ ] **PHARM-008** Validate dates (expiry cannot precede
    manufacturing date) and numeric quantities/prices.
-   [ ] **PHARM-009** Allow the same product to have multiple batches
    with different expiry, purchase price and MRP.
-   [ ] **PHARM-010** Prevent a batch update from accidentally
    overwriting another batch's values.
-   [ ] **PHARM-011** Branch-specific stock and price overrides do not
    affect other branches unintentionally.
-   [ ] **PHARM-012** Barcode values are unique where the business rule
    requires uniqueness.
-   [ ] **PHARM-013** Barcode scan/search selects the correct product
    and batch workflow.
-   [ ] **PHARM-014** Rack/shelf management can create, edit and search
    configured locations.

## 11B. Purchase, ledger and adjustments

-   [ ] **PHARM-015** Purchase entry increases stock for the correct
    branch, product and batch.
-   [ ] **PHARM-016** Free quantity is included in physical stock
    according to the configured rule without incorrectly inflating
    purchase value.
-   [ ] **PHARM-017** Purchase invoice and line totals are calculated
    correctly.
-   [ ] **PHARM-018** Opening stock entry is recorded with an
    identifiable transaction/audit record.
-   [ ] **PHARM-019** Ledger tracks opening, purchases, sales, returns,
    damaged/expired stock, adjustments and current balance.
-   [ ] **PHARM-020** Ledger movements reconcile to the current stock
    quantity.
-   [ ] **PHARM-021** Manual stock adjustments require an authorized
    user and a reason.
-   [ ] **PHARM-022** Physical stock verification records counted
    quantity, difference, reason and user.
-   [ ] **PHARM-023** Supplier returns reduce the correct batch stock
    and preserve the transaction history.
-   [ ] **PHARM-024** Sales returns add stock only according to the
    configured return/quality rules.
-   [ ] **PHARM-025** Damaged, expired or written-off stock is not
    available for normal sale.
-   [ ] **PHARM-026** Concurrent sales/purchases do not produce negative
    or inconsistent stock.
-   [ ] **PHARM-027** Retrying a purchase or stock API request does not
    duplicate stock movements.
-   [ ] **PHARM-028** Every stock movement records user, date/time,
    branch, source document and reason where relevant.

## 11C. Sale, batch selection and alerts

-   [ ] **PHARM-029** Sale deducts stock from the correct branch and
    batch.
-   [ ] **PHARM-030** FEFO selects the earliest-expiring eligible batch
    first.
-   [ ] **PHARM-031** Expired stock is blocked from ordinary sale.
-   [ ] **PHARM-032** Near-expiry alerts use the configured threshold
    and correct date calculation.
-   [ ] **PHARM-033** Low-stock and out-of-stock alerts match the
    configured minimum and actual available quantity.
-   [ ] **PHARM-034** Batch-specific MRP and selling price are used
    correctly.
-   [ ] **PHARM-035** Pack/unit conversion does not overstate or
    understate stock.
-   [ ] **PHARM-036** A sale cannot silently exceed available stock
    unless a deliberate, authorized policy permits it.
-   [ ] **PHARM-037** Stock reports match the sum of batch ledger
    balances.
-   [ ] **PHARM-038** Stock movements are traceable back to the invoice,
    return or adjustment.

## 11D. Optional feature switches

-   [ ] **PHARM-039** Pharmacy module can be switched ON/OFF by the
    authorized organization/clinic admin as designed.
-   [ ] **PHARM-040** Advanced tracking features have individual ON/OFF
    controls where required.
-   [ ] **PHARM-041** OFF hides/disables the related UI and the backend
    enforces the intended behavior.
-   [ ] **PHARM-042** Turning an option OFF does not delete its existing
    data.
-   [ ] **PHARM-043** Turning an option back ON restores access to
    retained data.
-   [ ] **PHARM-044** Settings in one organization/branch do not change
    another organization's/branch's settings.
-   [ ] **PHARM-045** Optional tracking does not block basic clinic
    workflows when it is disabled.
-   [ ] **PHARM-046** The owner can understand what each switch controls
    from its label/help text.

# 12. Panchakarma, therapies and treatment plans

-   [ ] **THER-001** Therapy master is organization-level and supports
    branch-level allowed overrides.
-   [ ] **THER-002** Create a therapy plan for the correct
    patient/visit.
-   [ ] **THER-003** Record planned date, status, assigned therapist and
    relevant instructions where supported.
-   [ ] **THER-004** Only authorized staff can create or edit therapy
    records.
-   [ ] **THER-005** Panchakarma/therapy module can be switched ON/OFF
    per branch.
-   [ ] **THER-006** When disabled, the feature is not accidentally
    accessible through direct APIs.
-   [ ] **THER-007** Therapy charges flow into the correct invoice
    without duplicate billing.
-   [ ] **THER-008** Therapy plan PDF/print shows correct patient and
    branch details where implemented.
-   [ ] **THER-009** Previous therapy records remain in the patient's
    history.
-   [ ] **THER-010** Missing optional therapy configuration does not
    break unrelated patient workflows.

# 13. Diet and lifestyle plans

-   [ ] **DIET-001** Create and maintain organization-level diet
    templates.
-   [ ] **DIET-002** Apply a diet/lifestyle plan to the correct patient
    and visit.
-   [ ] **DIET-003** Templates and plans support configured English,
    Gujarati and Hindi text.
-   [ ] **DIET-004** Branch overrides behave as intended without
    changing other branches.
-   [ ] **DIET-005** Only authorized roles can create/edit
    patient-specific plans.
-   [ ] **DIET-006** Diet chart PDF/print displays correct patient,
    clinic and language.
-   [ ] **DIET-007** Historical diet plans remain available after a
    template is edited.
-   [ ] **DIET-008** Optional diet module OFF state is respected in UI
    and API.

# 14. Billing, invoices, payments, refunds and cash closing

-   [ ] **BILL-001** One invoice can combine consultation, medicines and
    therapies.
-   [ ] **BILL-002** Invoice lines reference the correct patient, branch
    and source items.
-   [ ] **BILL-003** Quantity × unit price, discount, tax and final
    total calculations are correct.
-   [ ] **BILL-004** GST fields support GSTIN, HSN/SAC, CGST/SGST/IGST
    and place of supply as configured.
-   [ ] **BILL-005** Tax rates are configurable; do not assume a tax
    rate is legally correct without owner/CA confirmation.
-   [ ] **BILL-006** Invoice number is unique per branch and financial
    year (April--March).
-   [ ] **BILL-007** Concurrent invoice creation cannot duplicate
    invoice numbers.
-   [ ] **BILL-008** Invoice numbering is generated safely inside a
    database transaction.
-   [ ] **BILL-009** Cancelling an invoice creates a credit note; the
    original invoice is not deleted.
-   [ ] **BILL-010** Refund creates a traceable credit note/refund
    record and preserves the original invoice.
-   [ ] **BILL-011** Cash, UPI and card payment modes work as
    configured.
-   [ ] **BILL-012** Partial payments, outstanding balances and payment
    history calculate correctly if supported.
-   [ ] **BILL-013** Duplicate/double-click payment submissions do not
    create duplicate payments.
-   [ ] **BILL-014** Daily cash closing works per branch and reconciles
    with cash transactions.
-   [ ] **BILL-015** Refunds and invoice cancellation update pharmacy
    stock only according to the configured policy.
-   [ ] **BILL-016** Billing permissions are enforced for screen, API,
    PDF, export and print actions.
-   [ ] **BILL-017** Invoice totals match reports and the payment
    ledger.
-   [ ] **BILL-018** Failed transactions roll back fully; no half-saved
    invoice/payment/stock state remains.
-   [ ] **BILL-019** Invoice edits and financial adjustments are
    audited.
-   [ ] **BILL-020** Invoice sequence behaves correctly across
    financial-year change and branch change.

# 15. PDF, printing, QR and document templates

-   [ ] **DOC-001** Prescription PDF renders from server-side HTML
    templates using the configured PDF approach.
-   [ ] **DOC-002** Invoice PDF renders correctly.
-   [ ] **DOC-003** Receipt PDF renders correctly.
-   [ ] **DOC-004** Prakriti report, diet chart, therapy plan, consent
    form, certificates and follow-up card render where implemented.
-   [ ] **DOC-005** A4 and A5 paper layouts are correct.
-   [ ] **DOC-006** Thermal 80mm and 58mm layouts fit the intended
    printable width.
-   [ ] **DOC-007** Gujarati and Hindi glyphs render correctly with
    configured Noto fonts; no boxes, missing characters or broken
    conjuncts.
-   [ ] **DOC-008** English, Gujarati and Hindi versions use the
    selected patient's/document language.
-   [ ] **DOC-009** Correct branch logo, address, letterhead and footer
    appear.
-   [ ] **DOC-010** Correct doctor signature image appears only where
    configured and authorized.
-   [ ] **DOC-011** QR verification code resolves to the intended safe
    document-verification flow.
-   [ ] **DOC-012** Reprinted documents show the required
    `DUPLICATE COPY` watermark.
-   [ ] **DOC-013** PDF values match saved database records, not unsaved
    frontend-only values.
-   [ ] **DOC-014** Long content, tables, medicine lists and page breaks
    do not clip important information.
-   [ ] **DOC-015** Templates can be edited in the documented location
    without changing business logic.
-   [ ] **DOC-016** PDF/print events are written to the audit log.
-   [ ] **DOC-017** Unauthorized users cannot obtain a document by
    guessing its URL or ID.
-   [ ] **DOC-018** WhatsApp share creates the expected click-to-chat
    link and does not send automatically.

# 16. Notifications and provider adapters

-   [ ] **NOTIF-001** Every external provider is accessed through the
    intended adapter/interface.
-   [ ] **NOTIF-002** Provider selection is controlled by `.env`
    settings.
-   [ ] **NOTIF-003** Every adapter has a fake provider usable in
    automated tests.
-   [ ] **NOTIF-004** WhatsApp `click_to_chat` builds a correct `wa.me`
    link and prefilled message; staff must tap Send.
-   [ ] **NOTIF-005** SMS `console` provider logs/saves the test message
    but does not claim a real SMS was sent.
-   [ ] **NOTIF-006** Mailpit receives test emails at
    `http://localhost:8025` when configured.
-   [ ] **NOTIF-007** Reminder/notification failure is reported and does
    not break patient registration or billing.
-   [ ] **NOTIF-008** Retries do not send duplicate reminders
    unexpectedly.
-   [ ] **NOTIF-009** Consent and notification preferences are checked
    before sending.
-   [ ] **NOTIF-010** Notification status, destination, timestamp and
    failure reason are recorded without unnecessary sensitive content.
-   [ ] **NOTIF-011** Background jobs, if added, do not block normal API
    requests.
-   [ ] **NOTIF-012** Paid messaging/email services are not added
    without explicit owner approval.

# 17. AI, speech-to-text and OCR

-   [ ] **AI-001** Default AI provider is the configured local Ollama
    adapter.
-   [ ] **AI-002** If Ollama is offline, the UI clearly reports AI is
    offline and normal clinic workflows continue.
-   [ ] **AI-003** AI suggestions are never saved as final prescriptions
    without the doctor choosing Accept/Edit/Reject.
-   [ ] **AI-004** Doctor can edit or reject AI output before saving.
-   [ ] **AI-005** Store AI suggestion and doctor's final version with
    prompt version and model name in the AI audit table.
-   [ ] **AI-006** Patient AI consent is checked before every relevant
    AI call.
-   [ ] **AI-007** Name, phone and address are removed before sending
    text to any AI provider and correctly handled on return.
-   [ ] **AI-008** No real patient data is sent to a cloud AI provider
    in development or by default.
-   [ ] **AI-009** AI module has a per-branch ON/OFF switch.
-   [ ] **AI-010** Paid-provider monthly cost limit is supported if/when
    paid providers are explicitly approved.
-   [ ] **AI-011** Prompts are stored in versioned template files, not
    embedded directly in business code.
-   [ ] **AI-012** Slow AI jobs use background processing when
    configured and do not freeze the UI.
-   [ ] **AI-013** Local speech-to-text provider uses the configured
    faster-whisper path and handles missing models/devices gracefully.
-   [ ] **AI-014** OCR provider uses local Tesseract and configured
    Gujarati, Hindi and English languages where installed.
-   [ ] **AI-015** AI/OCR/speech errors are logged safely without
    exposing patient details or secrets.
-   [ ] **AI-016** AI outputs are treated as untrusted suggestions and
    validated before display/save.
-   [ ] **AI-017** AI features remain unavailable when disabled,
    including via direct API calls.
-   [ ] **AI-018** No paid AI provider/API is enabled without explicit
    owner approval.

# 18. Reports, dashboard, exports and search

-   [ ] **REP-001** Dashboard counts match the underlying records for
    the selected branch and date range.
-   [ ] **REP-002** Appointment and patient reports filter correctly by
    date, branch and doctor.
-   [ ] **REP-003** Billing totals reconcile with invoices, credit
    notes, refunds and payments.
-   [ ] **REP-004** Pharmacy reports reconcile with batch ledger and
    stock movements.
-   [ ] **REP-005** Exported data matches the filtered on-screen data.
-   [ ] **REP-006** Export permissions are checked server-side and
    exports are audited.
-   [ ] **REP-007** Sensitive fields are masked or omitted from exports
    unless explicitly authorized.
-   [ ] **REP-008** Pagination and filters work together without
    duplicate/missing records.
-   [ ] **REP-009** Sorting by date/amount/status works correctly.
-   [ ] **REP-010** Empty report ranges display a helpful empty state
    rather than an error.
-   [ ] **REP-011** Large reports do not time out unexpectedly;
    performance is measured on representative demo data.
-   [ ] **REP-012** Branch and organization totals do not double-count
    shared organization-level masters.

# 19. Languages and UI usability

-   [ ] **UI-001** User can select English, Gujarati and Hindi.
-   [ ] **UI-002** All user-facing screen text comes from translation
    files; components do not hardcode screen text.
-   [ ] **UI-003** Language switch updates labels, buttons, validation
    messages, menus and supported documents.
-   [ ] **UI-004** Missing translations are identified and do not crash
    the UI.
-   [ ] **UI-005** Gujarati/Hindi fonts render properly on supported
    browsers.
-   [ ] **UI-006** Forms show clear validation messages near the
    relevant field.
-   [ ] **UI-007** Save, loading, empty, success and failure states are
    clear.
-   [ ] **UI-008** Tables support practical search, sorting and
    pagination where required.
-   [ ] **UI-009** Dialogs confirm consequential actions such as
    cancellation or adjustment.
-   [ ] **UI-010** Keyboard navigation, focus state and labels are
    usable for staff.
-   [ ] **UI-011** Layout is usable on the intended desktop and tablet
    screen sizes.
-   [ ] **UI-012** Slow network/API failures are displayed without
    losing already-saved records.
-   [ ] **UI-013** Repeated clicks do not submit the same form multiple
    times.
-   [ ] **UI-014** Date, currency and number formats are consistent for
    the intended Indian clinic workflow.

# 20. Audit trail and record history

-   [ ] **AUD-001** Patient record view events are logged.
-   [ ] **AUD-002** Create, update, print, export and share events are
    logged.
-   [ ] **AUD-003** Each event records user, branch, time, IP and
    relevant change details as specified.
-   [ ] **AUD-004** Audit logs are append-only through normal
    application permissions.
-   [ ] **AUD-005** Ordinary users cannot edit or delete audit events.
-   [ ] **AUD-006** Audit history identifies what changed without
    storing unnecessary sensitive values.
-   [ ] **AUD-007** Pharmacy stock movements and financial adjustments
    are traceable.
-   [ ] **AUD-008** Consent, privacy requests and AI
    suggestion/final-result actions are audited.
-   [ ] **AUD-009** Audit events are associated with the correct
    organization and branch.
-   [ ] **AUD-010** Failed/unauthorized access attempts are logged
    safely where configured.
-   [ ] **AUD-011** Log output never exposes passwords, JWT secrets, API
    keys or full sensitive patient records.
-   [ ] **AUD-012** Audit records remain available after a record is
    archived/soft-deleted.

# 21. API, database integrity and migrations

-   [ ] **DB-001** All API endpoints are under `/api/v1/` as specified.
-   [ ] **DB-002** Frontend uses the REST APIs rather than directly
    accessing the database.
-   [ ] **DB-003** API request/response formats are consistent and
    documented.
-   [ ] **DB-004** Serializers validate required fields, lengths,
    ranges, dates and relationships.
-   [ ] **DB-005** Main tables use UUID primary keys and required
    organization/branch ownership fields.
-   [ ] **DB-006** Main tables include timestamps, created/updated user
    fields and soft-delete fields as required.
-   [ ] **DB-007** Medical, billing and audit records are not
    hard-deleted in normal workflows.
-   [ ] **DB-008** Foreign keys and uniqueness constraints prevent
    invalid relationships and duplicates.
-   [ ] **DB-009** Indexes exist for organization, branch and commonly
    filtered date fields where appropriate.
-   [ ] **DB-010** Dropdown/master values are managed through master
    tables, not hardcoded lists.
-   [ ] **DB-011** Migrations apply successfully to a clean test
    database.
-   [ ] **DB-012** Migrations apply safely to a representative existing
    test database.
-   [ ] **DB-013** Old migrations are never edited to change
    already-applied schema history.
-   [ ] **DB-014** Failed transactions roll back related writes
    together.
-   [ ] **DB-015** Concurrent requests cannot create duplicate patient
    IDs, invoice numbers or conflicting stock movements.
-   [ ] **DB-016** Pagination limits prevent unbounded data retrieval.
-   [ ] **DB-017** No unsafe raw SQL uses string formatting with user
    input.
-   [ ] **DB-018** PostgreSQL and pgvector versions/configuration match
    the project baseline.
-   [ ] **DB-019** pgvector-dependent features fail clearly if
    unavailable, without breaking unrelated features.
-   [ ] **DB-020** Soft-deleted records are excluded from ordinary lists
    but remain accessible through authorized history/audit paths.

# 22. Security testing

-   [ ] **SEC-001** Test for broken access control by changing record
    IDs in URLs/API requests.
-   [ ] **SEC-002** Test cross-organization and cross-branch data
    isolation across list, detail, create, update, delete/archive,
    search, report, export and PDF endpoints.
-   [ ] **SEC-003** Test injection attempts in search and text fields.
-   [ ] **SEC-004** Test XSS payloads in patient names, notes and other
    text fields; content is safely rendered.
-   [ ] **SEC-005** Verify CSRF protections according to the configured
    Django/DRF authentication design.
-   [ ] **SEC-006** Verify CORS settings are not overly permissive in
    any future non-local deployment.
-   [ ] **SEC-007** Verify upload type, size and content validation.
-   [ ] **SEC-008** Verify private uploaded files cannot be accessed
    through guessed public paths.
-   [ ] **SEC-009** Verify secrets are absent from Git history/current
    files, logs, frontend bundles and error responses.
-   [ ] **SEC-010** Verify sensitive data is encrypted at application
    level where practical and required by the design.
-   [ ] **SEC-011** Verify Aadhaar numbers are not collected/stored by
    this application.
-   [ ] **SEC-012** Verify list views mask sensitive phone data as
    specified.
-   [ ] **SEC-013** Verify role permissions for therapist, pharmacist,
    receptionist, doctor and admin.
-   [ ] **SEC-014** Verify rate limits and safe errors for login and
    sensitive endpoints.
-   [ ] **SEC-015** Verify access tokens are not placed in URLs or
    exposed in logs.
-   [ ] **SEC-016** Verify the browser cannot access admin-only actions
    merely by changing UI state.
-   [ ] **SEC-017** Verify audit logs cannot be altered by normal users.
-   [ ] **SEC-018** Verify local AI provider configuration keeps patient
    data on the local machine.
-   [ ] **SEC-019** Verify all development fixtures and automated tests
    use fake/demo patient data.
-   [ ] **SEC-020** Review security findings before any real patient
    data is entered.

# 23. Backup, recovery and local deployment readiness

-   [ ] **OPS-001** Database backup process is documented and
    executable.
-   [ ] **OPS-002** Restore backup into an isolated test database and
    verify the restored records.
-   [ ] **OPS-003** Verify patient, visit, prescription, invoice,
    payment and stock relationships survive restore.
-   [ ] **OPS-004** Verify uploaded files/documents are included in the
    relevant backup strategy.
-   [ ] **OPS-005** Verify recovery instructions are understandable to a
    non-programmer.
-   [ ] **OPS-006** Verify containers restart after a normal
    Docker/Desktop restart.
-   [ ] **OPS-007** Verify health checks and useful logs exist for
    backend/database and configured services.
-   [ ] **OPS-008** Verify a database migration failure does not
    silently destroy data.
-   [ ] **OPS-009** Verify `reset-demo-data.bat` cannot accidentally be
    mistaken for a production data reset tool.
-   [ ] **OPS-010** Verify no real patient data is used for development
    or QA.
-   [ ] **OPS-011** Verify current setup remains local-only until the
    owner explicitly approves hosting.
-   [ ] **OPS-012** Do not configure AWS/cloud hosting, paid services or
    new external providers unless the owner asks.

# 24. Performance, reliability and error handling

-   [ ] **PERF-001** Frontend production build succeeds.
-   [ ] **PERF-002** Frontend TypeScript/type-check passes using the
    project's actual scripts.
-   [ ] **PERF-003** Backend automated tests pass.
-   [ ] **PERF-004** API validation errors return expected status codes
    and safe messages.
-   [ ] **PERF-005** Database unavailable behavior is understandable and
    does not expose internal secrets.
-   [ ] **PERF-006** Ollama unavailable behavior is graceful and non-AI
    features continue working.
-   [ ] **PERF-007** Mail/SMS/WhatsApp/payment adapter failures do not
    corrupt clinic data.
-   [ ] **PERF-008** Repeated requests do not duplicate important
    records or transactions.
-   [ ] **PERF-009** Large lists use pagination and relevant indexes.
-   [ ] **PERF-010** Representative demo data is used to measure key
    patient search, appointment, prescription and billing flows.
-   [ ] **PERF-011** Browser console and server logs contain no
    unexpected errors during core workflows.
-   [ ] **PERF-012** UI does not claim an operation succeeded before the
    backend confirms success.
-   [ ] **PERF-013** Timeouts and retry behavior do not create duplicate
    payments, invoices, messages or stock movements.
-   [ ] **PERF-014** App remains usable when optional modules/providers
    are disabled.

# 25. End-to-end workflow tests

Run these as complete scenarios using fake/demo patients.

-   [ ] **E2E-001** Receptionist creates a patient → books appointment →
    checks patient in → doctor sees the correct patient.
-   [ ] **E2E-002** Doctor completes Ayurvedic assessment → records
    diagnosis/plan → creates prescription → final prescription is saved
    correctly.
-   [ ] **E2E-003** Doctor selects 180 days → follow-up and medicine
    duration default to 180 → doctor changes one field → the other
    remains unchanged.
-   [ ] **E2E-004** Prescription is printed in English, Gujarati and
    Hindi where supported; medicine details remain accurate.
-   [ ] **E2E-005** Consultation + medicines + therapy appear on one
    invoice and totals reconcile.
-   [ ] **E2E-006** Pharmacy purchase adds the correct batch stock and
    ledger movement.
-   [ ] **E2E-007** Pharmacy sale uses the correct batch/FEFO rule and
    deducts stock once.
-   [ ] **E2E-008** Invoice cancellation/refund creates the required
    credit note and does not delete the original invoice.
-   [ ] **E2E-009** Follow-up is scheduled and appears in the correct
    future/overdue list.
-   [ ] **E2E-010** Patient returns for a revisit → new assessment is
    created → old visit history remains unchanged.
-   [ ] **E2E-011** Doctor switches branch → sees only authorized branch
    data and the correct schedule.
-   [ ] **E2E-012** Organization admin turns an optional module OFF →
    existing data remains preserved and prohibited actions are blocked.
-   [ ] **E2E-013** Local Ollama is stopped → AI shows an offline
    message → registration, appointment, prescription entry and billing
    continue.
-   [ ] **E2E-014** Unauthorized therapist/pharmacist attempts a
    restricted action → API denies access and the attempt is handled
    safely.
-   [ ] **E2E-015** Backup is created → restored to an isolated test
    environment → key records and relationships are verified.

# 26. Regression test checklist after every change

-   [ ] **REG-001** Read the change summary and identify affected
    modules before testing.
-   [ ] **REG-002** Review the Git diff; ensure unrelated files/features
    were not changed.
-   [ ] **REG-003** Confirm any model change has a new migration and old
    migrations are untouched.
-   [ ] **REG-004** Run relevant backend tests.
-   [ ] **REG-005** Run frontend type-check and build.
-   [ ] **REG-006** Run tests for the modified workflow and connected
    workflows.
-   [ ] **REG-007** Verify permissions and branch/organization scoping
    for changed APIs.
-   [ ] **REG-008** Verify translations in English, Gujarati and Hindi
    for changed UI text.
-   [ ] **REG-009** Verify PDF/print output if the change affects
    documents.
-   [ ] **REG-010** Verify optional feature switches if the change
    affects a configurable module.
-   [ ] **REG-011** Update the relevant guide file(s) and
    `CHANGELOG.md`.
-   [ ] **REG-012** Confirm no secrets, real patient data or unintended
    generated files are included in the commit.
-   [ ] **REG-013** Commit the change in a small, reviewable unit after
    tests pass.
-   [ ] **REG-014** Record how to revert the change or return to the
    previous known-good commit.

# 27. Go-live decision checklist

**Do not mark the software ready for real patient data until the
responsible owner has reviewed the evidence.**

-   [ ] **LIVE-001** P0 security and data-integrity tests pass.
-   [ ] **LIVE-002** Organization/branch isolation has been verified on
    APIs, reports, exports and documents.
-   [ ] **LIVE-003** Authentication, role permissions and session
    controls have been verified.
-   [ ] **LIVE-004** Patient registration, visit, prescription, billing
    and follow-up end-to-end flow passes.
-   [ ] **LIVE-005** Pharmacy and stock flows pass if pharmacy is
    enabled.
-   [ ] **LIVE-006** Prescription safety warnings and doctor approval
    for AI suggestions are verified if these features are enabled.
-   [ ] **LIVE-007** PDF/print and Gujarati/Hindi rendering are verified
    for the clinic's actual required paper sizes.
-   [ ] **LIVE-008** Backup restore has been tested successfully.
-   [ ] **LIVE-009** Critical/high bugs are fixed or formally accepted
    by the owner with documented risk.
-   [ ] **LIVE-010** Demo-only reset tools and test accounts cannot
    affect real records.
-   [ ] **LIVE-011** Applicable Indian privacy, medical-record
    retention, tax and other compliance questions have been reviewed
    with qualified professionals.
-   [ ] **LIVE-012** Hosting is not enabled until separately approved
    and secured.
-   [ ] **LIVE-013** Owner understands how to start/stop the app, view
    logs, back up data and get help.
-   [ ] **LIVE-014** A tested rollback/recovery plan is available.

## Final QA summary

Fill this in after the audit; do not estimate or invent results.

-   **Audit date:**
-   **Git branch / commit:**
-   **Environment:**
-   **Total tests:**
-   **PASS:**
-   **FAIL:**
-   **BLOCKED:**
-   **NOT RUN:**
-   **P0 open bugs:**
-   **P1 open bugs:**
-   **Backup restore result:**
-   **Cross-organization isolation result:**
-   **End-to-end workflow result:**
-   **Go-live recommendation:** GO / NO-GO / CONDITIONAL
-   **Reason and evidence:**

**Important:** This file is a test plan. It does not prove the software
currently implements these features or complies with every applicable
law. Verify each item against the actual repository and record evidence
from tests.
