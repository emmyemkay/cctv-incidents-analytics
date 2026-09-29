from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="datasetupload",
            name="file",
            field=models.FileField(blank=True, upload_to="datasets/%Y/%m/"),
        ),
        migrations.AddField(
            model_name="datasetupload",
            name="file_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="datasetupload",
            name="import_method",
            field=models.CharField(
                choices=[
                    ("UPLOAD", "Web upload"),
                    ("BUNDLED", "Bundled dataset"),
                    ("COMMAND", "Management command"),
                ],
                db_index=True,
                default="UPLOAD",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="datasetupload",
            index=models.Index(fields=["file_hash", "status"], name="idx_upload_hash_status"),
        ),
    ]
