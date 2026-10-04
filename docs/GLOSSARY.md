# Glossary (tech words in one line)

| Word | Meaning |
|---|---|
| **API** | Fixed web addresses the screens use to ask the backend for data or to save it. |
| **Adapter** | A small "plug" so one service (e.g. SMS) can be swapped for another by changing a setting. |
| **Argon2** | A strong way of scrambling passwords so nobody can read them. |
| **Audit log** | A permanent diary of who did what, when, and from which computer. |
| **Backend** | The part that runs on the server, checks rules and stores data (Django, Python). |
| **Branch scoping** | Showing and allowing only the data of the branch you are working in. |
| **Container** | A sealed box (made by Docker) that runs one part of the app the same way on every PC. |
| **CORS** | A browser safety rule about websites talking to other addresses. We avoid it with a proxy. |
| **Django** | The Python toolkit used to build the backend. |
| **Docker / Docker Compose** | Tools that set up and run all the containers with one command. |
| **DPDP Act** | India's Digital Personal Data Protection law (patient consent, data rights). |
| **.env file** | A text file with settings and secrets (passwords, keys) for your installation. |
| **Feature flag** | An on/off switch for a module, per branch. |
| **Frontend** | The screens you see in the browser (React). |
| **i18n** | Short for "internationalization": showing the app in several languages. |
| **JWT / token** | A digital pass that proves you logged in; it expires after a short time. |
| **Migration** | A file describing a change to the database tables; applied automatically at start. |
| **Ollama** | Free software to run AI models on your own PC (used from Step 10). |
| **OTP / 2FA** | A one-time 6-digit code: a second lock after the password. |
| **Permission** | One small right, such as `billing.create`. |
| **PostgreSQL** | The database program where all data is stored. |
| **Proxy** | A forwarder: the screen at :5173 passes `/api` requests to the backend at :8000. |
| **Rate limit / throttle** | Slowing down too many attempts (e.g. password guessing). |
| **React** | The JavaScript toolkit used to build the screens. |
| **Role** | A named set of permissions, e.g. Doctor or Receptionist. |
| **Seed / demo data** | Fake starting data for testing (`seed_demo`). |
| **Soft delete** | Marking a record as deleted instead of really removing it. |
| **TypeScript** | JavaScript with checks that catch mistakes before the app runs. |
| **UUID** | A long random ID like `3f2a…`, safe to use in web addresses. |
| **Vite** | The tool that serves the React screens during development and reloads on changes. |
| **EMR** | Electronic Medical Record: the doctor's notes of each check-up, stored safely in the software. |
| **Template** (check-up) | A ready form such as Ashtavidha Pariksha; the doctor clicks answers instead of typing. |
| **Autosave** | The check-up saves itself a moment after you stop typing; no Save click needed. If saving fails it tries again. |
| **Undo / Redo** | Go one change back / forward again (Ctrl+Z / Ctrl+Y). |
| **Version** (template) | Each saved change of a template's questions gets a new number; old check-ups keep their version. |
| **Symptom score** | 0 (no problem) to 10 (worst), given per complaint at each visit to see progress. |
| **NAMASTE / ICD** | Official code lists for diagnoses (Ayush / WHO). Optional in this software. |
| **Token** | The queue number (1, 2, 3...) a patient gets on arrival, per doctor per day. |
| **Walk-in** | A patient who comes without an appointment; gets a token straight away. |
| **Click-to-chat** | A WhatsApp link (`wa.me/...`) that opens WhatsApp with the message typed; staff press Send. Free. |
| **Volume** | A storage box Docker keeps on your PC so data survives restarts. |
| **WSL 2** | The Windows feature that lets Docker run Linux programs. |
