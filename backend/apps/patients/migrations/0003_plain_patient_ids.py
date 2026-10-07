from django.db import migrations


def renumber(apps, schema_editor):
    """Give every existing patient a plain number (1, 2, 3 ... in the order they were registered) and set the counter."""
    Organization = apps.get_model("organizations", "Organization")
    Patient = apps.get_model("patients", "Patient")
    Sequence = apps.get_model("patients", "UhidSequence")
    for org in Organization.objects.all():
        patients = list(Patient.objects.filter(organization=org).order_by("created_at", "id"))
        for number, patient in enumerate(patients, start=1):
            Patient.objects.filter(pk=patient.pk).update(uhid=str(number))
        seq, _ = Sequence.objects.get_or_create(organization=org, year=0)
        seq.last_number = len(patients)
        seq.save()


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0002_vitals_permission_for_existing_roles"),
        ("organizations", "0010_plain_patient_id_prefix"),
    ]

    operations = [migrations.RunPython(renumber, migrations.RunPython.noop)]
