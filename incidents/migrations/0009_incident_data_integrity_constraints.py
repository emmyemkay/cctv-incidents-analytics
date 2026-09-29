from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("incidents", "0008_incident_analytics_indexes")]

    operations = [
        migrations.AddConstraint(
            model_name="incident",
            constraint=models.CheckConstraint(
                condition=models.Q(longitude__isnull=True) | models.Q(longitude__gte=-180, longitude__lte=180),
                name="ck_incident_longitude_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="incident",
            constraint=models.CheckConstraint(
                condition=models.Q(latitude__isnull=True) | models.Q(latitude__gte=-90, latitude__lte=90),
                name="ck_incident_latitude_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="incident",
            constraint=models.CheckConstraint(
                condition=models.Q(confidence__isnull=True) | models.Q(confidence__gte=0, confidence__lte=1),
                name="ck_incident_confidence_range",
            ),
        ),
    ]
