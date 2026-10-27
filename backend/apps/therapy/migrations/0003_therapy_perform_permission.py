"""The therapist list on a booking now means people whose role has "therapy.perform" (not every person who may book)."""
from django.db import migrations

ADD = {
    "therapist": ["therapy.perform"],
    "admin": ["therapy.perform"],
}


def add_permissions(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for code, perms in ADD.items():
        for role in Role.objects.filter(code=code, is_system=True, is_deleted=False):
            role.permissions = sorted(set(role.permissions) | set(perms))
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("therapy", "0002_therapy_permissions"),
        ("accounts", "0002_initial"),
    ]

    operations = [migrations.RunPython(add_permissions, migrations.RunPython.noop)]
