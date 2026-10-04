"""Give the new permission "patients.vitals" to the existing built-in Admin, Doctor and Receptionist roles."""
from django.db import migrations

ROLE_CODES = ["admin", "doctor", "receptionist"]
CODE = "patients.vitals"


def add_permission(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for role in Role.objects.filter(code__in=ROLE_CODES, is_system=True, is_deleted=False):
        if CODE not in role.permissions:
            role.permissions = sorted(role.permissions + [CODE])
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0001_initial"),
        ("accounts", "0002_initial"),
    ]

    operations = [migrations.RunPython(add_permission, migrations.RunPython.noop)]
