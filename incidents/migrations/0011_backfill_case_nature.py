from django.db import migrations, models


def backfill_case_nature(apps, schema_editor):
    Incident = apps.get_model("incidents", "Incident")
    Incident.objects.filter(case_nature="").exclude(category="").update(
        case_nature=models.F("category")
    )
    Incident.objects.filter(case_nature="", category="").exclude(sub_category="").update(
        case_nature=models.F("sub_category")
    )
    Incident.objects.filter(case_nature="", category="", sub_category="").update(
        case_nature="Uncategorised"
    )


def reverse_backfill(apps, schema_editor):
    # Source rows cannot be reconstructed safely after fallback values are materialized.
    pass


class Migration(migrations.Migration):
    dependencies = [("incidents", "0010_producer_aware_ingestion")]

    operations = [migrations.RunPython(backfill_case_nature, reverse_backfill)]
