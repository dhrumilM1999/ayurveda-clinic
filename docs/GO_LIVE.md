# Going live — put the clinic software on the internet

This guide takes you from "only on my PC" to **https://app.vednathayurved.com** (or any address you choose), step by step.
You do not need to be a programmer. Copy each command exactly, press Enter, and wait until it finishes.
A one-page tick list is in `docs/GO_LIVE_CHECKLIST.md`.

**How it will look when finished**

```
Browser  --https-->  [ your server (one small Linux computer, rented) ]
                       Caddy (front door + free HTTPS certificate)
                         |-- shows the screens (React)
                         `-- /api  -->  Backend (Django)  -->  Database (PostgreSQL)
                                                   `--> private folder with patient files
```

Everything runs in Docker on that one server, exactly like on your PC, but with `docker-compose.prod.yml` instead of `docker-compose.yml`.
Your PC setup (`start.bat`) is **not changed** by any of this.

Time needed: about 1.5 hours the first time (most of it waiting).

---

## 1. Rent the server (VPS)

A VPS is a small computer in a data centre that you rent by the month.
Any of these work: **AWS Lightsail (Mumbai)**, **DigitalOcean (Bangalore)**, **Vultr (Mumbai/Delhi)**, **Hostinger VPS**.
Choose a place in **India (Mumbai / Bangalore)** if you can: faster for your patients, and the data stays in India.

When you create it, choose:

| Setting | Choose |
|---|---|
| Operating system | **Ubuntu 24.04 LTS** (plain Ubuntu, no "apps" or panels) |
| Size | **2 vCPU and 4 GB RAM** recommended. 2 GB RAM is the minimum (it works, but is tight). |
| Disk | 40 GB or more |
| Login | If it asks for an SSH key, you may upload one (see step 3), or choose a password. Write the password down. |
| Backups option of the provider | Switch it on if it is cheap (it is a second safety net, not a replacement for step 9) |

When it is ready the provider shows the **server's IP address** (four numbers like `203.0.113.25`). Write it down.

> Do NOT install a control panel (cPanel, Plesk) and do NOT use XAMPP on the server.

## 2. GoDaddy: point `app.vednathayurved.com` to the server

1. Log in to GoDaddy → **My Products** → next to `vednathayurved.com` click **DNS** (or "Manage DNS").
2. Click **Add New Record** and fill:
   - **Type:** `A`
   - **Name:** `app`
   - **Value:** the server IP from step 1
   - **TTL:** the smallest offered (600 seconds / 10 minutes, or "1/2 hour")
3. Click **Save**.

> **Do not change or delete any other record.** Your existing website records (`@`, `www`, mail/`MX`, etc.) must stay exactly as they are. You are only *adding* one new line for `app`.

**Wait and check.** It usually works in 5–30 minutes (sometimes up to a few hours). On your Windows PC open PowerShell and run:

```powershell
nslookup app.vednathayurved.com
```

When the answer shows **your server's IP address**, DNS is ready. If it says "Non-existent domain", wait 10 more minutes and try again.
**Do not continue to step 6 before this works**, otherwise the HTTPS certificate cannot be issued.

## 3. Connect to the server from Windows

Open **PowerShell** (Start menu → type PowerShell) and run (replace the IP):

```powershell
ssh root@203.0.113.25
```

- First time it asks "Are you sure you want to continue connecting?" → type `yes`.
- Enter the password the provider gave you (typing is invisible — that is normal).
- Some providers log in as `ubuntu` instead of `root`: then use `ssh ubuntu@203.0.113.25` and put `sudo` in front of the commands in step 4.

Prefer a program with windows? **PuTTY** works too: Host Name = the IP, Port 22, click Open.

You will see a prompt like `root@server:~#`. Everything you type now runs on the server.

## 4. Prepare the server (once)

First get the code. The code lives at `https://github.com/dhrumilM1999/ayurveda-clinic.git`.

```bash
apt-get update && apt-get install -y git
```

```bash
git clone https://github.com/dhrumilM1999/ayurveda-clinic.git /root/ayurveda-clinic
```

**If GitHub asks for a username and password, the repository is private.** Use a *personal access token* (it is the "password"):
GitHub website → your photo → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → *Generate new token* →
choose only the repository `ayurveda-clinic`, permission **Contents: Read-only**, set an expiry of 1 year → copy the token (shown once).
Then clone with the token as the password. When Git asks, username = your GitHub name, password = the token.
(Alternative for experts: a *deploy key* — ask Claude Code to guide you.)

Now run the one-time setup. It updates the server, makes a normal user called `clinic`, switches on the firewall (only ports 22, 80, 443), fail2ban (blocks password guessers), automatic security updates, installs Docker, and adds a swap file:

```bash
bash /root/ayurveda-clinic/deploy/server-setup.sh
```

It asks you to choose a password for the new user `clinic`. **Write it down.**
At the end it prints some notes about SSH safety. **Read them.** It never changes how you log in (so it cannot lock you out).

Now move the code to the new user and switch to it:

```bash
mv /root/ayurveda-clinic /home/clinic/ayurveda-clinic && chown -R clinic:clinic /home/clinic/ayurveda-clinic
```

```bash
su - clinic
```

(From now on you are `clinic`. Next time, connect directly with `ssh clinic@<server-ip>`.)
Check that Docker works for this user:

```bash
docker ps
```

An empty table is correct. If you see "permission denied", type `exit`, log in again as `clinic` and retry.

## 5. Create the settings file (`.env`)

```bash
cd ~/ayurveda-clinic
```

```bash
bash deploy/make-env.sh app.vednathayurved.com you@example.com
```

(Use your own email: Let's Encrypt only uses it to warn you if the certificate cannot renew.)
This writes a file `.env` with a fresh secret key, a strong database password, a secret address for the admin page, and an encryption key. **It never shows the secrets on screen.** It prints the secret admin address — write it down.

> **VERY IMPORTANT:** copy the `.env` file to a safe place outside the server (password manager, or an encrypted USB).
> To see it: `nano .env` (Ctrl+X to leave). Never paste it in chat or email.
> If you lose `FIELD_ENCRYPTION_KEY`, the encrypted medical notes can never be read again, and backups do **not** contain it.

Optional: if you want to allow the enquiry form on your existing website, put your website addresses in `ENQUIRY_ALLOWED_ORIGINS=` inside `.env` (`nano .env`).

## 6. First start

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The first time this downloads and builds everything: **5–15 minutes**. When it ends, check:

```bash
bash deploy/status.sh
```

You want to see `healthy` for `db`, `backend` and `caddy`. The HTTPS certificate is requested automatically in the first minute. Then open **https://app.vednathayurved.com** in your browser: you should see the login page with a padlock.

If not, see section 11.

## 7. Create your clinic (first time only)

This makes your clinic, first branch and **your owner login**. There is **no demo data**: no sample patients, users or bills.

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py create_clinic
```

It asks, one by one: clinic name, branch name, short code (letters, used in invoice numbers), city, state, GSTIN (press Enter to skip), your login name, your full name, your mobile number.
Then it asks you to type a password twice (hidden). Or add `--generate-password` to the command and it makes a strong one and shows it **once** — write it down.
Names are your own data; you can change them later on the Settings screens.
Running it again is harmless: if a clinic exists it changes nothing.

## 8. Log in and the first-day checklist

Open https://app.vednathayurved.com and log in with the login name and password from step 7.

**About the login code (OTP).** Owners and doctors normally type a 6-digit code after the password. SMS is paid, so it is not available yet. You have two free choices (set in `.env`, `nano .env`, then `bash deploy/update.sh`):

- **E-mail codes (recommended):** set `REQUIRE_2FA=1`, `TWO_FACTOR_METHOD=email` and fill the `EMAIL_*` lines with a real mailbox (your domain mail, Zoho free, or Gmail with an "app password"). Every doctor/admin account needs an e-mail address saved.
- **Temporary, to start today:** `REQUIRE_2FA=0` (this is how `.env` is created). No code, password only, so use **very strong passwords** and switch e-mail codes on within the first week.

After the first start run the safety checker and fix every `FAIL`:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py check_production_ready
```

(It shows a `WARN` while 2FA is off, and a `FAIL` if no backup has been made yet: run `bash deploy/backup.sh` first.)

First-day tick list:

- [ ] Change your password (top right menu).
- [ ] **Settings → Clinic:** clinic name, logo, address, phone, GSTIN.
- [ ] **Settings → Branch details:** printed timings, prescription design, UPI ID for payments.
- [ ] Add the doctor(s): **Users** → new user, role Doctor, tick "is doctor", registration number, signature image.
- [ ] Doctor timings (**Doctor schedules**) and consultation fees / services & charges (**Billing settings**).
- [ ] Add your staff (receptionist, pharmacist, therapist) with the right roles.
- [ ] Add your real medicines (**Medicines → Import** from Excel). The 23 sample medicines are only examples — a pharmacist must verify any list.
- [ ] Do a full test with **one test patient**: register, book, consult, prescribe, bill, **print the bill and prescription as PDF** (check Gujarati text). Then ask Claude Code how to mark/remove the test patient, or keep him as "TEST".
- [ ] Set up **automatic backups** (step 9) and **test a restore** (a practice run).
- [ ] Put a monthly reminder in your calendar: "check backups + status + updates" (`docs/GO_LIVE_CHECKLIST.md`).

## 9. Backups (do this on day 1)

A backup saves the database and the private patient files to the folder `~/ayurveda-clinic/backups/` (keeps the last 14 daily + 8 weekly).
The `.env` file is NOT inside it — keep your own copy (step 5).

**Why this matters:** the DPDP Act 2023 expects you to protect patients' data and to recover it if something goes wrong. A backup only on the same server is lost if the server is lost, so you also copy it elsewhere.

Try one by hand:

```bash
bash deploy/backup.sh
```

**Practice restore** (safe: it loads the backup into a temporary database and deletes it again; your live data is not touched). Replace the folder name with the one printed above (look with `ls backups/daily`):

```bash
bash deploy/restore.sh backups/daily/2026-10-17_0230 --test
```

It should end with `PRACTICE RUN OK`.

### Automatic nightly backup (systemd timer)

```bash
sudo cp deploy/ayurveda-backup.service deploy/ayurveda-backup.timer /etc/systemd/system/
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now ayurveda-backup.timer
```

Check it is scheduled (it should list the next run, about 02:30):

```bash
systemctl list-timers ayurveda-backup.timer
```

(The files assume the user `clinic` and the folder `/home/clinic/ayurveda-clinic`. If you used other names, edit the two `.service` lines `User=` and the paths.)
The log of every backup is `backups/backup.log`.

### Copy the backups off the server (free)

Choose ONE way. The backup script does it automatically after each backup once it is set in `.env`.

**A) rclone to a storage you choose** (Google Drive, OneDrive, Backblaze B2 free tier, another server…):

```bash
rclone config
```

Follow the questions to create a "remote" (for example named `mydrive`). For patient data, make it an *encrypted* remote too (rclone type `crypt`) so the cloud company cannot read it. Then:

```bash
nano .env
```

and set `OFFSITE_RCLONE_REMOTE=mydrive:ayurveda-backups` (or your crypt remote). Run `bash deploy/backup.sh` and check that files appear there.

**B) scp to another computer you control** (e.g. an office PC with an SSH server, or a second cheap server):
create an SSH key on the server (`ssh-keygen -t ed25519`), add the public key to the other computer, then set `OFFSITE_SCP_TARGET=user@other-computer:/folder` in `.env`.

Whatever you choose: **once a month, really restore a backup on a spare machine or use `--test`** — an untested backup is only a hope.

### Real restore (new or broken server)

Only if you must. On a new server: repeat steps 4–5 but **copy your old `.env`** instead of making a new one, copy the backup folder to `~/ayurveda-clinic/backups/daily/`, run `docker compose -f docker-compose.prod.yml build`, then:

```bash
bash deploy/restore.sh backups/daily/2026-10-17_0230
```

Type `RESTORE` when asked. It replaces the database and files with the backup and starts the app.

## 10. Updating the software later

When Claude Code has new features ready (they are pushed to GitHub), on the server:

```bash
cd ~/ayurveda-clinic && bash deploy/update.sh
```

It makes a backup first, downloads the new code, rebuilds, applies database changes, restarts and waits until the app is healthy. Takes a few minutes; do it at a quiet time (e.g. after clinic hours) — users may be logged out for about a minute.

**If the new version misbehaves**, go back to the previous code:

```bash
bash deploy/update.sh --rollback
```

If the data itself looks wrong after an update, restore the backup that `update.sh` made just before (newest folder in `backups/daily`, see section 9).

## 11. If something breaks

Always start with the status page:

```bash
bash deploy/status.sh
```

| Problem | What to do |
|---|---|
| Site does not open at all | `bash deploy/status.sh`. If a container is not healthy, read its log (below). Check that the DNS still points to the server (`nslookup`). |
| Browser says "not secure" / certificate error | DNS not ready yet, or ports 80/443 blocked at the provider's firewall (open them in the provider's website panel, *Networking/Firewall*). Look: `docker compose -f docker-compose.prod.yml logs caddy --tail 50` |
| "Could not load data" for everyone | Backend problem. `docker compose -f docker-compose.prod.yml logs backend --tail 100` and show the red lines to Claude Code. |
| Cannot log in, no code arrives | Check the `EMAIL_*` settings and that your account has an e-mail address; or use `REQUIRE_2FA=0` temporarily (see step 8). |
| Server very slow | `bash deploy/status.sh` (memory, disk). A 2 GB server is tight: upgrade to 4 GB at your provider. |
| Disk full | `bash deploy/status.sh`; reduce `KEEP_DAILY` in `deploy/backup.sh`, delete old files in `backups/`, run `docker system prune -f`. |
| After an update things are wrong | `bash deploy/update.sh --rollback` |
| Data lost or damaged | Restore the newest backup (section 9). |
| Everything restarted after a server reboot? | Normal: all containers start by themselves (`restart: unless-stopped`). |

Useful commands:

```bash
docker compose -f docker-compose.prod.yml ps
```

```bash
docker compose -f docker-compose.prod.yml logs backend --tail 100
```

```bash
docker compose -f docker-compose.prod.yml restart backend
```

## 12. Free or paid?

| Item | Cost |
|---|---|
| The server (VPS) | **Paid**, monthly (roughly ₹500–1,500 depending on provider/size) |
| Domain `vednathayurved.com` | **Paid**, yearly (already bought at GoDaddy) |
| `app.…` sub-address (DNS record) | Free |
| HTTPS certificate (Let's Encrypt via Caddy) | Free, renews by itself |
| The clinic software, Docker, Caddy, PostgreSQL, fail2ban, firewall | Free |
| Backups on the server | Free (uses the server's disk) |
| Off-server backup with rclone/scp | Free tool; storage is free if you use your own PC or a free tier. Large cloud storage may cost a little |
| Login codes | By e-mail through a mailbox you already have (free), or off for now. Real SMS = paid DLT service, only if you ask |
| WhatsApp | Free "click to chat" links (staff press Send) |
| AI translate button | Not available on the server (needs Ollama on a PC) — shows "AI is offline" |
| UPI payments | Free QR code; staff mark bills paid |

Nothing here needs a paid account except the server and the domain.
