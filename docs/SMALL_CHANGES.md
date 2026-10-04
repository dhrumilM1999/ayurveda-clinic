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
