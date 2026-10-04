# Troubleshooting (Windows + Docker)

**General tip:** run `logs.bat`, copy the red error text, and paste it into Claude Code with "fix this".

| Problem | What to do |
|---|---|
| `start.bat` says **Docker is not installed** | Install Docker Desktop (see START_HERE_WINDOWS.md) and restart the PC. |
| **Docker Desktop is not running** / waits forever | Open Docker Desktop from the Start menu and wait for **Engine running**. Then run `start.bat` again. |
| Docker says **WSL 2 is not installed / needs update** | Open PowerShell **as administrator**, run `wsl --update`, then restart the PC. |
| **"port is already allocated"** (5432, 8000, 5173 or 8025) | Another program uses that port. Common case: **XAMPP's MySQL/Apache** or a local PostgreSQL. Stop it in the XAMPP Control Panel, or ask Claude Code to change the port. |
| Browser shows **"This site can't be reached"** at localhost:5173 | The first start is slow. Wait 2–3 minutes and press F5. Check `logs.bat` for `VITE ... ready`. |
| Login says **"Wrong username or password"** | Use the demo password `Ayur@Demo2026` (capital A and D). Usernames are lowercase. |
| Login says **"Request was throttled"** | Too many tries. Wait 1 minute. |
| **OTP not visible** | Look in the yellow box on the login screen, or run `logs.bat` and find `SMS (console`. The OTP is valid for 5 minutes. After 5 wrong tries, log in again to get a new one. |
| Logged out suddenly | Auto-logout after 15 minutes without use (`IDLE_TIMEOUT_MINUTES` in `.env`), or the session ended after 12 hours. |
| My code change doesn't show | Wait 5 seconds and press F5. If needed: `stop.bat` then `start.bat`. |
| Changed `.env` but nothing happened | `.env` is only read at start: run `stop.bat` then `start.bat`. |
| **"relation … does not exist"** / database errors after an update | A database update didn't run. Run `stop.bat` then `start.bat` (it runs `migrate` automatically). |
| Everything is messed up (demo only) | `reset-demo-data.bat` and type `YES`. **This deletes all data.** |
| Frontend error about `node_modules` | In the VS Code terminal: `docker compose down`, then `docker compose up -d --build --renew-anon-volumes`. |
| Scripts fail with strange `\r` errors | Line endings were changed by Git. `.gitattributes` prevents this. Ask Claude Code to fix the line endings. |
| `http://localhost/ayurveda/` shows "Forbidden" | That's correct. XAMPP is blocked on purpose. Use http://localhost:5173. |
| `start.bat` says a port is in use (5173 or 8000) | The no-Docker version may still be running. Close the black "Clinic BACKEND" and "Clinic SCREENS" windows, then run `start.bat` again. Never run both versions at the same time. |
| Patients I added in the no-Docker version are missing | The two versions use different databases (a file vs PostgreSQL). Both hold only demo data, so this is expected. |
