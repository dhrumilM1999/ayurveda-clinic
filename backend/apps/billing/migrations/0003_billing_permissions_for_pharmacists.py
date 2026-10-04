"""Pharmacists make the pharmacy bill when they dispense: give built-in Pharmacist roles billing.view / create."""
from django.db import migrations

CODES = ["billing.view", "billing.create"]


def add_permissions(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for role in Role.objects.filter(code="pharmacist", is_system=True, is_deleted=False):
        role.permissions = sorted(set(role.permissions) | set(CODES))
        role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0002_initial"),
        ("accounts", "0002_initial"),
    ]

    operations = [migrations.RunPython(add_permissions, migrations.RunPython.noop)]
