# Go-live tick list (one page)

Full explanations: `docs/GO_LIVE.md`.

## Before launch day
- [ ] Server rented (Ubuntu 24.04, 4 GB RAM recommended, India region). IP written down.
- [ ] GoDaddy: **A record `app` → server IP** added (existing website records untouched).
- [ ] `nslookup app.vednathayurved.com` shows the server IP.
- [ ] A safe place chosen for the copy of `.env` (password manager / encrypted USB).
- [ ] A place chosen for off-server backups (rclone storage or another computer).
- [ ] Staff list ready: names, mobile numbers, roles (owner, doctors, reception, pharmacy, therapy).

## Launch day
- [ ] Connected by SSH; `server-setup.sh` finished; login as `clinic` works.
- [ ] `make-env.sh` done; **`.env` copied to the safe place** (especially `FIELD_ENCRYPTION_KEY`).
- [ ] `docker compose -f docker-compose.prod.yml up -d --build` finished; `bash deploy/status.sh` says ALL GOOD (except backups).
- [ ] https://app… opens with a padlock.
- [ ] `create_clinic` done; owner login works.
- [ ] `check_production_ready` shows no FAIL. E-mail login codes switched on (or `REQUIRE_2FA=0` noted as temporary).
- [ ] Password changed; clinic name, logo, address, GSTIN, timings, UPI ID entered.
- [ ] Doctors, staff, schedules, fees, services and real medicines entered.
- [ ] Test patient: register → consult → prescription → bill → **PDF print with Gujarati** → looks right.
- [ ] `bash deploy/backup.sh` works; practice restore (`--test`) says OK.
- [ ] Nightly timer enabled (`systemctl list-timers ayurveda-backup.timer`).
- [ ] Off-server backup copy set in `.env` and a file really arrived there.
- [ ] Secret admin address written down (shown by make-env; also `ADMIN_URL` in `.env`).
- [ ] Phone/tablet at the front desk opens the site and logs in.

## First week
- [ ] Every morning: `bash deploy/status.sh` (takes 10 seconds) says ALL GOOD.
- [ ] Day 2: look at `backups/backup.log` — last night's backup is there.
- [ ] Ask staff what is confusing; write it down for Claude Code.
- [ ] After day 7: do one real restore test on a spare computer or `--test` again.
- [ ] Check disk space and memory in `status.sh`; upgrade the server if memory is always full.
- [ ] Put a **monthly** reminder: status, backup restore test, `bash deploy/update.sh` for new versions, check the DPDP screens (consent, patient requests).
