"""
Database-level protection: on PostgreSQL, any UPDATE or DELETE on the audit log is refused,
even if someone bypasses the Django code. (SQLite, used only for quick local tests, is skipped.)
"""
from django.db import migrations

CREATE_SQL = """
CREATE OR REPLACE FUNCTION audit_log_block_changes() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_auditlog is append-only: % is not allowed', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_log_append_only ON audit_auditlog;
CREATE TRIGGER audit_log_append_only
    BEFORE UPDATE OR DELETE ON audit_auditlog
    FOR EACH ROW EXECUTE FUNCTION audit_log_block_changes();
"""

DROP_SQL = """
DROP TRIGGER IF EXISTS audit_log_append_only ON audit_auditlog;
DROP FUNCTION IF EXISTS audit_log_block_changes();
"""


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        # params=None: run the SQL as-is (the "%" in RAISE EXCEPTION is not a Python placeholder)
        schema_editor.execute(CREATE_SQL, params=None)


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DROP_SQL, params=None)


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [migrations.RunPython(forwards, backwards)]
