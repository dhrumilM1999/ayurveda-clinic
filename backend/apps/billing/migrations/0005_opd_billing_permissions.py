"""OPD billing: doctors and receptionists may add charges to OPD bills; admins may edit fees and services."""
from django.db import migrations

ADD = {
    "doctor": ["billing.charge"],
    "receptionist": ["billing.charge"],
    "admin": ["billing.charge", "billing.manage"],
}


def add_permissions(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for code, perms in ADD.items():
        for role in Role.objects.filter(code=code, is_system=True, is_deleted=False):
            role.permissions = sorted(set(role.permissions) | set(perms))
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0004_opd_billing"),
        ("accounts", "0002_initial"),
    ]

    operations = [migrations.RunPython(add_permissions, migrations.RunPython.noop)]
