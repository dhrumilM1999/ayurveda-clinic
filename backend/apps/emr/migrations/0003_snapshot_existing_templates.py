"""Save a frozen copy (version history) of every template that already exists."""
from django.db import migrations


def forwards(apps, schema_editor):
    ExamTemplate = apps.get_model("emr", "ExamTemplate")
    ExamTemplateVersion = apps.get_model("emr", "ExamTemplateVersion")
    for template in ExamTemplate.objects.all():
        ExamTemplateVersion.objects.get_or_create(
            template=template, version=template.version, defaults={"fields": template.fields},
        )


class Migration(migrations.Migration):
    dependencies = [("emr", "0002_template_versions_and_photos")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
