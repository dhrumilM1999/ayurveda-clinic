# Audit log: keep 90 days, archive the rest

The audit log (who viewed, changed, printed what) is kept **90 days** in the live database.
Older rows are first saved in a compressed file, checked, and only then removed. The database
itself refuses to delete anything newer than 90 days, and refuses every change at any age.

## Run it (once a day)
```
docker compose exec backend python manage.py purge_audit_log --dry-run   # only count
docker compose exec backend python manage.py purge_audit_log             # archive + remove
```
- Archive files: `backend/audit_archive/` (set `AUDIT_ARCHIVE_DIR` in `.env` to change). Keep this folder in your backups,
  and on the live server copy it off the server (for example to Google Drive) because the audit trail is your proof.
- The purge writes one line in the audit log itself ("Audit log older than 90 days archived", rows, file name).
- `AUDIT_RETENTION_DAYS` in `.env` can be raised (for example 180) but never below 90.

## On the live server
Add a daily job (cron) once the server exists, for example 02:30:
`30 2 * * * cd /srv/ayurveda && docker compose exec -T backend python manage.py purge_audit_log`

## Read an archive file
`python -c "import gzip,json;[print(json.loads(l)) for l in gzip.open('FILE.jsonl.gz','rt',encoding='utf-8')]"`
