# Generated manually for the supplied project.
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="DatasetUpload",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="datasets/%Y/%m/")),
                ("original_name", models.CharField(max_length=255)),
                ("incident_type", models.CharField(choices=[("AUTO", "Auto-detect from filename"), ("FIRE", "Fire"), ("CRIME", "General crime"), ("TRAFFIC", "Traffic"), ("CCTV", "CCTV detection")], default="AUTO", max_length=20)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("PROCESSING", "Processing"), ("COMPLETED", "Completed"), ("FAILED", "Failed")], default="PENDING", max_length=20)),
                ("rows_seen", models.PositiveIntegerField(default=0)),
                ("rows_imported", models.PositiveIntegerField(default=0)),
                ("rows_skipped", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-uploaded_at"]},
        ),
        migrations.CreateModel(
            name="Incident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.CharField(max_length=80)),
                ("source_type", models.CharField(choices=[("FIRE", "Fire"), ("CRIME", "General crime"), ("TRAFFIC", "Traffic"), ("CCTV", "CCTV detection")], db_index=True, max_length=20)),
                ("origin", models.CharField(choices=[("UPLOAD", "File upload"), ("STREAM", "Real-time stream"), ("COMMAND", "Management command")], db_index=True, default="UPLOAD", max_length=20)),
                ("reported_at", models.DateTimeField(db_index=True)),
                ("incident_location", models.TextField(blank=True)),
                ("case_nature", models.CharField(blank=True, db_index=True, max_length=255)),
                ("category", models.CharField(blank=True, db_index=True, max_length=255)),
                ("sub_category", models.CharField(blank=True, max_length=255)),
                ("reporting_type", models.CharField(blank=True, max_length=255)),
                ("contact_name", models.CharField(blank=True, max_length=255)),
                ("contact_number", models.CharField(blank=True, max_length=80)),
                ("description", models.TextField(blank=True)),
                ("governing_branch", models.CharField(blank=True, db_index=True, max_length=255)),
                ("police_station", models.CharField(blank=True, db_index=True, max_length=255)),
                ("create_room", models.CharField(blank=True, max_length=255)),
                ("feedback_content", models.TextField(blank=True)),
                ("processing_result", models.TextField(blank=True)),
                ("event_status", models.CharField(blank=True, db_index=True, max_length=100)),
                ("longitude", models.FloatField(blank=True, db_index=True, null=True)),
                ("latitude", models.FloatField(blank=True, db_index=True, null=True)),
                ("camera_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("detection_label", models.CharField(blank=True, db_index=True, max_length=120)),
                ("confidence", models.FloatField(blank=True, null=True)),
                ("snapshot_url", models.URLField(blank=True)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-reported_at"],
                "indexes": [
                    models.Index(fields=["source_type", "reported_at"], name="idx_source_reported"),
                    models.Index(fields=["police_station", "reported_at"], name="idx_station_reported"),
                    models.Index(fields=["event_status", "reported_at"], name="idx_status_reported"),
                ],
                "constraints": [models.UniqueConstraint(fields=("source_type", "event_id"), name="uq_incident_source_event")],
            },
        ),
    ]
