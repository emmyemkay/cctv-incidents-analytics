from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("incidents", "0007_architecture_analytics_snapshot")]

    operations = [
        migrations.AddIndex(
            model_name="incident",
            index=models.Index(fields=["category", "reported_at"], name="idx_category_reported"),
        ),
        migrations.AddIndex(
            model_name="incident",
            index=models.Index(fields=["governing_branch", "reported_at"], name="idx_branch_reported"),
        ),
        migrations.AddIndex(
            model_name="incident",
            index=models.Index(fields=["origin", "created_at"], name="idx_origin_created"),
        ),
        migrations.AddIndex(
            model_name="incident",
            index=models.Index(fields=["source_type", "category"], name="idx_source_category"),
        ),
        migrations.AddIndex(
            model_name="incident",
            index=models.Index(fields=["police_station", "event_status"], name="idx_station_status"),
        ),
    ]
