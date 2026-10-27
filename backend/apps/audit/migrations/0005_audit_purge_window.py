"""
The audit log stays append-only, with ONE exception that the database itself enforces: the purge command
(manage.py purge_audit_log) may delete rows that are OLDER THAN 90 DAYS, after saving them to an archive file.
Nothing newer can be deleted, and nothing can ever be changed. The 90 days cannot be shortened from the app.
"""
from django.db import migrations

NEW_SQL = """
CREATE OR REPLACE FUNCTION audit_log_block_changes() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE'
       AND current_setting('app.audit_purge', true) = 'on'
       AND OLD.created_at < now() - interval '90 days' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'audit_auditlog is append-only: % is not allowed', TG_OP;
END;
$$ LANGUAGE plpgsql;
"""

OLD_SQL = """
CREATE OR REPLACE FUNCTION audit_log_block_changes() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_auditlog is append-only: % is not allowed', TG_OP;
END;
$$ LANGUAGE plpgsql;
"""


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(NEW_SQL, params=None)


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(OLD_SQL, params=None)


class Migration(migrations.Migration):
    dependencies = [("audit", "0004_error_log_extra")]

    operations = [migrations.RunPython(forwards, backwards)]
