"""
Keeps the audit log for 90 days. Older rows are first saved in a compressed archive file, checked, and only then
removed from the database. Run it every day (see docs/AUDIT_RETENTION.md):

    python manage.py purge_audit_log              # archive, then delete rows older than 90 days
    python manage.py purge_audit_log --dry-run    # only say how many rows it would archive

The database itself refuses to delete anything newer than 90 days (migration audit.0005), so --days cannot go below 90.
"""
import gzip
import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import log_action

MIN_DAYS = 90
FIELDS = ["id", "created_at", "organization_id", "branch_id", "user_id", "username", "action", "object_type",
          "object_id", "object_repr", "changes", "ip_address", "user_agent"]


class Command(BaseCommand):
    help = "Save audit log rows older than 90 days to an archive file, then remove them from the database."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=getattr(settings, "AUDIT_RETENTION_DAYS", MIN_DAYS))
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        days = options["days"]
        if days < MIN_DAYS:
            raise CommandError(f"The audit log must be kept for at least {MIN_DAYS} days.")
        cutoff = timezone.now() - timedelta(days=days)
        old = AuditLog.objects.filter(created_at__lt=cutoff).order_by("created_at")
        total = old.count()
        if total == 0:
            self.stdout.write(f"Nothing to archive: no audit rows older than {days} days.")
            return
        first, last = old.first().created_at, old.last().created_at
        if options["dry_run"]:
            self.stdout.write(f"Would archive and delete {total} rows ({first:%d-%m-%Y} to {last:%d-%m-%Y}).")
            return

        folder = Path(getattr(settings, "AUDIT_ARCHIVE_DIR", settings.BASE_DIR / "audit_archive"))
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"audit_log_{first:%Y%m%d}_to_{last:%Y%m%d}_saved_{timezone.now():%Y%m%d_%H%M%S}.jsonl.gz"
        with gzip.open(path, "wt", encoding="utf-8") as out:
            for row in old.values(*FIELDS).iterator(chunk_size=2000):
                out.write(json.dumps(row, cls=DjangoJSONEncoder, ensure_ascii=False) + "\n")
        with gzip.open(path, "rt", encoding="utf-8") as check:  # read it back: never delete on a hope
            saved = sum(1 for _ in check)
        if saved != total:
            path.unlink(missing_ok=True)
            raise CommandError(f"The archive file has {saved} rows but {total} were expected. Nothing was deleted.")

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.audit_purge = 'on'")
                cursor.execute("DELETE FROM audit_auditlog WHERE created_at < %s", [cutoff])
                deleted = cursor.rowcount
            if deleted != total:
                raise CommandError(f"{deleted} rows would be deleted but {total} were archived. Nothing was deleted.")
        log_action(None, "delete", object_type="audit.purge", object_repr="Audit log older than %d days archived" % days,
                   username="system", changes={"rows": deleted, "from": first.isoformat(), "to": last.isoformat(), "file": path.name})
        self.stdout.write(self.style.SUCCESS(f"Archived {deleted} rows to {path} and removed them from the database."))
