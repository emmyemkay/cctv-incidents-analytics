from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0002_datasetupload_import_tracking"),
    ]

    operations = [
        migrations.AlterField(
            model_name="incident",
            name="origin",
            field=models.CharField(
                choices=[
                    ("UPLOAD", "File upload"),
                    ("STREAM", "Real-time stream"),
                    ("COMMAND", "Management command"),
                    ("MANUAL", "Manual web entry"),
                ],
                db_index=True,
                default="UPLOAD",
                max_length=20,
            ),
        ),
    ]
