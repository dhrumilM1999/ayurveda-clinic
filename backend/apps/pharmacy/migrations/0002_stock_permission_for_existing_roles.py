"""Give the new permission "pharmacy.stock" to the existing built-in Admin and Pharmacist roles."""
from django.db import migrations

ROLE_CODES = ["admin", "pharmacist"]
CODE = "pharmacy.stock"


def add_permission(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for role in Role.objects.filter(code__in=ROLE_CODES, is_system=True, is_deleted=False):
        if CODE not in role.permissions:
            role.permissions = sorted(role.permissions + [CODE])
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("pharmacy", "0001_initial"),
        ("accounts", "0002_initial"),
    ]

    operations = [migrations.RunPython(add_permission, migrations.RunPython.noop)]
