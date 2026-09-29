from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from incidents.models import DatasetUpload, Incident
from incidents.services.importer import detect_source_type, file_sha256, process_path_import


DEFAULT_FILES = (
    "FIRE-INCIDENTS-2020-2024.csv",
    "GENERAL-CRIME-2020-2024.csv",
    "TRAFFIC-INCIDENTS-2020-2024.csv",
)


class Command(BaseCommand):
    help = "Import the Fire, General Crime, and Traffic CSV files bundled in the data directory."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            default=str(settings.BASE_DIR / "data"),
            help="Directory containing the bundled CSV files.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Read the files again even when the same file hash was imported previously.",
        )

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        force = options["force"]
        failures: list[str] = []

        for filename in DEFAULT_FILES:
            path = data_dir / filename
            if not path.exists():
                failures.append(f"Missing bundled dataset: {path}")
                continue

            checksum = file_sha256(path)
            source_type = detect_source_type(filename)
            known_file = DatasetUpload.objects.filter(
                file_hash=checksum,
                status=DatasetUpload.Status.COMPLETED,
            ).exists()
            source_has_data = Incident.objects.filter(source_type=source_type).exists()
            if not force and known_file and source_has_data:
                self.stdout.write(self.style.WARNING(f"{filename}: already imported; skipped."))
                continue

            upload = DatasetUpload.objects.create(
                original_name=filename,
                file_hash=checksum,
                incident_type=DatasetUpload.IncidentType.AUTO,
                import_method=DatasetUpload.ImportMethod.BUNDLED,
            )
            try:
                result = process_path_import(
                    upload,
                    path,
                    Incident.Origin.COMMAND,
                    skip_known_file=not force,
                )
            except Exception as exc:
                failures.append(f"{filename}: {exc}")
                continue

            self.stdout.write(
                self.style.SUCCESS(
                    f"{filename}: source={result.source_type}, seen={result.seen}, "
                    f"imported={result.imported}, skipped={result.skipped}"
                )
            )

        if failures:
            raise CommandError("; ".join(failures))
