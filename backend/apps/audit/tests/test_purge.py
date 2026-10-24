import gzip
import json
import uuid
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.db.utils import InternalError, OperationalError, ProgrammingError
from django.utils import timezone

from apps.audit.models import AuditLog

BLOCKED = (InternalError, OperationalError, ProgrammingError, Exception)


def add_row(days_ago, username="old-user"):
    """Insert straight into the table with an older time (the app itself always stamps 'now')."""
    with connection.cursor() as c:
        c.execute(
            "INSERT INTO audit_auditlog (id, created_at, username, action, object_type, object_id, object_repr, changes, user_agent)"
            " VALUES (%s, %s, %s, 'view', 'patients.patient', '', 'x', '{}', '')",
            [str(uuid.uuid4()), timezone.now() - timedelta(days=days_ago), username],
        )


@pytest.fixture
def archive(settings, tmp_path):
    settings.AUDIT_ARCHIVE_DIR = str(tmp_path)
    return tmp_path


@pytest.mark.django_db
def test_old_rows_are_saved_to_a_file_then_removed_and_new_ones_stay(archive):
    for d in (400, 120, 91):
        add_row(d)
    for d in (89, 10, 0):
        add_row(d, username="recent")
    call_command("purge_audit_log")
    left = AuditLog.objects.filter(username__in=["old-user", "recent"])
    assert sorted(left.values_list("username", flat=True)) == ["recent"] * 3
    files = list(archive.glob("audit_log_*.jsonl.gz"))
    assert len(files) == 1
    rows = [json.loads(line) for line in gzip.open(files[0], "rt", encoding="utf-8")]
    assert len(rows) == 3 and {r["username"] for r in rows} == {"old-user"}
    # the purge itself is written in the log
    note = AuditLog.objects.get(object_type="audit.purge")
    assert note.changes["rows"] == 3 and note.changes["file"] == files[0].name


@pytest.mark.django_db
def test_dry_run_and_nothing_to_do_change_nothing(archive):
    add_row(200)
    call_command("purge_audit_log", "--dry-run")
    assert AuditLog.objects.filter(username="old-user").count() == 1 and not list(archive.iterdir())
    call_command("purge_audit_log")
    call_command("purge_audit_log")  # second run: nothing left, no error
    assert len(list(archive.iterdir())) == 1


@pytest.mark.django_db
def test_less_than_90_days_is_refused():
    with pytest.raises(CommandError):
        call_command("purge_audit_log", "--days", "30")


@pytest.mark.django_db(transaction=True)
def test_the_database_still_refuses_every_other_delete_or_change(archive):
    add_row(200)
    add_row(5, username="recent")
    for sql in (
        "DELETE FROM audit_auditlog WHERE username = 'recent'",                       # new row, no switch
        "UPDATE audit_auditlog SET username = 'x' WHERE username = 'old-user'",       # never changed
        "DELETE FROM audit_auditlog WHERE username = 'old-user'",                     # old row but no purge switch
    ):
        with pytest.raises(BLOCKED), transaction.atomic(), connection.cursor() as c:
            c.execute(sql)
    # even with the purge switch on, a recent row cannot be deleted
    with pytest.raises(BLOCKED), transaction.atomic(), connection.cursor() as c:
        c.execute("SET LOCAL app.audit_purge = 'on'")
        c.execute("DELETE FROM audit_auditlog WHERE username = 'recent'")
    assert AuditLog.objects.filter(username__in=["old-user", "recent"]).count() == 2
