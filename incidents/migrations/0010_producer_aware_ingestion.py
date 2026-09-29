from django.db import migrations, models


def populate_producer_ids(apps, schema_editor):
    Incident = apps.get_model("incidents", "Incident")
    Incident.objects.filter(origin__in=["UPLOAD", "COMMAND"], producer_id="").update(
        producer_id="dataset",
        payload_version="csv-v1",
    )
    Incident.objects.filter(origin="STREAM", producer_id="").update(
        producer_id="legacy-stream",
        payload_version="1.0",
    )


def reverse_producer_ids(apps, schema_editor):
    Incident = apps.get_model("incidents", "Incident")
    Incident.objects.update(producer_id="", payload_version="1.0")


class Migration(migrations.Migration):
    dependencies = [("incidents", "0009_incident_data_integrity_constraints")]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="producer_id",
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
        migrations.AddField(
            model_name="incident",
            name="payload_version",
            field=models.CharField(blank=True, default="1.0", max_length=30),
        ),
        migrations.RunPython(populate_producer_ids, reverse_producer_ids),
        migrations.RemoveConstraint(
            model_name="incident",
            name="uq_incident_source_event",
        ),
        migrations.AddConstraint(
            model_name="incident",
            constraint=models.UniqueConstraint(
                fields=("source_type", "producer_id", "event_id"),
                name="uq_incident_producer_event",
            ),
        ),
        migrations.AddIndex(
            model_name="incident",
            index=models.Index(
                fields=["producer_id", "reported_at"],
                name="idx_producer_reported",
            ),
        ),
    ]
