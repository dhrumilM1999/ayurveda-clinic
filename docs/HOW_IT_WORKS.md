# How it works (in plain words)

Think of the software as a **clinic building**:

| Part | Analogy | What it really is |
|---|---|---|
| **Frontend** | The reception desk and forms the staff see | React app in `frontend/`. It runs in the browser at http://localhost:5173 |
| **Backend** | The back office that checks rules and keeps files | Django in `backend/`. It answers requests at `/api/v1/...` |
| **Database** | The locked record room | PostgreSQL. All data lives here, in a Docker "volume" (a storage box) |
| **Docker** | A building contractor who sets up every room the same way on any PC | `docker-compose.yml` describes the 4 "rooms" (containers): db, backend, frontend, mailpit |
| **API** | The window between reception and back office | Fixed addresses like `/api/v1/rooms/` that the frontend calls |

## Where is my data?

Your data is **not** in the project folder. Docker keeps it in "volumes" (storage boxes) inside
Docker Desktop's own disk on your PC:

| What | Docker volume name | Inside the container |
|---|---|---|
| The database (patients, appointments, staff, audit log...) | `ayurveda_pgdata` | `/var/lib/postgresql/data` |
| Patient photos and documents (private, only through the app) | `ayurveda_private_media` | `/app/private_media` |
| Other uploaded files (logos) | `ayurveda_media` | `/app/media` |

- See them: open **Docker Desktop -> Volumes**.
- `stop.bat`, restarting the PC, or updating the code **keeps** the data.
- Only `reset-demo-data.bat` (after typing `YES`) or deleting the volume in Docker Desktop removes it.
- To look inside the database yourself, use the technical admin site: http://localhost:8000/admin/ (user `admin`).
- The no-Docker version (`start-without-docker.bat`) uses a different, separate file: `backend/db.sqlite3`.
- Proper daily backups come in a later step (Step 11). Until then the data is demo data only.

## What happens when you click "Save" on a room

1. The **frontend** sends the data to `/api/v1/rooms/`, together with
   - your **login token** (a pass that proves who you are, valid for 15 minutes), and
   - the **current branch** (header `X-Branch-ID`).
2. The **backend** checks:
   - Is the token valid?
   - Are you allowed in this branch?
   - Does your role in this branch have the permission `rooms.manage`?
3. If all is OK, it saves the room in the **database** and writes an **audit log** entry:
   who, what, when, from which computer.
4. The frontend shows "Saved".

## Organization, branches, people

```
Organization (clinic group)          ← patients, medicine list, roles live here (shared)
 ├── Branch: Ahmedabad               ← appointments, bills, stock, rooms live here
 │     └── Rooms
 └── Branch: Vadodara
       └── Rooms
Staff user ── has one Role per Branch (e.g. Doctor in Ahmedabad, Doctor in Vadodara)
```

- A **permission** is one small right, e.g. `billing.create`.
- A **role** (Doctor, Receptionist…) is a list of permissions. You can edit roles on the **Roles** screen.
- An **organization admin** (like `admin`) can do everything in all branches.

## Safety features already in place

- Passwords are stored scrambled (Argon2). Nobody can read them, not even the admin.
- Login is slowed down after 5 wrong tries in a minute (stops password guessing).
- Doctors and admins need an OTP at login (2-step login).
- Auto-logout after 15 minutes without using the screen.
- Nothing important is really deleted. It is only marked "deleted" (soft delete).
- The audit log cannot be changed or deleted, not even directly in the database.

## Free services now, paid later

External services (SMS, WhatsApp, AI, payments…) are behind **adapters**: small plug sockets.
Today SMS uses the "console" plug: the message is only printed in `logs.bat`.
Later, a paid SMS company can be plugged in by changing `SMS_PROVIDER` in `.env` (plus an API key).
