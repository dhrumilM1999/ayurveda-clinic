# Troubleshooting (Windows + Docker)

**General tip:** run `logs.bat`, copy the red error text, and paste it into Claude Code with "fix this".

| Problem | What to do |
|---|---|
| `start.bat` says **Docker is not installed** | Install Docker Desktop (see START_HERE_WINDOWS.md) and restart the PC. |
| **Docker Desktop is not running** / waits forever | Open Docker Desktop from the Start menu and wait for **Engine running**. Then run `start.bat` again. |
| Docker says **WSL 2 is not installed / needs update** | Open PowerShell **as administrator**, run `wsl --update`, then restart the PC. |
| **"port is already allocated"** (5432, 8000, 5173 or 8025) | Another program uses that port. Common case: **XAMPP's MySQL/Apache** or a local PostgreSQL. Stop it in the XAMPP Control Panel, or ask Claude Code to change the port. |
| Browser shows **"This site can't be reached"** at localhost:5173 | The first start is slow. Wait 2–3 minutes and press F5. Check `logs.bat` for `VITE ... ready`. |
| Login says **"Wrong username or password"** | Use the sample password `Ayur@2026` (capital A). Usernames are lowercase. |
| Login says **"Request was throttled"** | Too many tries. Wait 1 minute. |
| **OTP not visible** | Look in the yellow box on the login screen, or run `logs.bat` and find `SMS (console`. The OTP is valid for 5 minutes. After 5 wrong tries, log in again to get a new one. |
| Logged out suddenly | Auto-logout after 15 minutes without use (`IDLE_TIMEOUT_MINUTES` in `.env`), or the session ended after 12 hours. |
| **Login suddenly fails** for everyone / screens show "Could not load data" | The backend stopped after a code change. Run `logs.bat`: if you see a red error (for example `ModuleNotFoundError`), run `stop.bat` then `start.bat`. If the error stays, paste it into Claude Code. |
| Booking popup says **"The doctor does not sit on this day"** | That doctor has no timing on that weekday in this branch. Add it on **Doctor schedules**, or pick another date. |
| **WhatsApp button** missing after booking | The patient has not given SMS/WhatsApp consent. Open the patient -> **Consent** tab. |
| My code change doesn't show | Wait 5 seconds and press F5. If needed: `stop.bat` then `start.bat`. |
| Changed `.env` but nothing happened | `.env` is only read at start: run `stop.bat` then `start.bat`. |
| **"relation … does not exist"** / database errors after an update | A database update didn't run. Run `stop.bat` then `start.bat` (it runs `migrate` automatically). |
| Everything is messed up (sample data only) | `reset-demo-data.bat` and type `YES`. **This deletes all data.** |
| Frontend error about `node_modules` | In the VS Code terminal: `docker compose down`, then `docker compose up -d --build --renew-anon-volumes`. |
| Scripts fail with strange `\r` errors | Line endings were changed by Git. `.gitattributes` prevents this. Ask Claude Code to fix the line endings. |
| `http://localhost/ayurveda/` shows "Forbidden" | That's correct. XAMPP is blocked on purpose. Use http://localhost:5173. |
| `start.bat` says a port is in use (5173 or 8000) | Another program uses it. Restart the PC, then run `start.bat` again. |

## Live server (see docs/GO_LIVE.md)

| Problem | Fix |
|---|---|
| `bash deploy/status.sh` shows `!!` lines | Each `!!` line says what is wrong (container not healthy, disk full, backup too old, certificate). Follow the hint printed on that line. |
| Site shows a certificate error | DNS (`nslookup app...`) must show the server IP, and ports 80 + 443 must be open at the provider's firewall. See `docker compose -f docker-compose.prod.yml logs caddy --tail 50`. |
| No login code arrives | On the live server codes go by e-mail (`TWO_FACTOR_METHOD=email` and the `EMAIL_*` settings in `.env`), or are off with `REQUIRE_2FA=0`. See docs/GO_LIVE.md step 8. |
| `docker: permission denied` on the server | Log out and in again as `clinic` (the Docker group is applied at login). |
| Update did not become healthy | `bash deploy/update.sh --rollback`, then show `logs backend --tail 100` to Claude Code. |
| Backup failed | See `backups/backup.log`. Common reasons: disk full, database container stopped. |
| `ADMIN_URL` page gives "Not found" | Use the secret address from `.env` (`ADMIN_URL=`): `https://your-address/<ADMIN_URL>/`. |
