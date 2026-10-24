"""The doctor may take the consultation fee in the room (the front desk still can too)."""
from django.db import migrations


def add_permission(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for role in Role.objects.filter(code="doctor", is_system=True, is_deleted=False):
        role.permissions = sorted(set(role.permissions) | {"billing.create"})
        role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_user_signature")]

    operations = [migrations.RunPython(add_permission, migrations.RunPython.noop)]
