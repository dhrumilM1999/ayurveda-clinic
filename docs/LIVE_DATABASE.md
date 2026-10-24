# Which database is the app using?

Since 2026-10-25 the app on your PC saves to the **Supabase database** (the "live" copy), not to the database on your PC.
Everything you enter (patients, bills, check-ups) now goes to Supabase and stays there.

## How to see which one is used
Open `.env` and look at `POSTGRES_HOST`:
- `aws-0-ap-southeast-1.pooler.supabase.com` = Supabase (live)
- `db` = the database on this PC

## Go back to the PC database
Copy the lines from `.env.local-db` over the `POSTGRES_` lines in `.env`, remove `POSTGRES_SSLMODE=require`, then run `docker compose up -d backend`.
Data entered while on Supabase stays in Supabase; the PC database has the old copy from 2026-10-24.

## Careful
- `reset-demo-data.bat` now deletes the **Supabase** data too (it asks you to type YES). Do not run it once real data is in.
- The app is a little slower than before: Supabase is in Singapore and your PC calls it over the internet. On the real server in Mumbai this goes away.
- Automatic tests must never run on the live database. Use `run-tests.bat` (it uses the PC database; the test code refuses anything else).
- Real patient data: wait for the Mumbai setup first (see `docs/GO_LIVE.md`). Singapore is for demo data only.
