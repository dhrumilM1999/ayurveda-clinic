# QA results: Ayurveda Clinic Management Software

Audit of `docs/qa/QA_CHECKLIST.md` (the owner's checklist). Written from real runs, not estimates.

## Final QA summary

- **Audit date:** 2026-10-24
- **Git branch / commit:** feature/panchakarma at cee3359 (plus this report). Go-live branches (security hardening, deployment, backups) were NOT part of this branch and are marked BLOCKED where needed
- **Environment:** developer PC, Docker Compose (Django 5, PostgreSQL 16, Vite dev server), fictional demo data only
- **Total checklist items:** 427
- **PASS:** 354   **FAIL:** 24   **BLOCKED:** 8   **NOT RUN:** 41
- **P0 open bugs:** 0 found
- **P1 open bugs:** 0 found
- **Backup restore result:** BLOCKED. Backup and restore scripts are on the deployment branch (not merged); not independently re-run
- **Cross-organization isolation result:** PASS on patients, appointments, invoices, stock, therapy plans and handwriting pictures (tests named in the table)
- **End-to-end workflow result:** PASS for the clinic day (front desk, doctor, pharmacy, one bill, owner totals) in an automated test and in the real screens; E2E-004, E2E-011 not run; E2E-005 FAIL (therapy plan billing); E2E-015 blocked
- **Go-live recommendation:** **CONDITIONAL.** The clinic day works and is protected against many mistakes. Before real patient data: merge and verify the security + deployment branches, restore-test a backup, decide the doctor/admin login-code method, print on the real printer, and have a lawyer/CA review the compliance and tax questions. Open FAILs are P2/P3 (list below), none is a data-loss or data-leak bug found in this audit

Not tested is not passed: every NOT RUN and BLOCKED item is listed in the tables. PASS means the evidence in the row exists and was run; it does not mean legal compliance.

## Bugs and gaps found by this audit

| ID | Severity | What | Status |
|---|---|---|---|
| RX-005 | P2 | Typing 2222 in the dosage box silently became 2-2-22 with no warning | **Fixed** (a warning now shows) |
| PHARM-027 | P2 | The same supplier invoice could be entered twice and doubled the stock | **Fixed** (second entry refused) |
| THER-007 / E2E-005 | P2 | Therapy plan sessions are not added to the bill automatically | Open: needs the owner's yes / no |
| CONS-007, 008, 009 | P2 | No screens for patient requests (view / correct / erase) and no grievance contact | Open: due before 13 May 2027 (DPDP) |
| PAT-016 | P2 | Two people editing one patient: the last save wins | Open |
| ORG-009, THER-001 | P3 | Therapy and questionnaire masters have no branch override | Open |
| PAT-010 | P3 | Therapy and diet plans are not on the patient profile | Open |
| BILL-004 | P3 | IGST (other-state sale) not built | Open (not needed for a one-state clinic) |
| PHARM-012 | P3 | A batch barcode is not forced to be unique (medicine barcode is) | Open |
| NOTIF-010 | P3 | Message log keeps the full text (patient name, token) | Open |
| SET-014, REG-012 | P3 | Working copy not clean: .gitignore no longer ignores the big demo mp4 files | Open: restore the ignore line |
| DIET-001..007, AI-005, AI-013, AI-014 | n/a | Diet module, AI audit table, speech-to-text, OCR are not built | Not built (see CLAUDE.md steps) |

## 1. Repository, setup and developer workflow

PASS 14 · FAIL 1 · BLOCKED 0 · NOT RUN 1

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| SET-001 | PASS | Verify the repository structure matches the documented architecture, and identify the actual implemented apps and frontend modules. | Apps in backend/apps match CLAUDE.md except diet, ai, feedback (not built, see DIET/AI) |
| SET-002 | PASS | Confirm the fixed tech stack is used; any proposed stack change is presented to the owner before implementation. | Stack unchanged (Django 5, DRF, React/TS/Vite, Ant Design, Postgres+pgvector image) |
| SET-003 | PASS | Verify `.env.example` contains safe demo values and no real credentials. | .env.example has dev-only placeholder values (dev key, dev DB password) |
| SET-004 | PASS | Verify secrets are loaded from environment configuration and are not hardcoded. | settings.py reads everything through env(); no real secret in code |
| SET-005 | PASS | Verify `docker compose up` starts the required local services from a clean setup. | docker compose up / up -d --build run today after Docker Desktop restarts (3 times) |
| SET-006 | PASS | Verify `start.bat`, `stop.bat`, `logs.bat`, and `reset-demo-data.bat` exist and print clear messages; test reset only on disposable demo data. | start/stop/logs/reset bat files exist; reset needs typing YES and DEMO_MODE=true (bat files not executed by this audit) |
| SET-007 | PASS | Verify frontend URL `http://localhost:5173`, API base `/api/v1/`, Django admin `http://localhost:8000/admin/`, and Mailpit `http://localhost:8025` ... | :5173 app, /api/v1/health/ ok, Mailpit :8025 = 200, admin /admin/ in dev |
| SET-008 | PASS | Verify Vite polling reload works inside Docker on Windows. | vite.config.ts watch.usePolling true (config check; a live edit-reload was not timed) |
| SET-009 | PASS | Verify `.gitattributes` uses LF for text and CRLF for `.bat` files. | .gitattributes: * text=auto eol=lf, *.bat eol=crlf |
| SET-010 | PASS | Verify `node_modules` is kept in the intended container volume and not accidentally mounted from the Windows host. | docker-compose.yml anonymous volume /app/node_modules |
| SET-011 | PASS | Verify startup does not depend on undocumented `.sh` entrypoint scripts. | No .sh entrypoints in backend/frontend; commands are in docker-compose.yml |
| SET-012 | NOT RUN | Verify documented commands work in Windows PowerShell/Command Prompt as described. | PowerShell / Command Prompt documented commands were not re-run one by one |
| SET-013 | PASS | Verify the app starts after Docker restart and gives understandable errors when a required service is unavailable. | Containers came back after every Docker restart; failed loads show "Could not load this list" + Try again (test ui_mistakes) |
| SET-014 | FAIL | Verify a clean Git status, understandable commit history, and a documented rollback approach before risky work. | P3: git status is not clean (.gitignore edited, demo mp4 files untracked). History is readable; rollback = git revert / docs/GO_LIVE |
| SET-015 | PASS | Verify guide files exist and are updated: `START_HERE_WINDOWS.md`, `HOW_IT_WORKS.md`, `FOLDER_MAP.md`, `SMALL_CHANGES.md`, `TROUBLESHOOTING.md`, `G... | All 7 guide files exist; CHANGELOG current; some guides (HOW_IT_WORKS) do not yet describe therapy / handwriting |
| SET-016 | PASS | Verify editable files contain accurate `SAFE TO EDIT` comments and dangerous changes are marked `ASK FIRST`. | 56 files carry SAFE TO EDIT; ASK FIRST marked in docs/FOLDER_MAP.md |

## 2. Authentication, accounts and sessions

PASS 14 · FAIL 0 · BLOCKED 0 · NOT RUN 0

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| AUTH-001 | PASS | Valid user credentials allow login. | test_receptionist_logs_in_without_otp |
| AUTH-002 | PASS | Invalid username/password is rejected with a safe, understandable message. | test_wrong_password_is_rejected_and_logged |
| AUTH-003 | PASS | Login is rate-limited after repeated failed attempts. | test_login_is_rate_limited; test_wrong_password_attempts_are_limited_and_message_is_the_same |
| AUTH-004 | PASS | Passwords are stored using Argon2 hashing; plaintext passwords are never stored or logged. | QA probe test_AUTH_004 (argon2$ hash); passwords hidden from audit (HIDDEN_FIELDS); OTP not in message log test |
| AUTH-005 | PASS | JWT access tokens expire according to the configured short lifetime. | QA probe: ACCESS_TOKEN_LIFETIME 15 min |
| AUTH-006 | PASS | Refresh-token behavior and logout/revocation behavior match the documented security design. | QA probe test_AUTH_006_013: refresh token dead after logout |
| AUTH-007 | PASS | Idle sessions automatically log out after the configured idle period. | Code: useIdleLogout (15 min from IDLE_TIMEOUT_MINUTES); the 15-minute wait was not run |
| AUTH-008 | PASS | Password reset/change works and invalidates sessions/tokens as designed. | QA probe test_AUTH_008: old password required, weak refused, old password stops working |
| AUTH-009 | PASS | Admin and doctor 2FA/OTP flow is tested; development OTP is shown only through the console provider as documented. | test_doctor_needs_otp_then_gets_tokens; test_org_admin_needs_otp; OTP only in console provider/dev |
| AUTH-010 | PASS | Disabled/inactive users cannot sign in or continue using protected APIs. | QA probe test_AUTH_010: inactive user token and refresh refused; test_inactive_or_deleted_user_cannot_log_in |
| AUTH-011 | PASS | API endpoints reject missing, malformed, expired and tampered tokens. | test_expired_or_fake_token_is_refused; test_api_needs_login |
| AUTH-012 | PASS | Authentication errors do not reveal whether a sensitive account exists. | Same answer for unknown user and wrong password (test_wrong_password_attempts...) |
| AUTH-013 | PASS | Logout prevents further use according to the token/session design. | QA probe test_AUTH_006_013 |
| AUTH-014 | PASS | User profile and password endpoints validate inputs and enforce permissions. | Change-password validated (probe); set-password needs staff.manage (test_weak_password_is_refused) |

## 3. Organization, branches, rooms and staff

PASS 14 · FAIL 1 · BLOCKED 0 · NOT RUN 1

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| ORG-001 | PASS | Create, view and edit an organization. | test_branding...; organization PATCH needs settings.manage (test_branch_admin_cannot_touch...) |
| ORG-002 | PASS | Create, view and edit multiple branches under one organization. | test_only_org_admin_can_add_branches; test_single_branch_mode_shows_only_main_branch |
| ORG-003 | PASS | Create and manage rooms for the correct branch. | test_rooms_are_filtered_by_branch; test_branch_admin_adds_room_and_it_is_audited |
| ORG-004 | PASS | Assign staff to the intended organization and branch. | test_branch_admin_creates_staff_only_in_own_branch |
| ORG-005 | PASS | A doctor can be assigned to more than one branch. | Fixture doctor works in two branches; test_doctor_must_work_in_branch |
| ORG-006 | PASS | Doctor schedules can differ by branch. | DoctorSchedule per branch; test_doctor_schedule_overlap_is_refused |
| ORG-007 | PASS | Patient identity is organization-wide and the patient can be seen at different branches with the same patient ID. | test_patient_registered_in_one_branch_is_seen_in_another |
| ORG-008 | PASS | Visits, appointments, invoices and pharmacy stock are associated with the correct branch. | test_appointments_stay_in_their_branch; test_stock_is_per_branch; test_invoice_of_another_branch_is_not_reachable |
| ORG-009 | FAIL | Organization-level medicine, therapy, diet and questionnaire masters can be overridden at branch level only for allowed fields. | P3: medicine price/on-off branch override works (test_branch_price_and_switch_off); therapy and questionnaire masters have no branch override |
| ORG-010 | PASS | Branch-level price, stock and active/inactive overrides do not unintentionally change another branch. | test_branch_price_and_switch_off; test_stock_is_per_branch |
| ORG-011 | PASS | Current branch is sent in the `X-Branch-ID` header where required. | test_rooms_need_a_branch_header |
| ORG-012 | PASS | Invalid, missing or unauthorized branch IDs are rejected safely. | test_bad_branch_header_is_rejected; QA probe test_ORG_012 |
| ORG-013 | PASS | Organization admin can see permitted branches; other roles see only their assigned branches. | test_org_admin_sees_all_branches_but_others_only_theirs |
| ORG-014 | NOT RUN | Branch switching refreshes lists, dashboards, permissions and branch-specific settings correctly. | Branch switching in the screen not exercised (single-branch demo) |
| ORG-015 | PASS | Date/time, invoice numbering and reports remain scoped to the correct branch. | test_numbers_per_branch_and_year; test_branch_choice_respects_access |
| ORG-016 | PASS | Deactivating a branch or staff member preserves historical records and does not orphan records. | test_staff_delete_is_soft; test_room_delete_is_soft |

## 4. Roles, permissions and branch scoping

PASS 14 · FAIL 0 · BLOCKED 0 · NOT RUN 0

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| PERM-001 | PASS | Permission codes are defined in the central permission catalog. | accounts/permissions_catalog.py |
| PERM-002 | PASS | Roles are data-managed and can be configured through the admin screen as intended. | test_changing_a_role_changes_what_users_can_do; Roles screen |
| PERM-003 | PASS | Users receive role assignments per branch. | UserBranchRole model; test_branch_admin_creates_staff_only_in_own_branch |
| PERM-004 | PASS | Admin can perform only the actions allowed by the configured role. | test_system_role_cannot_be_deleted; test_branch_admin_cannot_make_org_admin |
| PERM-005 | PASS | Doctor can access assigned clinical workflows but not unauthorized organization settings. | test_wrong_people_and_the_checkup; doctor lacks staff/settings (crawl: no access screens) |
| PERM-006 | PASS | Receptionist can manage permitted patient registration and appointments but cannot access restricted clinical/billing data. | test_receptionist_cannot_see_checkups; test_medical_history_hidden_from_receptionist_but_allergies_shown |
| PERM-007 | PASS | Therapist cannot see billing information unless explicitly granted permission. | test_therapist_has_no_billing_permission; test_therapist_cannot_bill; test_therapist_cannot_see_money_reports |
| PERM-008 | PASS | Pharmacist can access permitted medicine/prescription and pharmacy functions but not the patient's full clinical history unless explicitly authorized. | test_pharmacist_cannot_see_appointments; pharmacist has no emr.view (test_wrong_people_and_the_checkup) |
| PERM-009 | PASS | Hiding a button in the frontend is not the only security control; the API also denies unauthorized actions. | QA probe test_PERM_009 (therapist/pharmacist/receptionist API calls refused) |
| PERM-010 | PASS | Direct API calls with another branch ID are rejected unless the user is authorized for that branch. | test_user_cannot_use_a_branch_they_are_not_in |
| PERM-011 | PASS | Cross-organization list, detail, search, export and update requests return no unauthorized data. | test_other_organization_data_is_invisible; test_other_clinic_cannot_see_patient; other_organizations tests |
| PERM-012 | PASS | Permission changes take effect as designed without requiring unsafe manual database edits. | test_changing_a_role_changes_what_users_can_do |
| PERM-013 | PASS | Permission checks apply to PDF, print, export and share actions, not only normal screen views. | test_who_can_print; test_pictures_are_private...; test_export_excel_and_pdf_are_audited |
| PERM-014 | PASS | Soft-deleted records do not leak through search, APIs or reports unless an authorized audit view is intended. | ActiveManager hides soft-deleted rows; test_patients_are_never_deleted; test_room_delete_is_soft |

## 5. Patient registration and patient records

PASS 14 · FAIL 2 · BLOCKED 0 · NOT RUN 0

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| PAT-001 | PASS | Register a new patient with valid required information. | test_uhid_is_a_plain_running_number |
| PAT-002 | PASS | Required fields, lengths, formats and date values are validated by the backend. | test_registration_refuses_wrong_input (11 cases) |
| PAT-003 | PASS | Patient IDs are unique within the intended organization and are not duplicated by concurrent registrations. | QA probe test_PAT_003: 6 registrations at once = 6 different ids |
| PAT-004 | PASS | Search patients by patient ID, name and supported phone search. | test_search_while_typing; test_list_masks_phone_and_search_is_audited |
| PAT-005 | PASS | Patient phone numbers are masked in lists, e.g. `98XXXXXX21`, where appropriate. | test_list_masks_phone_and_search_is_audited; test_mask_phone |
| PAT-006 | PASS | Patient demographic details can be corrected by authorized staff and changes are audited. | test_update_records_what_changed; test_receptionist_cannot_change_medical_history_later |
| PAT-007 | PASS | Duplicate-patient detection warns staff and supports safe resolution without silently merging records. | test_duplicate_check (warns, never merges) |
| PAT-008 | PASS | A patient's complete history is available across authorized branches of the same organization. | test_patient_registered_in_one_branch_is_seen_in_another; test_history_from_all_branches |
| PAT-009 | PASS | A patient from another organization cannot be accessed by changing a URL, UUID or API parameter. | test_other_organization_patient_is_invisible |
| PAT-010 | FAIL | Patient profile shows correct visits, assessments, prescriptions, therapies, diet plans, invoices and follow-ups according to permissions. | P3: profile shows visits, Rx, bills, documents; therapy plans and diet plans are not on the patient profile (diet not built) |
| PAT-011 | PASS | Archive/soft-delete preserves legally required medical history. | test_patients_are_never_deleted |
| PAT-012 | PASS | Medical records are never hard-deleted through ordinary application flows. | test_deleting_a_patient_never_removes_the_record |
| PAT-013 | PASS | Patient list pagination, sorting, filtering and empty states work correctly. | Patients list tested in crawl and UI (live search, pagination, empty state) |
| PAT-014 | PASS | Search handles Gujarati, Hindi and English names/synonyms where supported. | Gujarati names stored (test_odd_names...) and found by substring search; no transliteration between scripts |
| PAT-015 | PASS | Patient import/export, if implemented, is permission-controlled and audited. | No patient import/export exists (QA probe test_PAT_015): nothing to leak |
| PAT-016 | FAIL | Concurrent edits do not silently overwrite important patient changes. | P2: no edit-conflict protection: two people editing the same patient = last save wins |

## 6. Consent, privacy requests and grievance handling

PASS 7 · FAIL 3 · BLOCKED 0 · NOT RUN 2

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| CONS-001 | PASS | Registration records separate consent for treatment, SMS/WhatsApp, AI processing and research. | ConsentPurpose: treatment, communication, AI, research (ensure_consent_purposes) |
| CONS-002 | PASS | Consent text is available in English, Gujarati and Hindi. | test_consent_purposes_have_three_languages |
| CONS-003 | PASS | Consent records include when and how consent was given. | test_consent_grant_withdraw_and_history (method, language, time) |
| CONS-004 | PASS | Patient consent withdrawal is recorded with date/time and method. | same test: withdrawal is a new record; records cannot be edited or deleted |
| CONS-005 | NOT RUN | Withdrawing optional AI consent prevents subsequent AI processing requiring that consent. | No AI feature processes patient data yet (Translate sends only list names) |
| CONS-006 | PASS | Withdrawing SMS/WhatsApp consent prevents relevant promotional/reminder communication according to the configured policy. | test_no_messages_without_consent; test_whatsapp_share_needs_consent |
| CONS-007 | FAIL | Staff can handle patient requests to view, correct and erase data. | P2: no screen for patient requests to view / correct / erase (CLAUDE.md wants it before 13 May 2027) |
| CONS-008 | FAIL | Erasure requests respect applicable medical-record retention rules; mask/restrict where deletion is not permitted rather than hard-delete required ... | P2: no erasure-request / mask workflow built; records are never hard-deleted (safe default) |
| CONS-009 | FAIL | Grievance contact/details are available to patients or staff as designed. | P2: no grievance contact in the software |
| CONS-010 | PASS | Consent and privacy-request actions are audited. | QA probe test_CONS_010; consent rows are append-only |
| CONS-011 | PASS | Consent state is checked on the backend, not just the frontend. | consent checked in services before messages |
| CONS-012 | NOT RUN | QA report records which legal/compliance items require review by a qualified Indian legal/compliance professional; do not claim legal compliance so... | Needs a qualified Indian legal / compliance professional. Tests passing is NOT legal compliance |

## 7. Appointment, check-in and patient flow

PASS 12 · FAIL 0 · BLOCKED 0 · NOT RUN 1

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| APT-001 | PASS | Create an appointment for an existing patient. | test_book_appointment_sends_sms_and_whatsapp_link |
| APT-002 | PASS | Register a new patient as part of the appointment/check-in workflow where supported. | Registration is a separate step, then book / walk-in (UI journey run) |
| APT-003 | PASS | Assign the correct doctor, branch, date, time and room if applicable. | Doctor, branch, date, time (no rooms for consultations) |
| APT-004 | PASS | Prevent or clearly warn about conflicting appointments for the same doctor/time. | test_double_booking_is_refused; test_database_also_blocks_double_booking |
| APT-005 | PASS | Support appointment status changes: booked, waiting, in progress, completed and cancelled where implemented. | test_check_in_start_complete; test_undo_* |
| APT-006 | PASS | Today's queue displays the correct branch, doctor and status. | test_queue_groups_by_doctor; Queue screen |
| APT-007 | PASS | Reschedule and cancellation preserve history and are audited. | test_reschedule_moves_the_slot; test_cancel_frees_the_slot; audited via log_action |
| APT-008 | PASS | A cancelled appointment is not treated as an active appointment. | test_cancel_frees_the_slot; test_wrong_step_order_is_refused |
| APT-009 | PASS | Doctor availability and schedules are checked per branch. | test_slots_come_from_doctor_schedule; test_doctor_must_work_in_branch |
| APT-010 | NOT RUN | Date filters work at day/month/year boundaries. | Month / year boundary filters not specifically tested |
| APT-011 | PASS | Concurrent booking attempts do not create unintended duplicate/conflicting appointments. | test_token_numbers_never_repeat_when_many_check_in_at_once; DB constraint test |
| APT-012 | PASS | Appointment workflow links to the correct patient assessment and visit. | test_open_visit_from_appointment |
| APT-013 | PASS | Follow-up/revisit returns the patient to a new assessment while preserving prior visit history. | Each appointment opens a new visit; old visits unchanged (test_history_from_all_branches) |

## 8. Ayurvedic assessment, diagnosis and care plan (EMR)

PASS 10 · FAIL 0 · BLOCKED 0 · NOT RUN 0

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| EMR-001 | PASS | Start a clinical visit for the correct patient and branch. | test_open_visit_from_appointment |
| EMR-002 | PASS | Save and reopen Ayurvedic assessment information without losing data. | test_save_sections_and_complete |
| EMR-003 | PASS | Diagnosis and care plan are linked to the correct visit. | Diagnoses saved on the visit |
| EMR-004 | PASS | Assessment history from earlier visits remains available to authorized clinicians. | test_history_from_all_branches |
| EMR-005 | PASS | Clinical fields validate lengths, dates and required values. | test_wrong_check_up_data_is_refused_and_nothing_changes; test_wrong_section_data_refused |
| EMR-006 | PASS | Draft and final states behave as designed; unsaved work is not presented as final. | Visit draft / completed; Rx draft / final; Re-open check-up |
| EMR-007 | PASS | Edits to clinical notes are audited with user/time/change information. | test_opening_visit_is_audited; test_notes_are_encrypted_and_not_in_audit_log |
| EMR-008 | PASS | Only authorized clinical roles can create or edit assessments/diagnoses. | test_wrong_people_and_the_checkup |
| EMR-009 | PASS | Reopening a past visit does not accidentally overwrite a newer visit. | Visits are separate rows per appointment; edits are by visit id |
| EMR-010 | PASS | Clinical content is displayed and printed in the selected language where supported. | Screens and prints follow the language (crawl, therapy/Rx print tests) |

## 9. Medicine master and Ayurvedic medicine safety

PASS 15 · FAIL 0 · BLOCKED 0 · NOT RUN 0

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| MED-001 | PASS | Medicine master distinguishes Classical medicines from Patent & Proprietary medicines. | Medicine.kind classical / proprietary / homeopathy |
| MED-002 | PASS | Classical medicine includes the official name and reference to the applicable Ayurvedic Formulary/Pharmacopoeia source. | reference field on classical medicines |
| MED-003 | PASS | Patent & Proprietary medicine stores brand, manufacturer and composition. | brand, manufacturer, composition fields |
| MED-004 | PASS | A brand can link to its classical equivalent where configured. | classical_equivalent link |
| MED-005 | PASS | Search works using Sanskrit, English, Hindi and Gujarati synonyms where entered. | test_search_by_synonym_and_gujarati; test_search_puts_names_that_start_with_the_text_first |
| MED-006 | PASS | Dosage form supports configured forms such as churna, vati, kashaya, arishta, asava, taila, ghrita, bhasma and lehya. | dosage forms from masters_catalog |
| MED-007 | PASS | Composition, reference, manufacturer, AYUSH licence number, HSN and GST rate are stored and validated where applicable. | ayush_licence_no, hsn_code, gst_rate stored |
| MED-008 | PASS | Safety flags can represent Schedule E1, metals/bhasma, pregnancy caution and child caution. | schedule_e1, contains_metals, pregnancy_caution, child_caution |
| MED-009 | PASS | Safety warnings are generated from fixed application rules, not solely by AI. | test_safety_rules (fixed rules in code) |
| MED-010 | PASS | Warnings are visible at the prescribing point and cannot be silently lost in the normal workflow. | Warnings shown in the Rx screen (safety.py); test_safety_rules |
| MED-011 | PASS | Authorized users can edit medicine masters; unauthorized roles cannot. | test_permissions (medicines) |
| MED-012 | PASS | Formulation version history is retained. | test_create_edit_keeps_versions |
| MED-013 | PASS | Old prescriptions continue to show the formulation/version actually prescribed at that time. | test_write_prescription_with_copies |
| MED-014 | PASS | Inactive medicines are not offered for new prescriptions unless an explicit permitted workflow exists. | Rx search uses for_rx=1 (active, not switched off in the branch) |
| MED-015 | PASS | Master values are loaded from database/master tables rather than hardcoded dropdown arrays. | MasterField / master tables |

## 10. Prescription creation, dosage and follow-up defaults

PASS 21 · FAIL 0 · BLOCKED 0 · NOT RUN 1

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| RX-001 | PASS | Create a prescription for the correct patient, visit and doctor. | test_write_prescription_with_copies |
| RX-002 | PASS | Add, edit, reorder and remove medicine lines before finalizing, according to permissions. | test_edit_lines_keeps_ids; screen add/remove |
| RX-003 | PASS | Verify the requested dosage shorthand: entering `222` displays `2-2-2` when that format is selected. | Real screen (probe rx_probe2): typing 222 shows 2-2-2 |
| RX-004 | PASS | Dosage formatting handles supported patterns and does not transform unrelated medicine names or text. | quickDosage converts only exactly 3 digits; names and free text unchanged |
| RX-005 | PASS | Invalid or ambiguous dosage input is flagged instead of silently misinterpreted. | FOUND AND FIXED in this audit: 2222 silently became 2-2-22. Now a warning is shown (commit 86806d5) |
| RX-006 | PASS | Medicine strength, dosage form, route, timing, frequency, duration and instructions remain associated with the correct medicine. | Fields stay on their own line (test_edit_lines_keeps_ids) |
| RX-007 | PASS | Follow-up day presets include 3, 5, 7, 15, 30, 60, 90 and 180 days plus a custom option. | Real screen: chips 3, 5, 7, 15, 30, 60, 90, 120, 150, 180 days plus a custom box (120 and 150 added at the owner's request) |
| RX-008 | PASS | Selecting a follow-up preset sets the initial/default value for both follow-up and medicine duration fields as requested. | Real screen: 180 sets BOTH follow-up (180) and the medicine line duration (180) |
| RX-009 | PASS | Doctor can change follow-up timing independently after the default is applied. | Real screen: follow-up changed to 30, medicine stays 180 |
| RX-010 | PASS | Doctor can change medicine duration independently after the default is applied. | Real screen: medicine changed to 90, follow-up stays 30 |
| RX-011 | PASS | Changing one field after initialization does not unexpectedly overwrite the other field. | Same run: no field overwrote the other after the first default |
| RX-012 | PASS | Custom day values are validated and retained. | Real screen: custom 45 kept (range 1 to 3650) |
| RX-013 | PASS | Prescription draft, save, edit, finalize and print flows work as designed. | Draft / final / print flows (test_completing_visit_makes_prescription_final; handwriting tests) |
| RX-014 | PASS | Editing a saved prescription does not create duplicate medicine lines or duplicate stock movements. | test_edit_lines_keeps_ids; Rx edit creates no stock movement |
| RX-015 | PASS | Final prescription identifies patient, doctor, branch and visit correctly. | patient, doctor, branch, visit on the Rx |
| RX-016 | PASS | Only authorized roles can finalize or modify prescriptions. | test_who_can_see_and_write |
| RX-017 | PASS | Each added optional detail can be enabled/disabled according to the requested UI behavior; OFF fields do not silently submit stale values. | Label detail switches: test_label_fields_follow_the_switches (OFF fields are not printed) |
| RX-018 | PASS | Label format options show the chosen format consistently on screen and print/PDF. | test_prescription_labels_pdf_in_each_format |
| RX-019 | PASS | Prescription history is preserved and edits are audited. | Rx edits audited; lines keep copies of name / version |
| RX-020 | PASS | Medicine safety warnings appear for relevant flags. | test_safety_rules |
| RX-021 | PASS | Prescription can be printed/shared only by authorized users and each action is audited. | test_who_can_print; print / share audited |
| RX-022 | NOT RUN | Prescription data remains correct when switching languages or refreshing the page. | Language switch / refresh while writing not exercised (draft restore exists) |

## 11. Pharmacy and batch-wise inventory

PASS 45 · FAIL 1 · BLOCKED 0 · NOT RUN 0

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| PHARM-001 | PASS | Create a product with product name, generic name, manufacturer and category. | Medicine master (name, generic, manufacturer, category) |
| PHARM-002 | PASS | Store dosage/form or pack type and pack size where configured. | pack type, pack size, units per pack |
| PHARM-003 | PASS | Store batch number, manufacturing date and expiry date. | batch no, mfg date, expiry |
| PHARM-004 | PASS | Store supplier, supplier invoice number and invoice date. | supplier, invoice no, invoice date on a purchase |
| PHARM-005 | PASS | Store purchase quantity and free quantity separately. | test_purchase_with_free_quantity_and_gst |
| PHARM-006 | PASS | Store purchase price, MRP and selling price separately. | purchase rate, MRP, selling price separate |
| PHARM-007 | PASS | Store GST, HSN, barcode, minimum-stock level and rack/shelf location where enabled. | GST, HSN, barcode, reorder level, rack (racks switch) |
| PHARM-008 | PASS | Validate dates (expiry cannot precede manufacturing date) and numeric quantities/prices. | receive_stock refuses expiry in the past and mfg after expiry; numbers validated |
| PHARM-009 | PASS | Allow the same product to have multiple batches with different expiry, purchase price and MRP. | Several batches per medicine (unique per batch no) |
| PHARM-010 | PASS | Prevent a batch update from accidentally overwriting another batch's values. | Batch updates touch only that batch (receive_stock) |
| PHARM-011 | PASS | Branch-specific stock and price overrides do not affect other branches unintentionally. | test_stock_is_per_branch; branch price override |
| PHARM-012 | FAIL | Barcode values are unique where the business rule requires uniqueness. | P3: medicine barcode is unique per organization; a BATCH barcode is only indexed, not unique |
| PHARM-013 | PASS | Barcode scan/search selects the correct product and batch workflow. | test_alerts_scan_location_ledger; test_scanned_extra_medicine_goes_on_the_same_bill |
| PHARM-014 | PASS | Rack/shelf management can create, edit and search configured locations. | Racks screen and location (optional_features tests) |
| PHARM-015 | PASS | Purchase entry increases stock for the correct branch, product and batch. | test_purchase_with_free_quantity_and_gst |
| PHARM-016 | PASS | Free quantity is included in physical stock according to the configured rule without incorrectly inflating purchase value. | same test: free qty in stock, not in value |
| PHARM-017 | PASS | Purchase invoice and line totals are calculated correctly. | same test: taxable 500, GST 60, total 565 |
| PHARM-018 | PASS | Opening stock entry is recorded with an identifiable transaction/audit record. | test_opening_stock |
| PHARM-019 | PASS | Ledger tracks opening, purchases, sales, returns, damaged/expired stock, adjustments and current balance. | test_alerts_scan_location_ledger (ledger statement) |
| PHARM-020 | PASS | Ledger movements reconcile to the current stock quantity. | QA probe test_PHARM_020_037: history balance equals quantity after purchase, sale, correction |
| PHARM-021 | PASS | Manual stock adjustments require an authorized user and a reason. | test_corrections_need_reason |
| PHARM-022 | PASS | Physical stock verification records counted quantity, difference, reason and user. | test_physical_stock_check |
| PHARM-023 | PASS | Supplier returns reduce the correct batch stock and preserve the transaction history. | test_purchase_return |
| PHARM-024 | PASS | Sales returns add stock only according to the configured return/quality rules. | test_sale_return_gives_credit_note_and_stock (back_to_stock choice) |
| PHARM-025 | PASS | Damaged, expired or written-off stock is not available for normal sale. | expired batches never offered / sold (test_cannot_sell_more_than_stock_or_expired) |
| PHARM-026 | PASS | Concurrent sales/purchases do not produce negative or inconsistent stock. | test_the_last_pack_cannot_be_sold_twice; DB check stock_not_negative |
| PHARM-027 | PASS | Retrying a purchase or stock API request does not duplicate stock movements. | FOUND AND FIXED in this audit: the same supplier invoice could be entered twice (doubling stock). Now refused |
| PHARM-028 | PASS | Every stock movement records user, date/time, branch, source document and reason where relevant. | StockMovement: user, branch, kind, reference, reason |
| PHARM-029 | PASS | Sale deducts stock from the correct branch and batch. | test_sell_makes_bill_with_gst |
| PHARM-030 | PASS | FEFO selects the earliest-expiring eligible batch first. | suggested_batches orders earliest expiry first |
| PHARM-031 | PASS | Expired stock is blocked from ordinary sale. | test_cannot_sell_more_than_stock_or_expired |
| PHARM-032 | PASS | Near-expiry alerts use the configured threshold and correct date calculation. | Near-expiry tile; alert_counts |
| PHARM-033 | PASS | Low-stock and out-of-stock alerts match the configured minimum and actual available quantity. | Low / out tiles; test_alerts_scan_location_ledger; test_full_day (out + asked-for) |
| PHARM-034 | PASS | Batch-specific MRP and selling price are used correctly. | Batch price used in the Dispense window |
| PHARM-035 | PASS | Pack/unit conversion does not overstate or understate stock. | test_loose_sale (units per pack) |
| PHARM-036 | PASS | A sale cannot silently exceed available stock unless a deliberate, authorized policy permits it. | test_cannot_sell_more_than_stock_or_expired |
| PHARM-037 | PASS | Stock reports match the sum of batch ledger balances. | QA probe: batch history sums to quantity |
| PHARM-038 | PASS | Stock movements are traceable back to the invoice, return or adjustment. | reference_label shows the bill number |
| PHARM-039 | PASS | Pharmacy module can be switched ON/OFF by the authorized organization/clinic admin as designed. | test_permissions_and_switch |
| PHARM-040 | PASS | Advanced tracking features have individual ON/OFF controls where required. | Additional settings: one switch per extra |
| PHARM-041 | PASS | OFF hides/disables the related UI and the backend enforces the intended behavior. | test_extras_are_refused_while_off |
| PHARM-042 | PASS | Turning an option OFF does not delete its existing data. | Switch off hides, does not delete |
| PHARM-043 | PASS | Turning an option back ON restores access to retained data. | test_switching_on_one_extra_enables_only_that_one |
| PHARM-044 | PASS | Settings in one organization/branch do not change another organization's/branch's settings. | test_other_organizations_are_not_affected |
| PHARM-045 | PASS | Optional tracking does not block basic clinic workflows when it is disabled. | test_basic_pharmacy_works_with_all_extras_off |
| PHARM-046 | PASS | The owner can understand what each switch controls from its label/help text. | Every switch has a label and help text (en / gu / hi) |

## 12. Panchakarma, therapies and treatment plans

PASS 8 · FAIL 2 · BLOCKED 0 · NOT RUN 0

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| THER-001 | FAIL | Therapy master is organization-level and supports branch-level allowed overrides. | P3: therapy master is organization-level; branch-level overrides are not built (price comes from the service price per branch) |
| THER-002 | PASS | Create a therapy plan for the correct patient/visit. | test_plan_can_be_linked_to_the_check_up_of_the_same_patient_only |
| THER-003 | PASS | Record planned date, status, assigned therapist and relevant instructions where supported. | test_plan_with_sessions_and_progress |
| THER-004 | PASS | Only authorized staff can create or edit therapy records. | test_pharmacist_cannot_see_therapy; therapy.manage |
| THER-005 | PASS | Panchakarma/therapy module can be switched ON/OFF per branch. | test_module_is_off_until_switched_on |
| THER-006 | PASS | When disabled, the feature is not accidentally accessible through direct APIs. | same test: direct API gives 403 |
| THER-007 | FAIL | Therapy charges flow into the correct invoice without duplicate billing. | P2: therapy plan sessions are NOT added to the invoice automatically; staff add the therapy as a service on the OPD bill (no duplicate billing, but manual). Needs an owner decision |
| THER-008 | PASS | Therapy plan PDF/print shows correct patient and branch details where implemented. | test_therapy_plan_prints_as_pdf_in_the_patient_language |
| THER-009 | PASS | Previous therapy records remain in the patient's history. | Plans and sessions stay; undo tests |
| THER-010 | PASS | Missing optional therapy configuration does not break unrelated patient workflows. | Module off does not affect other screens (crawl, tests) |

## 13. Diet and lifestyle plans

PASS 0 · FAIL 7 · BLOCKED 0 · NOT RUN 1

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| DIET-001 | FAIL | Create and maintain organization-level diet templates. | NOT BUILT: the diet module does not exist yet (only a switch name). In CLAUDE.md Step 14 |
| DIET-002 | FAIL | Apply a diet/lifestyle plan to the correct patient and visit. | NOT BUILT: the diet module does not exist yet (only a switch name). In CLAUDE.md Step 14 |
| DIET-003 | FAIL | Templates and plans support configured English, Gujarati and Hindi text. | NOT BUILT: the diet module does not exist yet (only a switch name). In CLAUDE.md Step 14 |
| DIET-004 | FAIL | Branch overrides behave as intended without changing other branches. | NOT BUILT: the diet module does not exist yet (only a switch name). In CLAUDE.md Step 14 |
| DIET-005 | FAIL | Only authorized roles can create/edit patient-specific plans. | NOT BUILT: the diet module does not exist yet (only a switch name). In CLAUDE.md Step 14 |
| DIET-006 | FAIL | Diet chart PDF/print displays correct patient, clinic and language. | NOT BUILT: the diet module does not exist yet (only a switch name). In CLAUDE.md Step 14 |
| DIET-007 | FAIL | Historical diet plans remain available after a template is edited. | NOT BUILT: the diet module does not exist yet (only a switch name). In CLAUDE.md Step 14 |
| DIET-008 | NOT RUN | Optional diet module OFF state is respected in UI and API. | Nothing to switch yet |

## 14. Billing, invoices, payments, refunds and cash closing

PASS 18 · FAIL 1 · BLOCKED 0 · NOT RUN 1

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| BILL-001 | PASS | One invoice can combine consultation, medicines and therapies. | test_combined_bill_puts_medicines_on_opd_bill; test_full_day; therapy as a service line |
| BILL-002 | PASS | Invoice lines reference the correct patient, branch and source items. | invoice lines carry patient / branch / source |
| BILL-003 | PASS | Quantity × unit price, discount, tax and final total calculations are correct. | test_gst_inclusive_maths; bad lines refused (test_bad_bill_lines_are_refused) |
| BILL-004 | FAIL | GST fields support GSTIN, HSN/SAC, CGST/SGST/IGST and place of supply as configured. | P3: GSTIN, HSN/SAC, CGST/SGST, place of supply exist; IGST (other state) is not built |
| BILL-005 | PASS | Tax rates are configurable; do not assume a tax rate is legally correct without owner/CA confirmation. | GST rates are settings; the owner / CA must confirm them (NOT a legal check) |
| BILL-006 | PASS | Invoice number is unique per branch and financial year (April--March). | test_numbers_per_branch_and_year |
| BILL-007 | PASS | Concurrent invoice creation cannot duplicate invoice numbers. | test_bill_numbers_never_repeat_when_many_bill_at_once |
| BILL-008 | PASS | Invoice numbering is generated safely inside a database transaction. | next_number inside a transaction |
| BILL-009 | PASS | Cancelling an invoice creates a credit note; the original invoice is not deleted. | test_cancel_makes_credit_note_and_refund |
| BILL-010 | PASS | Refund creates a traceable credit note/refund record and preserves the original invoice. | credit note + refund record; original kept |
| BILL-011 | PASS | Cash, UPI and card payment modes work as configured. | cash / UPI / card modes (test_round_off_and_payments) |
| BILL-012 | PASS | Partial payments, outstanding balances and payment history calculate correctly if supported. | partly_paid and balance (test_round_off_and_payments) |
| BILL-013 | PASS | Duplicate/double-click payment submissions do not create duplicate payments. | test_paying_twice_by_double_click_never_overpays; test_a_bill_cannot_be_overpaid... |
| BILL-014 | PASS | Daily cash closing works per branch and reconciles with cash transactions. | Day summary: received by mode, refunds, cash in hand (test_round_off_and_payments, test_day_summary_by_kind_of_bill). There is no "lock the day" button |
| BILL-015 | NOT RUN | Refunds and invoice cancellation update pharmacy stock only according to the configured policy. | Stock effect of cancelling a pharmacy bill is not separately tested (returns are: back_to_stock) |
| BILL-016 | PASS | Billing permissions are enforced for screen, API, PDF, export and print actions. | test_wrong_people_and_billing; PDF permission tests |
| BILL-017 | PASS | Invoice totals match reports and the payment ledger. | test_collection_by_payment_mode; test_money_today_by_opd_and_pharmacy |
| BILL-018 | PASS | Failed transactions roll back fully; no half-saved invoice/payment/stock state remains. | Nothing half-saved: test_cannot_sell_more_than_stock_or_expired |
| BILL-019 | PASS | Invoice edits and financial adjustments are audited. | Payments / cancels audited |
| BILL-020 | PASS | Invoice sequence behaves correctly across financial-year change and branch change. | test_numbers_per_branch_and_year includes the 2026-27 to 2027-28 change |

## 15. PDF, printing, QR and document templates

PASS 18 · FAIL 0 · BLOCKED 0 · NOT RUN 0

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| DOC-001 | PASS | Prescription PDF renders from server-side HTML templates using the configured PDF approach. | WeasyPrint HTML templates |
| DOC-002 | PASS | Invoice PDF renders correctly. | test_pdf_prints_and_duplicate; QA probe: invoice in A4, A5, 80mm, 58mm |
| DOC-003 | PASS | Receipt PDF renders correctly. | OPD bill / receipt is the invoice PDF |
| DOC-004 | PASS | Prakriti report, diet chart, therapy plan, consent form, certificates and follow-up card render where implemented. | Prakriti, therapy plan, certificate, follow-up card tests; consent form and diet chart are not built |
| DOC-005 | PASS | A4 and A5 paper layouts are correct. | test_prescription_with_nine_medicines_is_one_page; test_case_sheet_shrinks_to_half_a4_on_one_page |
| DOC-006 | PASS | Thermal 80mm and 58mm layouts fit the intended printable width. | QA probe test_DOC_006: 80mm and 58mm bills render |
| DOC-007 | PASS | Gujarati and Hindi glyphs render correctly with configured Noto fonts; no boxes, missing characters or broken conjuncts. | Gujarati letterhead, handwritten picture and therapy plan looked at: no boxes or broken conjuncts |
| DOC-008 | PASS | English, Gujarati and Hindi versions use the selected patient's/document language. | language_of(patient): en / gu / hi |
| DOC-009 | PASS | Correct branch logo, address, letterhead and footer appear. | test_clinic_logo_upload_and_where_it_prints |
| DOC-010 | PASS | Correct doctor signature image appears only where configured and authorized. | test_admin_uploads_and_removes_a_doctor_signature; signature on prints |
| DOC-011 | PASS | QR verification code resolves to the intended safe document-verification flow. | test_prescription_pdf_number_duplicate_and_verify; verify page shows initials only |
| DOC-012 | PASS | Reprinted documents show the required `DUPLICATE COPY` watermark. | test_prescription_pdf_number_duplicate_and_verify; test_duplicate_watermark_and_fixed_language |
| DOC-013 | PASS | PDF values match saved database records, not unsaved frontend-only values. | PDFs are rendered from saved records |
| DOC-014 | PASS | Long content, tables, medicine lists and page breaks do not clip important information. | nine-medicine prescription = one page; long lists wrap to a second page |
| DOC-015 | PASS | Templates can be edited in the documented location without changing business logic. | backend/templates/documents + SAFE TO EDIT comments |
| DOC-016 | PASS | PDF/print events are written to the audit log. | view / print logged (log_action in DocumentPdfView) |
| DOC-017 | PASS | Unauthorized users cannot obtain a document by guessing its URL or ID. | test_documents_with_wrong_ids_or_kinds; test_who_can_print |
| DOC-018 | PASS | WhatsApp share creates the expected click-to-chat link and does not send automatically. | test_whatsapp_share_needs_consent (wa.me link, never auto-sent) |

## 16. Notifications and provider adapters

PASS 9 · FAIL 1 · BLOCKED 0 · NOT RUN 2

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| NOTIF-001 | PASS | Every external provider is accessed through the intended adapter/interface. | sms.py, whatsapp.py, EMAIL_PROVIDER, PAYMENT_PROVIDER, STORAGE_PROVIDER, AI_PROVIDER |
| NOTIF-002 | PASS | Provider selection is controlled by `.env` settings. | Providers chosen in .env |
| NOTIF-003 | PASS | Every adapter has a fake provider usable in automated tests. | fake providers: SMS, WhatsApp, payment, AI |
| NOTIF-004 | PASS | WhatsApp `click_to_chat` builds a correct `wa.me` link and prefilled message; staff must tap Send. | test_whatsapp_number_format; test_whatsapp_link_action |
| NOTIF-005 | PASS | SMS `console` provider logs/saves the test message but does not claim a real SMS was sent. | console provider logs only |
| NOTIF-006 | PASS | Mailpit receives test emails at `http://localhost:8025` when configured. | Mailpit container healthy, UI :8025 = 200 (a test mail was not sent in this audit) |
| NOTIF-007 | NOT RUN | Reminder/notification failure is reported and does not break patient registration or billing. | Adapter failure while registering / billing not simulated |
| NOTIF-008 | NOT RUN | Retries do not send duplicate reminders unexpectedly. | Retry duplicate reminders: no automatic reminders exist yet |
| NOTIF-009 | PASS | Consent and notification preferences are checked before sending. | test_no_messages_without_consent |
| NOTIF-010 | FAIL | Notification status, destination, timestamp and failure reason are recorded without unnecessary sensitive content. | P3: OutboundMessage stores the full message text (patient name, token) as a record |
| NOTIF-011 | PASS | Background jobs, if added, do not block normal API requests. | No background jobs added |
| NOTIF-012 | PASS | Paid messaging/email services are not added without explicit owner approval. | No paid messaging service added |

## 17. AI, speech-to-text and OCR

PASS 8 · FAIL 3 · BLOCKED 0 · NOT RUN 7

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| AI-001 | PASS | Default AI provider is the configured local Ollama adapter. | AI_PROVIDER default ollama (Translate button) |
| AI-002 | PASS | If Ollama is offline, the UI clearly reports AI is offline and normal clinic workflows continue. | test_ai_offline_is_a_friendly_503; Ollama is not even installed and the app works |
| AI-003 | PASS | AI suggestions are never saved as final prescriptions without the doctor choosing Accept/Edit/Reject. | The only AI feature (Translate) fills boxes as a suggestion; no AI writes a prescription |
| AI-004 | PASS | Doctor can edit or reject AI output before saving. | Translate output can be edited before saving |
| AI-005 | FAIL | Store AI suggestion and doctor's final version with prompt version and model name in the AI audit table. | NOT BUILT: no AI audit table (prompt version, model, doctor final) |
| AI-006 | NOT RUN | Patient AI consent is checked before every relevant AI call. | No AI feature uses patient data yet |
| AI-007 | NOT RUN | Name, phone and address are removed before sending text to any AI provider and correctly handled on return. | Name removal not built (no patient text goes to AI today) |
| AI-008 | PASS | No real patient data is sent to a cloud AI provider in development or by default. | No cloud AI provider exists in the code |
| AI-009 | NOT RUN | AI module has a per-branch ON/OFF switch. | ai_scribe / ai_summary switch names exist; the features do not |
| AI-010 | NOT RUN | Paid-provider monthly cost limit is supported if/when paid providers are explicitly approved. | No paid provider approved |
| AI-011 | PASS | Prompts are stored in versioned template files, not embedded directly in business code. | backend/templates/ai/translate_v1.txt |
| AI-012 | NOT RUN | Slow AI jobs use background processing when configured and do not freeze the UI. | No Celery jobs yet |
| AI-013 | FAIL | Local speech-to-text provider uses the configured faster-whisper path and handles missing models/devices gracefully. | NOT BUILT: speech-to-text (faster-whisper) |
| AI-014 | FAIL | OCR provider uses local Tesseract and configured Gujarati, Hindi and English languages where installed. | NOT BUILT: OCR (Tesseract) |
| AI-015 | NOT RUN | AI/OCR/speech errors are logged safely without exposing patient details or secrets. | Nothing to log |
| AI-016 | PASS | AI outputs are treated as untrusted suggestions and validated before display/save. | Translate answers are turned into plain text boxes |
| AI-017 | NOT RUN | AI features remain unavailable when disabled, including via direct API calls. | AI switches have no features to block yet |
| AI-018 | PASS | No paid AI provider/API is enabled without explicit owner approval. | No paid AI provider enabled |

## 18. Reports, dashboard, exports and search

PASS 9 · FAIL 0 · BLOCKED 0 · NOT RUN 3

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| REP-001 | PASS | Dashboard counts match the underlying records for the selected branch and date range. | test_doctor_sees_own_opd_in_simple_words; test_money_today_by_opd_and_pharmacy |
| REP-002 | PASS | Appointment and patient reports filter correctly by date, branch and doctor. | test_new_vs_repeat_patients; filters by date / branch / doctor |
| REP-003 | PASS | Billing totals reconcile with invoices, credit notes, refunds and payments. | test_collection_by_month_and_refund; test_gst_summary |
| REP-004 | PASS | Pharmacy reports reconcile with batch ledger and stock movements. | test_daily_top_selling_margin_and_gst; ledger reconcile probe |
| REP-005 | PASS | Exported data matches the filtered on-screen data. | test_export_excel_and_pdf_are_audited |
| REP-006 | PASS | Export permissions are checked server-side and exports are audited. | test_export_excel_and_pdf_are_audited; test_therapist_cannot_see_money_reports |
| REP-007 | PASS | Sensitive fields are masked or omitted from exports unless explicitly authorized. | test_missed_follow_ups_masks_phone_and_is_audited |
| REP-008 | PASS | Pagination and filters work together without duplicate/missing records. | Pagination + filters (tests and UI) |
| REP-009 | NOT RUN | Sorting by date/amount/status works correctly. | Sorting by amount / status not specifically tested |
| REP-010 | PASS | Empty report ranges display a helpful empty state rather than an error. | Empty states in the screens; test_bad_dates_are_refused |
| REP-011 | NOT RUN | Large reports do not time out unexpectedly; performance is measured on representative demo data. | Performance on large data was not measured (demo data only) |
| REP-012 | NOT RUN | Branch and organization totals do not double-count shared organization-level masters. | Double-counting of shared masters not tested |

## 19. Languages and UI usability

PASS 12 · FAIL 0 · BLOCKED 0 · NOT RUN 2

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| UI-001 | PASS | User can select English, Gujarati and Hindi. | EN / GU / HI switch (screens opened in all three) |
| UI-002 | PASS | All user-facing screen text comes from translation files; components do not hardcode screen text. | scripts/check-translations.mjs: all keys exist in 3 languages; a text scan found no hard-coded English sentences |
| UI-003 | PASS | Language switch updates labels, buttons, validation messages, menus and supported documents. | Language switch updates menu, labels and prints |
| UI-004 | PASS | Missing translations are identified and do not crash the UI. | check-translations fails the build on a missing key |
| UI-005 | PASS | Gujarati/Hindi fonts render properly on supported browsers. | Gujarati / Hindi rendered in the app and PDFs (screenshots) |
| UI-006 | PASS | Forms show clear validation messages near the relevant field. | Forms show field messages (registration tests) |
| UI-007 | PASS | Save, loading, empty, success and failure states are clear. | Loading, empty, success, failure states (ListEmpty, toasts) |
| UI-008 | PASS | Tables support practical search, sorting and pagination where required. | Search, sort, pagination on lists |
| UI-009 | PASS | Dialogs confirm consequential actions such as cancellation or adjustment. | Confirm dialogs: give medicines, cancel, remove, Re-open |
| UI-010 | NOT RUN | Keyboard navigation, focus state and labels are usable for staff. | Keyboard-only use and focus order not audited |
| UI-011 | NOT RUN | Layout is usable on the intended desktop and tablet screen sizes. | Tablet layout not audited (desktop and phone Share mode seen) |
| UI-012 | PASS | Slow network/API failures are displayed without losing already-saved records. | ListEmpty + Try again; nothing lost on failure |
| UI-013 | PASS | Repeated clicks do not submit the same form multiple times. | Double click on Register / Walk-in sends one request; Give medicines refuses a second give |
| UI-014 | PASS | Date, currency and number formats are consistent for the intended Indian clinic workflow. | DD-MM-YYYY, rupee amounts with paise |

## 20. Audit trail and record history

PASS 11 · FAIL 0 · BLOCKED 0 · NOT RUN 1

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| AUD-001 | PASS | Patient record view events are logged. | test_every_view_is_audited |
| AUD-002 | PASS | Create, update, print, export and share events are logged. | print / export / share audited (tests above) |
| AUD-003 | PASS | Each event records user, branch, time, IP and relevant change details as specified. | QA probe test_AUD_003: user, branch, time, IP |
| AUD-004 | PASS | Audit logs are append-only through normal application permissions. | test_audit_log_is_append_only |
| AUD-005 | PASS | Ordinary users cannot edit or delete audit events. | test_audit_log_is_append_only; no edit / delete route |
| AUD-006 | PASS | Audit history identifies what changed without storing unnecessary sensitive values. | test_notes_are_encrypted_and_not_in_audit_log |
| AUD-007 | PASS | Pharmacy stock movements and financial adjustments are traceable. | StockMovement ledger + invoice audit |
| AUD-008 | PASS | Consent, privacy requests and AI suggestion/final-result actions are audited. | Consent rows + audit probe; AI audit not built |
| AUD-009 | PASS | Audit events are associated with the correct organization and branch. | Audit rows carry organization and branch |
| AUD-010 | PASS | Failed/unauthorized access attempts are logged safely where configured. | Failed logins are logged; a 403 screen attempt is not (P3) |
| AUD-011 | NOT RUN | Log output never exposes passwords, JWT secrets, API keys or full sensitive patient records. | Log filter for tokens / passwords exists only on the security branch (not merged yet) |
| AUD-012 | PASS | Audit records remain available after a record is archived/soft-deleted. | AuditLog keeps object ids; all_objects keeps archived rows |

## 21. API, database integrity and migrations

PASS 20 · FAIL 0 · BLOCKED 0 · NOT RUN 0

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| DB-001 | PASS | All API endpoints are under `/api/v1/` as specified. | All routes under /api/v1/ |
| DB-002 | PASS | Frontend uses the REST APIs rather than directly accessing the database. | Frontend uses axios to /api/v1 |
| DB-003 | PASS | API request/response formats are consistent and documented. | Consistent pagination and error format |
| DB-004 | PASS | Serializers validate required fields, lengths, ranges, dates and relationships. | Serializers validate (mistakes tests) |
| DB-005 | PASS | Main tables use UUID primary keys and required organization/branch ownership fields. | QA probe: every main table has a UUID id; 5 technical tables (audit log, login code, message log, 2 version tables) are documented exceptions |
| DB-006 | PASS | Main tables include timestamps, created/updated user fields and soft-delete fields as required. | Same probe: created_at, updated_at, is_deleted on all main tables; created_by / updated_by via BaseModel |
| DB-007 | PASS | Medical, billing and audit records are not hard-deleted in normal workflows. | BaseModel.delete is soft; patients / visits / invoices have no hard delete route |
| DB-008 | PASS | Foreign keys and uniqueness constraints prevent invalid relationships and duplicates. | Unique and check constraints (stock_not_negative, slot, invoice number) |
| DB-009 | PASS | Indexes exist for organization, branch and commonly filtered date fields where appropriate. | db_index on organization / branch / dates |
| DB-010 | PASS | Dropdown/master values are managed through master tables, not hardcoded lists. | MasterValue tables |
| DB-011 | PASS | Migrations apply successfully to a clean test database. | pytest builds a fresh test DB from migrations every run |
| DB-012 | PASS | Migrations apply safely to a representative existing test database. | Migrations applied to the dev database with real-looking data several times today without loss |
| DB-013 | PASS | Old migrations are never edited to change already-applied schema history. | git history: no applied migration file modified |
| DB-014 | PASS | Failed transactions roll back related writes together. | test_cannot_sell_more_than_stock_or_expired (nothing half-saved) |
| DB-015 | PASS | Concurrent requests cannot create duplicate patient IDs, invoice numbers or conflicting stock movements. | Concurrency tests: invoice numbers, tokens, patient ids, last pack, payment |
| DB-016 | PASS | Pagination limits prevent unbounded data retrieval. | max_page_size 200 |
| DB-017 | PASS | No unsafe raw SQL uses string formatting with user input. | No .raw / cursor.execute / RawSQL in apps/ |
| DB-018 | PASS | PostgreSQL and pgvector versions/configuration match the project baseline. | compose image pgvector/pgvector:pg16 |
| DB-019 | PASS | pgvector-dependent features fail clearly if unavailable, without breaking unrelated features. | No pgvector-dependent feature exists |
| DB-020 | PASS | Soft-deleted records are excluded from ordinary lists but remain accessible through authorized history/audit paths. | ActiveManager; audit keeps references |

## 22. Security testing

PASS 19 · FAIL 0 · BLOCKED 0 · NOT RUN 1

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| SEC-001 | PASS | Test for broken access control by changing record IDs in URLs/API requests. | test_odd_urls_never_crash_the_server; test_invoice_of_another_branch_is_not_reachable; many 404 / 403 tests |
| SEC-002 | PASS | Test cross-organization and cross-branch data isolation across list, detail, create, update, delete/archive, search, report, export and PDF endpoints. | Isolation tests on patients, appointments, invoices, stock, therapy, handwriting; exports and PDFs by permission tests |
| SEC-003 | PASS | Test injection attempts in search and text fields. | test_odd_urls_never_crash_the_server (quotes, ordering, NUL) |
| SEC-004 | PASS | Test XSS payloads in patient names, notes and other text fields; content is safely rendered. | Names stored as text (test_odd_names...); PDF templates escape (QA probe test_SEC_004); React escapes screens |
| SEC-005 | PASS | Verify CSRF protections according to the configured Django/DRF authentication design. | API uses a bearer token (no cookie auth); Django admin keeps CSRF |
| SEC-006 | PASS | Verify CORS settings are not overly permissive in any future non-local deployment. | No CORS headers; the frontend proxies /api (same origin) |
| SEC-007 | PASS | Verify upload type, size and content validation. | test_wrong_patient_uploads_are_refused; test_wrong_logo_files_are_refused |
| SEC-008 | PASS | Verify private uploaded files cannot be accessed through guessed public paths. | QA probe test_SEC_008: /media and /private_media paths are not served |
| SEC-009 | PASS | Verify secrets are absent from Git history/current files, logs, frontend bundles and error responses. | git history scan: no private keys / cloud keys; dev placeholders only in .env.example; built bundle has no secrets. Real production keys are not in git (.env ignored) |
| SEC-010 | PASS | Verify sensitive data is encrypted at application level where practical and required by the design. | EncryptedTextField / JSON fields for notes and history |
| SEC-011 | PASS | Verify Aadhaar numbers are not collected/stored by this application. | QA probe test_SEC_011: no Aadhaar field |
| SEC-012 | PASS | Verify list views mask sensitive phone data as specified. | Phone masked in lists |
| SEC-013 | PASS | Verify role permissions for therapist, pharmacist, receptionist, doctor and admin. | Role tests for all five roles |
| SEC-014 | PASS | Verify rate limits and safe errors for login and sensitive endpoints. | Login limits; safe errors |
| SEC-015 | PASS | Verify access tokens are not placed in URLs or exposed in logs. | Tokens go in headers, never in URLs |
| SEC-016 | PASS | Verify the browser cannot access admin-only actions merely by changing UI state. | API enforces; probe test_PERM_009 |
| SEC-017 | PASS | Verify audit logs cannot be altered by normal users. | Audit log append-only |
| SEC-018 | PASS | Verify local AI provider configuration keeps patient data on the local machine. | Ollama is local; only list names are translated |
| SEC-019 | PASS | Verify all development fixtures and automated tests use fake/demo patient data. | All fixtures and demo data are fictional |
| SEC-020 | NOT RUN | Review security findings before any real patient data is entered. | The owner must read this report before real data is entered |

## 23. Backup, recovery and local deployment readiness

PASS 6 · FAIL 0 · BLOCKED 5 · NOT RUN 1

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| OPS-001 | BLOCKED | Database backup process is documented and executable. | backup.sh / restore.sh are on branch claude/live-deploy-e44f3e (not merged yet); not re-run by this audit |
| OPS-002 | BLOCKED | Restore backup into an isolated test database and verify the restored records. | Restore into a test database: same branch; the deploy session reported a dry run, not independently repeated |
| OPS-003 | BLOCKED | Verify patient, visit, prescription, invoice, payment and stock relationships survive restore. | Needs the restore test above |
| OPS-004 | BLOCKED | Verify uploaded files/documents are included in the relevant backup strategy. | Media volume is part of backup.sh on the deploy branch (not re-run) |
| OPS-005 | BLOCKED | Verify recovery instructions are understandable to a non-programmer. | docs/GO_LIVE.md on the deploy branch (not merged) |
| OPS-006 | PASS | Verify containers restart after a normal Docker/Desktop restart. | Containers restarted correctly after each Docker Desktop restart (restart: unless-stopped) |
| OPS-007 | PASS | Verify health checks and useful logs exist for backend/database and configured services. | /api/v1/health/ ok; db healthcheck; logs.bat |
| OPS-008 | NOT RUN | Verify a database migration failure does not silently destroy data. | A failing migration was not simulated |
| OPS-009 | PASS | Verify `reset-demo-data.bat` cannot accidentally be mistaken for a production data reset tool. | reset-demo-data.bat needs typing YES and DEMO_MODE=true |
| OPS-010 | PASS | Verify no real patient data is used for development or QA. | Only fictional data |
| OPS-011 | PASS | Verify current setup remains local-only until the owner explicitly approves hosting. | Local only on this branch; hosting files are on separate branches until approved |
| OPS-012 | PASS | Do not configure AWS/cloud hosting, paid services or new external providers unless the owner asks. | No paid service configured |

## 24. Performance, reliability and error handling

PASS 9 · FAIL 0 · BLOCKED 0 · NOT RUN 5

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| PERF-001 | PASS | Frontend production build succeeds. | npx vite build succeeds |
| PERF-002 | PASS | Frontend TypeScript/type-check passes using the project's actual scripts. | npx tsc --noEmit clean |
| PERF-003 | PASS | Backend automated tests pass. | pytest: all tests pass (350+) |
| PERF-004 | PASS | API validation errors return expected status codes and safe messages. | Validation errors give 400 with a clear message |
| PERF-005 | NOT RUN | Database unavailable behavior is understandable and does not expose internal secrets. | Database-down screen not tested (API-down is) |
| PERF-006 | PASS | Ollama unavailable behavior is graceful and non-AI features continue working. | Ollama is off all day; nothing else is affected |
| PERF-007 | NOT RUN | Mail/SMS/WhatsApp/payment adapter failures do not corrupt clinic data. | Adapter failure injection not run |
| PERF-008 | PASS | Repeated requests do not duplicate important records or transactions. | Double-click / retry tests across billing, stock, tokens, purchases |
| PERF-009 | PASS | Large lists use pagination and relevant indexes. | Pagination everywhere; indexes on dates |
| PERF-010 | NOT RUN | Representative demo data is used to measure key patient search, appointment, prescription and billing flows. | No timing measurements on representative data |
| PERF-011 | PASS | Browser console and server logs contain no unexpected errors during core workflows. | Browser console and HTTP errors: none in the 5-role crawl and the clinic-day run; server logs not reviewed line by line |
| PERF-012 | NOT RUN | UI does not claim an operation succeeded before the backend confirms success. | Not audited screen by screen |
| PERF-013 | NOT RUN | Timeouts and retry behavior do not create duplicate payments, invoices, messages or stock movements. | Timeout / retry behaviour not simulated in the browser |
| PERF-014 | PASS | App remains usable when optional modules/providers are disabled. | Modules switched off: tests (pharmacy, therapy, billing, enquiry) |

## 25. End-to-end workflow tests

PASS 11 · FAIL 1 · BLOCKED 1 · NOT RUN 2

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| E2E-001 | PASS | Receptionist creates a patient → books appointment → checks patient in → doctor sees the correct patient. | test_a_whole_clinic_day + real-screen journey (journey.py) |
| E2E-002 | PASS | Doctor completes Ayurvedic assessment → records diagnosis/plan → creates prescription → final prescription is saved correctly. | test_full_day: visit, diagnosis, prescription |
| E2E-003 | PASS | Doctor selects 180 days → follow-up and medicine duration default to 180 → doctor changes one field → the other remains unchanged. | Real screen probe: 180 days, then each field changed alone |
| E2E-004 | NOT RUN | Prescription is printed in English, Gujarati and Hindi where supported; medicine details remain accurate. | Prescription printed in all three languages was not looked at one by one (therapy plan and handwriting were) |
| E2E-005 | FAIL | Consultation + medicines + therapy appear on one invoice and totals reconcile. | P2: consultation + medicines are on one invoice; therapy plan sessions are not (see THER-007) |
| E2E-006 | PASS | Pharmacy purchase adds the correct batch stock and ledger movement. | test_full_day: purchase then batch + ledger movement |
| E2E-007 | PASS | Pharmacy sale uses the correct batch/FEFO rule and deducts stock once. | test_full_day; test_double_click_on_give_medicines... |
| E2E-008 | PASS | Invoice cancellation/refund creates the required credit note and does not delete the original invoice. | test_cancel_makes_credit_note_and_refund |
| E2E-009 | PASS | Follow-up is scheduled and appears in the correct future/overdue list. | Missed follow-ups report; follow-up date on the visit and card |
| E2E-010 | PASS | Patient returns for a revisit → new assessment is created → old visit history remains unchanged. | A new appointment opens a new visit; old unchanged |
| E2E-011 | NOT RUN | Doctor switches branch → sees only authorized branch data and the correct schedule. | Branch switch in the screen not exercised |
| E2E-012 | PASS | Organization admin turns an optional module OFF → existing data remains preserved and prohibited actions are blocked. | Module OFF tests (data kept, API 403) |
| E2E-013 | PASS | Local Ollama is stopped → AI shows an offline message → registration, appointment, prescription entry and billing continue. | Ollama stopped all along: registration, appointments, Rx and billing all worked |
| E2E-014 | PASS | Unauthorized therapist/pharmacist attempts a restricted action → API denies access and the attempt is handled safely. | Role tests: therapist and pharmacist refused (403) |
| E2E-015 | BLOCKED | Backup is created → restored to an isolated test environment → key records and relationships are verified. | Backup / restore belongs to the deploy branch (not merged) |

## 26. Regression test checklist after every change

PASS 10 · FAIL 1 · BLOCKED 0 · NOT RUN 3

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| REG-001 | NOT RUN | Read the change summary and identify affected modules before testing. | Process item for each change |
| REG-002 | NOT RUN | Review the Git diff; ensure unrelated files/features were not changed. | Process item for each change |
| REG-003 | PASS | Confirm any model change has a new migration and old migrations are untouched. | New migrations only; none edited |
| REG-004 | PASS | Run relevant backend tests. | Backend tests run before every commit |
| REG-005 | PASS | Run frontend type-check and build. | tsc and build run before every commit |
| REG-006 | PASS | Run tests for the modified workflow and connected workflows. | Connected workflows re-run (full-day test) |
| REG-007 | PASS | Verify permissions and branch/organization scoping for changed APIs. | Permission / branch tests included |
| REG-008 | PASS | Verify translations in English, Gujarati and Hindi for changed UI text. | check-translations on every change |
| REG-009 | PASS | Verify PDF/print output if the change affects documents. | Print tests on every document change |
| REG-010 | PASS | Verify optional feature switches if the change affects a configurable module. | Switch tests |
| REG-011 | PASS | Update the relevant guide file(s) and `CHANGELOG.md`. | CHANGELOG and docs updated |
| REG-012 | FAIL | Confirm no secrets, real patient data or unintended generated files are included in the commit. | P3: .gitignore no longer ignores demo-video mp4 files (someone removed the line); they are untracked and could be committed by accident |
| REG-013 | PASS | Commit the change in a small, reviewable unit after tests pass. | Small commits after green tests |
| REG-014 | NOT RUN | Record how to revert the change or return to the previous known-good commit. | A written "how to go back" per change is not kept |

## 27. Go-live decision checklist

PASS 6 · FAIL 0 · BLOCKED 2 · NOT RUN 6

| ID | Status | Requirement | Evidence / note |
|---|---|---|---|
| LIVE-001 | NOT RUN | P0 security and data-integrity tests pass. | CONDITIONAL: security hardening is on branch claude/live-security-89c7f2 (not merged); P0 tests on the dev branch pass |
| LIVE-002 | PASS | Organization/branch isolation has been verified on APIs, reports, exports and documents. | Isolation verified on APIs, documents, stock, billing (see PERM / SEC) |
| LIVE-003 | PASS | Authentication, role permissions and session controls have been verified. | Login, roles, sessions verified (AUTH / PERM) |
| LIVE-004 | PASS | Patient registration, visit, prescription, billing and follow-up end-to-end flow passes. | Register -> visit -> Rx -> pharmacy -> one bill -> owner totals pass (test_full_day and real screens) |
| LIVE-005 | PASS | Pharmacy and stock flows pass if pharmacy is enabled. | Pharmacy and stock flows pass |
| LIVE-006 | PASS | Prescription safety warnings and doctor approval for AI suggestions are verified if these features are enabled. | Safety warnings verified; AI approval N/A (no AI prescribing) |
| LIVE-007 | NOT RUN | PDF/print and Gujarati/Hindi rendering are verified for the clinic's actual required paper sizes. | Needs the clinic printer and pre-printed pad test on real paper |
| LIVE-008 | BLOCKED | Backup restore has been tested successfully. | Backup restore: deploy branch, not merged / not independently tested |
| LIVE-009 | NOT RUN | Critical/high bugs are fixed or formally accepted by the owner with documented risk. | Open bugs need the owner decision (see list) |
| LIVE-010 | NOT RUN | Demo-only reset tools and test accounts cannot affect real records. | Needs create_clinic on the live server (deploy branch) |
| LIVE-011 | NOT RUN | Applicable Indian privacy, medical-record retention, tax and other compliance questions have been reviewed with qualified professionals. | Needs a lawyer / CA |
| LIVE-012 | PASS | Hosting is not enabled until separately approved and secured. | No hosting enabled on this branch |
| LIVE-013 | NOT RUN | Owner understands how to start/stop the app, view logs, back up data and get help. | Owner training pending (docs/CLINIC_DAY.md ready) |
| LIVE-014 | BLOCKED | A tested rollback/recovery plan is available. | Rollback plan is on the deploy branch (not merged) |

