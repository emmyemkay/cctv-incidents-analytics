from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("incidents", "0006_normalize_command_center_branches")]

    operations = [
        migrations.AddField(
            model_name="datasetupload",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="datasetupload",
            name="task_id",
            field=models.CharField(blank=True, db_index=True, max_length=80),
        ),
        migrations.CreateModel(
            name="AnalyticsSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=120, unique=True)),
                ("payload", models.JSONField(default=dict)),
                ("source_row_count", models.PositiveBigIntegerField(default=0)),
                ("latest_reported_at", models.DateTimeField(blank=True, null=True)),
                ("generated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-generated_at"]},
        ),
    ]
