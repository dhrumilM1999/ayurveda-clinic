# Security for the live server (real patients)

Plain-English guide. The live server has **real patient health data** (DPDP Act 2023), so these rules are strict.
Your own PC (`docker compose up`, `DJANGO_DEBUG=true`) keeps working as before.

## 1. The rule: debug off = "live mode"

When `DJANGO_DEBUG` is **not** `1`/`true`, the software runs in live mode. In live mode it **refuses to start** unless:

- `DJANGO_SECRET_KEY` is a long random value (40+ characters, not the sample key),
- `FIELD_ENCRYPTION_KEY` is set (it scrambles medical notes; keep a safe copy, never change it),
- `DJANGO_ALLOWED_HOSTS` lists the real website name (not `*`),
- doctors/admins can really receive their login code (see section 3).

The error says exactly what to fix. (`SKIP_STARTUP_CHECKS=1` skips this - only for building the image; never on the live server.)

## 2. Settings (names go in the server's settings file)

| Name | What it does |
|---|---|
| `DJANGO_DEBUG` | `1` only on your PC. Leave empty on the server. |
| `DJANGO_SECRET_KEY` | Long random secret. |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | Real address, e.g. `app.vednathayurved.com` and `https://app.vednathayurved.com`. |
| `DJANGO_HTTPS=1` | Behind the HTTPS proxy: secure cookies, HSTS (1 year), proxy header, real visitor IP. |
| `HSTS_INCLUDE_SUBDOMAINS=1` | Optional. Forces HTTPS on ALL sub-sites of vednathayurved.com. Only if every one has a certificate. Default off. |
| `ADMIN_URL` | Address of the Django admin, e.g. `manage-k7x2/`. Change it from `admin/`. It allows 10 login tries a minute. |
| `TWO_FACTOR_METHOD` | `email` (OTP to the person's e-mail) or `sms`. |
| `REQUIRE_2FA` | `0` switches the OTP step off for everyone (weaker). Default `1`. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`/`EMAIL_USE_SSL`, `DEFAULT_FROM_EMAIL` | A real mailbox for e-mail OTP. |
| `BACKUP_DIR` | Folder where backups are saved (`check_production_ready` looks for a fresh file). |
| `CACHE_DIR` | Shared folder for login-limit counters (default `/tmp/ayurveda_cache`). |

## 3. Login codes (OTP) - you must choose

Doctors and admins type a one-time code after their password. A code needs a way to reach them:

- **Option A (recommended): `TWO_FACTOR_METHOD=email`.** The code is e-mailed. Needs a real mailbox (your domain mail,
  Zoho free, Gmail with an app password) in the `EMAIL_*` settings, and an **e-mail address saved on every doctor/admin account**.
- **Option B: a real SMS gateway.** Not built yet (paid, needs DLT registration). Ask when you want it.
- **Option C (temporary): `REQUIRE_2FA=0`.** No code; password only. Use very strong passwords. The checker shows a WARN until you switch it on again.

`SMS_PROVIDER=console` sends nothing. On the live server it never writes phone numbers or codes into the log.
The login code is **never** shown on the screen when debug is off.

## 4. The checker

```
docker compose exec backend python manage.py check_production_ready
```

Prints `[PASS]`, `[WARN]` or `[FAIL]` for: debug, secret key, encryption key, allowed hosts, https, admin address,
OTP-on-screen, 2FA delivery, demo users, demo patients, DEMO_MODE, database password, backups, and Django's own checks.
Any FAIL = not ready (the command ends with an error). It changes nothing.

## 5. What is protected (and proven by tests)

- Every API address needs a login except: health, branding (+logo), login / verify-otp / refresh, the public enquiry form, and the QR "verify" page (`apps/common/tests/test_security_walk.py` tries them all).
- A person with an empty role opens nothing private; staff of one branch cannot use another branch; one clinic never sees another clinic's records.
- The audit log has no edit/delete address, and the database layer refuses edits.
- API answers are never cached by the browser (`Cache-Control: no-store`), carry a strict Content-Security-Policy, no framing, `nosniff`, Referrer and Permissions policies. No other website may call the API from a browser (no CORS) except the enquiry form from `ENQUIRY_ALLOWED_ORIGINS`.
- Logs hide tokens, passwords, OTPs and database values. PDFs can only use pictures embedded in the page (never files or websites).
- Changing a password in Staff logs that person out everywhere. Logout cancels the refresh token. A switched-off account stops working at once.
- `seed_demo`, `seed_demo_journey`, `use_single_doctor` refuse to run on the live server.

## 6. Still your job (outside the software)

- The web server (Caddy) must serve the screens with a strict header (scripts only from the site itself) and must **not** publish `/media` or the backend port.
- Backups: copy them off the server too; test a restore once.
- Remove demo users/patients before real use; give every person their own account.
- Keep the server and Docker images updated.
