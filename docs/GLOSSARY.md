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
| **Sample data** | Made-up starting data for practice (`seed_demo`, `reset-demo-data.bat`). |
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
| **Classical medicine** | A medicine with an official name in the Ayurvedic Formulary / Pharmacopoeia of India (AFI / API). |
| **Patent & Proprietary** | A company's brand of Ayurvedic medicine. |
| **Anupana** | What the medicine is taken with (warm water, milk, honey, ghee...). |
| **Schedule E1** | Official list of poisonous ingredients; such medicines are given only on prescription. |
| **HSN code** | Tax code of a product, printed on GST bills (medicines usually 3004). |
| **M-N-N (1-0-1)** | How many doses in the Morning, at Noon and at Night. |
| **Batch** | One lot of a medicine from the maker, with its own number and expiry date. |
| **FEFO** | First Expiry, First Out: the batch that expires first is given first. |
| **Dispense** | Give the prescribed medicines to the patient (stock goes down). |
| **MRP** | Maximum Retail Price printed on the pack; the selling price can be lower, never higher. |
| **Free quantity** | Extra packs the supplier gives free with a purchase; they add to stock at no cost. |
| **Opening stock** | The stock you already have on the day you start using the software. |
| **Stock ledger** | The list of every stock movement (+ and -) with the balance after each one. |
| **Stock check** | Counting what is really on the shelves and correcting the software to match. |
| **Credit note** | A document that cancels all or part of a bill (for a return or refund). The bill itself stays. |
| **Financial year (FY)** | April to March. Bill numbers start again from 1 each April (e.g. 2026-27). |
| **Taxable value** | The price without GST. GST is worked out on this amount. |
| **CGST / SGST** | The two halves of GST inside one state (central and state). |
| **Loose sale** | Selling part of a pack, such as 10 tablets from a strip of 60. |
| **Token** | The queue number (1, 2, 3...) a patient gets on arrival, per doctor per day. |
| **Walk-in** | A patient who comes without an appointment; gets a token straight away. |
| **Click-to-chat** | A WhatsApp link (`wa.me/...`) that opens WhatsApp with the message typed; staff press Send. Free. |
| **Volume** | A storage box Docker keeps on your PC so data survives restarts. |
| **WSL 2** | The Windows feature that lets Docker run Linux programs. |
