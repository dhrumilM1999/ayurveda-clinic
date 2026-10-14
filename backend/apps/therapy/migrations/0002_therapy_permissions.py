"""Receptionists may book therapy sessions (the front desk usually does)."""
from django.db import migrations


def add_permissions(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for role in Role.objects.filter(code="receptionist", is_system=True, is_deleted=False):
        role.permissions = sorted(set(role.permissions) | {"therapy.view", "therapy.manage"})
        role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("therapy", "0001_initial"),
        ("accounts", "0002_initial"),
    ]

    operations = [migrations.RunPython(add_permissions, migrations.RunPython.noop)]
