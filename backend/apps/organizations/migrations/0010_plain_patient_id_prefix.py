from django.db import migrations, models


def clear_prefix(apps, schema_editor):
    """Patient IDs are plain numbers now: clear the old "AY" prefix of existing clinics (they can add one again in Settings)."""
    apps.get_model("organizations", "Organization").objects.update(uhid_prefix="")


class Migration(migrations.Migration):
    dependencies = [("organizations", "0009_prescription_design")]

    operations = [
        migrations.AlterField(
            model_name="organization", name="uhid_prefix",
            field=models.CharField(blank=True, default="", help_text="Optional letters before the patient number, e.g. AY -> AY44. Empty -> 44",
                                   max_length=6, verbose_name="Patient ID prefix"),
        ),
        migrations.RunPython(clear_prefix, migrations.RunPython.noop),
    ]
