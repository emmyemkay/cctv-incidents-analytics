from django.db import migrations, models


def convert_manual_origins(apps, schema_editor):
    Incident = apps.get_model("incidents", "Incident")
    for incident in Incident.objects.filter(origin="MANUAL").iterator():
        raw = incident.raw_data if isinstance(incident.raw_data, dict) else {}
        raw.setdefault("legacy_origin", "MANUAL")
        raw.setdefault("migration_note", "Manual web capture was removed from the application.")
        incident.origin = "UPLOAD"
        incident.raw_data = raw
        incident.save(update_fields=["origin", "raw_data"])


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0003_incident_manual_origin"),
    ]

    operations = [
        migrations.RunPython(convert_manual_origins, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="incident",
            name="origin",
            field=models.CharField(
                choices=[
                    ("UPLOAD", "File upload"),
                    ("STREAM", "Real-time stream"),
                    ("COMMAND", "Management command"),
                ],
                db_index=True,
                default="UPLOAD",
                max_length=20,
            ),
        ),
    ]
