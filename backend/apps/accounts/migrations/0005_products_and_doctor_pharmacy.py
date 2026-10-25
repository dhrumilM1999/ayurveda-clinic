"""The doctor runs the pharmacy (pharmacy and medicine-list permissions); doctor, receptionist and pharmacist can sell clinic products."""
from django.db import migrations

ADD = {
    "doctor": {"medicines.manage", "pharmacy.view", "pharmacy.dispense", "pharmacy.stock", "products.view", "products.sell"},
    "receptionist": {"products.view", "products.sell"},
    "pharmacist": {"products.view", "products.sell"},
}


def add_permissions(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for code, extra in ADD.items():
        for role in Role.objects.filter(code=code, is_system=True, is_deleted=False):
            role.permissions = sorted(set(role.permissions) | extra)
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_doctor_takes_payments")]

    operations = [migrations.RunPython(add_permissions, migrations.RunPython.noop)]
