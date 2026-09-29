from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from incidents.models import DatasetUpload, Incident
from incidents.services.importer import process_path_import


class Command(BaseCommand):
    help = "Import one or more supported incident CSV files and record the import history."

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="+", help="One or more CSV paths")
        parser.add_argument("--source", choices=["AUTO", *Incident.SourceType.values], default="AUTO")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Read a file again even when the same file hash was imported previously.",
        )

    def handle(self, *args, **options):
        for raw_path in options["paths"]:
            path = Path(raw_path)
            if not path.exists():
                raise CommandError(f"{path}: file not found")

            upload = DatasetUpload.objects.create(
                original_name=path.name,
                incident_type=options["source"],
                import_method=DatasetUpload.ImportMethod.COMMAND,
            )
            try:
                result = process_path_import(
                    upload,
                    path,
                    Incident.Origin.COMMAND,
                    skip_known_file=not options["force"],
                )
            except Exception as exc:
                raise CommandError(f"{path}: {exc}") from exc
            duplicate_note = " (file already imported)" if result.duplicate_file else ""
            self.stdout.write(
                self.style.SUCCESS(
                    f"{path}: source={result.source_type}, seen={result.seen}, "
                    f"imported={result.imported}, skipped={result.skipped}{duplicate_note}"
                )
            )
