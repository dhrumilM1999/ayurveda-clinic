# Small changes you can make yourself

After saving a file, wait a few seconds. The browser updates by itself.
If it doesn't, press **F5**. If something breaks, undo your change (Ctrl+Z, save), or ask Claude Code.

> Tip: before changing things, ask Claude Code to **"commit to git"**. Then you can always go back.

---

## Change the clinic name, colours, fonts or logo

Open `frontend/src/config/clinic.ts`:

```ts
appName: 'Ayurveda Clinic',   // ← your clinic name
colors: {
  primary: '#1f5c45',         // ← buttons, links (forest green)
  sidebar: '#12382a',         // ← left menu and login panel (darker green)
  accent: '#c98a2b',          // ← highlights (turmeric gold)
  background: '#f6f3ec',      // ← page background (cream)
  ...
},
borderRadius: 10,             // ← roundness of corners
```
Pick colours at https://htmlcolorcodes.com and copy the `#xxxxxx` code.

**Fonts:** English uses *Plus Jakarta Sans*, Gujarati uses *Hind Vadodara*, Hindi uses *Hind*, and
titles use *Fraunces*. They are stored inside the project, so they work without internet. To use a
different font, ask Claude Code (the font has to be added to the project first).

**Logo:** replace `frontend/public/logo.svg` with your logo. To use a PNG instead, put
`logo.png` in `frontend/public/` and set `logoPath: '/logo.png'`.

**Login page sentence and the small line under the name:** these are screen text. Change them in
`frontend/src/i18n/en.json`, `gu.json`, `hi.json` → `"login" → "quote"` and `"layout" → "tagline"`.

The clinic name printed on documents and bills is set on the **Settings** screen.

## Change Gujarati or Hindi text

1. Open `frontend/src/i18n/gu.json` (Gujarati) or `hi.json` (Hindi).
2. Find the English text in `en.json` to see which key it uses, e.g. `"save": "Save"`.
3. In `gu.json`, change only the text **after** the colon: `"save": "સાચવો"`.
4. Keep the quotes and commas exactly as they are.
5. Keep words in `{{curly}}` brackets unchanged, e.g. `{{name}}`.

Check: in VS Code's terminal run `cd frontend` then `npm run check:i18n`. It tells you if a key is missing.

## Edit a print template

Print templates come in **Step 7**. They will live in `backend/templates/documents/`.
This section will then explain how to edit them.

## Add a role or change what a role can do

**Easiest (no code):** log in as `admin` → **Roles & permissions** → **Add role**, or **Edit**,
then tick the permissions and save.

The default roles for *new* organizations are in `backend/apps/accounts/permissions_catalog.py`
(the `DEFAULT_ROLES` part).

## Add a new permission

1. In `backend/apps/accounts/permissions_catalog.py` add a line to `PERMISSIONS`:
   `"reports.export": "Export reports",`
2. In each of `frontend/src/i18n/en.json`, `gu.json` and `hi.json`, under `"permissions"`, add
   `"reports_export": "Export reports"` (dot → underscore). This step is optional.
3. A permission only *does* something when a screen checks it, so ask Claude Code to use it.

## Add a menu item

Open `frontend/src/config/menu.tsx` and copy a line, e.g.:
```tsx
{ key: 'audit', path: '/audit-log', labelKey: 'menu.audit', icon: <AuditOutlined />, permission: 'audit.view' },
```
The `path` must be a screen that exists in `src/App.tsx`. Add the label text under `"menu"` in all
three language files. (A brand-new screen needs code, so ask Claude Code.)

## Add a dropdown value

Dropdown values are kept in the database, not in code.
- **Room types:** go to **Rooms** → **Room types** → type a new name → **Add**. To hide one, switch it off.
- **Patient lists** (title, blood group, relation, medical conditions, allergy types, document types,
  "how did they hear of us"): for now, use the technical admin site
  http://localhost:8000/admin/ → **Master values** → **Add**. Pick the list (category), type a short code
  (e.g. `piles`), the English label, and the Gujarati and Hindi labels. A proper editing screen comes in Step 9.
- The *starting* values for new clinics are in `backend/apps/common/masters_catalog.py`.

## Change the patient ID prefix

**Settings** → "Patient ID prefix" (for example `AY` → `AY26-000001`). New patients get the new prefix;
old IDs never change.

## Change the consent wording

The starting text is in `backend/apps/patients/consent_catalog.py` (English, Gujarati, Hindi).
It is SAMPLE text: have a lawyer check it. Text already copied into the database can be changed in the
admin site (http://localhost:8000/admin/ → Consent purposes). **Raise the version number** when you change
the meaning, so the app asks existing patients again.

## One branch or many branches

The software starts in **one-branch mode**: no branch picker at the top and no **Branches** menu.
When you open a second branch: log in as `admin` -> **Settings** -> switch on **Use more than one branch** -> **Save**.
Switching it off again hides the other branches; nothing is deleted. Only the owner account (`admin`) sees this switch.

## Switch a module on or off for one branch

**Settings** → "Modules in <branch>" → flip the switch.
The list of switches is in `backend/apps/organizations/features_catalog.py`.

## Add a simple field (with migration)

Example: add "Landmark" to branches.
1. In `backend/apps/organizations/models.py`, in `class Branch`, add:
   `landmark = models.CharField(max_length=200, blank=True)`
2. Add `"landmark"` to the `fields` list in `backend/apps/organizations/serializers.py` (BranchSerializer).
3. Create the database change. In the VS Code terminal (with the app running) run:
   `docker compose exec backend python manage.py makemigrations`
   Then restart: `stop.bat`, `start.bat` (this applies the change).
4. Add the input box in `frontend/src/pages/BranchesPage.tsx` (copy the `city` line), and add the
   label `"landmark"` in the three language files under `"branches"`.

Changing the database is an **ASK FIRST** change. It's fine to try, but ask Claude Code to review it.

## Add check-up chips (complaints, diagnoses, advice)

The quick-pick chips on the check-up screen are dropdown lists. Add one in the technical admin site:
http://localhost:8000/admin/ -> **Master values** -> **Add**. Category `complaint`, `diagnosis` or `advice`,
a short code (e.g. `pandu`), the English, Gujarati and Hindi text. The doctor can also simply type new words
in the search box and press Enter (that does not add it to the list).

## Change or add a check-up template (Ashtavidha, Prakriti...)

**No code needed:** log in as `admin` -> **Check-up templates**.
- **Edit**: change question and answer text (English, Gujarati, Hindi), add or remove questions and answers,
  move questions up/down. Answer types: one answer, many answers, number (with unit), notes.
- **Add template**: a new form (e.g. "Nadi detail", "Skin examination").
- **Add Prakriti-type questionnaire**: every answer counts for Vata, Pitta or Kapha; the score is calculated.
- **Active** switch: hide a template from the check-up screen (it is never deleted).
- Saving changed questions makes a **new version**. Old check-ups still show the questions they were filled with.

The starting templates for a *new* clinic are in `backend/apps/emr/templates_catalog.py`.
The Prakriti questions are a SAMPLE - the doctor should review and replace them.

## Add or change a medicine

**Medicines** screen (pharmacist or admin): **Add medicine** or the pencil button. Classical medicines use the
official name and AFI/API reference; Patent & Proprietary brands have a manufacturer and can be linked to their
classical equivalent. Fill **Other names** (Sanskrit, English, Hindi, Gujarati) so searching works.
Every save keeps a version; old prescriptions keep what was prescribed. Medicines are never deleted: switch
**In use** off.

## Import your whole medicine list from Excel

**Medicines** -> **Import** -> **Download template**. Fill one row per medicine (type `classical` or
`proprietary`; dosage form, unit, when and anupana as the short code or the English name, e.g. `churna`,
`g`, `after_food`, `warm_water`; flags as `yes` / `no`). Drop the file: the preview shows new / changed rows and
problems, nothing is saved until you click **Import**.

## Safety warnings on prescriptions

They are **fixed rules in code** (not AI), listed at the top of `backend/apps/prescriptions/safety.py`.
They use the medicine's flags (Schedule E1, metals / bhasma, pregnancy, child) and the patient's age, allergies
and medical history (*Pregnant* / *Breastfeeding*). The doctor always decides. To change a rule, ask Claude Code.

## Prescription templates

On the check-up -> **Rx** -> **Save as template**, choose the diagnosis. Next time, **Apply template**
lists the matching ones first (★).

## Pharmacy: "expiring soon" and low stock

- "Expiring soon" = within 90 days. To change it, edit `EXPIRY_WARNING_DAYS` at the top of
  `backend/apps/pharmacy/services.py`.
- Low stock: **Pharmacy -> Stock** -> type a number in **Low-stock level** for each medicine (per branch).
- Switch the whole pharmacy off for a branch: **Settings -> Modules -> Pharmacy and stock**.

## Change the SMS / WhatsApp appointment messages

Open `backend/apps/appointments/messages_catalog.py`. Each message has an English (`en`), Gujarati (`gu`)
and Hindi (`hi`) text. Change the words, but keep `{name}`, `{doctor}`, `{date}`, `{time}`, `{token}`,
`{clinic}` and `{phone}` exactly as they are. The patient's language (from registration) picks the text.

## Change doctor timings or slot length

**Doctor schedules** screen -> edit the doctor's day. "Slot length" (e.g. 15 minutes) decides the time buttons
shown when booking. Already booked appointments are not moved.

## Change the auto-logout time or OTP settings

Open `.env` and change `IDLE_TIMEOUT_MINUTES=15` (or `OTP_VALID_MINUTES`, …).
Then run `stop.bat` and `start.bat`.
