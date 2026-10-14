"""Online enquiries: admins and receptionists may see and follow up enquiries."""
from django.db import migrations

ADD = {
    "receptionist": ["enquiries.view", "enquiries.manage"],
    "admin": ["enquiries.view", "enquiries.manage"],
}


def add_permissions(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for code, perms in ADD.items():
        for role in Role.objects.filter(code=code, is_system=True, is_deleted=False):
            role.permissions = sorted(set(role.permissions) | set(perms))
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("enquiries", "0001_initial"),
        ("accounts", "0002_initial"),
    ]

    operations = [migrations.RunPython(add_permissions, migrations.RunPython.noop)]
