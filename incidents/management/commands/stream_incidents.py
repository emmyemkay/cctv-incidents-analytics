import time
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from incidents.models import Incident
from incidents.services.broadcast import broadcast_incident
from incidents.services.importer import TEXT_FIELDS, _clean_text, _valid_coordinate, detect_source_type, read_incident_csv


class Command(BaseCommand):
    help = "Replay a CSV as a real-time incident stream and publish each event over WebSockets."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--source", choices=["AUTO", *Incident.SourceType.values], default="AUTO")
        parser.add_argument("--interval", type=float, default=1.0, help="Seconds between events")
        parser.add_argument("--limit", type=int, default=0, help="Maximum rows; 0 means all")
        parser.add_argument("--use-now", action="store_true", help="Use the current time instead of the CSV time")

    def handle(self, *args, **options):
        path = options["path"]
        if not Path(path).exists():
            raise CommandError(f"File not found: {path}")
        frame = read_incident_csv(path)
        source = detect_source_type(Path(path).name, options["source"])
        if options["limit"]:
            frame = frame.head(options["limit"])

        for _, row in frame.iterrows():
            event_id = _clean_text(row.get("event_id"))
            dt = pd.to_datetime(row.get("reported_at"), dayfirst=True, errors="coerce")
            if not event_id or pd.isna(dt):
                continue
            reported_at = timezone.now() if options["use_now"] else dt.to_pydatetime()
            if timezone.is_naive(reported_at):
                reported_at = timezone.make_aware(reported_at, timezone.get_current_timezone())
            defaults = {field: _clean_text(row.get(field)) for field in TEXT_FIELDS}
            defaults.update(
                {
                    "origin": Incident.Origin.STREAM,
                    "reported_at": reported_at,
                    "longitude": _valid_coordinate(row.get("longitude"), -180, 180),
                    "latitude": _valid_coordinate(row.get("latitude"), -90, 90),
                    "raw_data": {str(k): _clean_text(v) for k, v in row.to_dict().items()},
                }
            )
            incident, _ = Incident.objects.update_or_create(source_type=source, event_id=event_id, defaults=defaults)
            broadcast_incident(incident)
            self.stdout.write(f"Published {source}/{event_id}")
            time.sleep(max(0, options["interval"]))
