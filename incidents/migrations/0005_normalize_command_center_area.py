import re

from django.db import migrations


COMMAND_CENTER_LABEL = "Command Center"
COMMAND_CENTER_ALIASES = {
    "COMMAND CENTER",
    "COMMAND CENTRE",
    "CONTROL ROOM",
    "HEADQUARTERS",
}


def group_command_center_labels(apps, schema_editor):
    Incident = apps.get_model("incidents", "Incident")
    pending = []

    for incident in Incident.objects.exclude(police_station="").only(
        "id", "police_station"
    ).iterator(chunk_size=2000):
        normalized = re.sub(r"\s+", " ", incident.police_station or "").strip()
        if normalized.upper() not in COMMAND_CENTER_ALIASES:
            continue
        if incident.police_station == COMMAND_CENTER_LABEL:
            continue
        incident.police_station = COMMAND_CENTER_LABEL
        pending.append(incident)
        if len(pending) >= 1000:
            Incident.objects.bulk_update(pending, ["police_station"], batch_size=1000)
            pending.clear()

    if pending:
        Incident.objects.bulk_update(pending, ["police_station"], batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0004_remove_manual_capture_origin"),
    ]

    operations = [
        migrations.RunPython(group_command_center_labels, migrations.RunPython.noop),
    ]
