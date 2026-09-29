import re

from django.db import migrations

COMMAND_CENTER_LABEL = "Command Center"
COMMAND_CENTER_ALIASES = {"COMMAND CENTER", "COMMAND CENTRE", "CONTROL ROOM", "HEADQUARTERS"}


def normalize_command_center_branches(apps, schema_editor):
    Incident = apps.get_model("incidents", "Incident")
    pending = []
    for incident in Incident.objects.exclude(governing_branch="").only("id", "governing_branch").iterator(chunk_size=2000):
        normalized = re.sub(r"\s+", " ", incident.governing_branch or "").strip()
        if normalized.upper() not in COMMAND_CENTER_ALIASES or incident.governing_branch == COMMAND_CENTER_LABEL:
            continue
        incident.governing_branch = COMMAND_CENTER_LABEL
        pending.append(incident)
        if len(pending) >= 1000:
            Incident.objects.bulk_update(pending, ["governing_branch"], batch_size=1000)
            pending.clear()
    if pending:
        Incident.objects.bulk_update(pending, ["governing_branch"], batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [("incidents", "0005_normalize_command_center_area")]
    operations = [migrations.RunPython(normalize_command_center_branches, migrations.RunPython.noop)]
