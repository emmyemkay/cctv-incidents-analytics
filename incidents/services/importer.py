from __future__ import annotations

import hashlib
import logging
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from django.db import transaction
from django.utils import timezone

from incidents.models import DatasetUpload, Incident
from incidents.services.normalization import normalize_operational_area

logger = logging.getLogger("incidents.importer")

COLUMN_ALIASES = {
    "event instruction id": "event_id",
    "reporting time": "reported_at",
    "incident location": "incident_location",
    "case nature": "case_nature",
    "category": "category",
    "sub-category": "sub_category",
    "sub category": "sub_category",
    "reporting type": "reporting_type",
    "contact name": "contact_name",
    "contact no.": "contact_number",
    "contact no": "contact_number",
    "description": "description",
    "governing branch": "governing_branch",
    "police station": "police_station",
    "create room": "create_room",
    "feedback content": "feedback_content",
    "processing result": "processing_result",
    "event status": "event_status",
    "x coordinate": "longitude",
    "y coordinate": "latitude",
}

TEXT_FIELDS = [
    "incident_location",
    "case_nature",
    "category",
    "sub_category",
    "reporting_type",
    "contact_name",
    "contact_number",
    "description",
    "governing_branch",
    "police_station",
    "create_room",
    "feedback_content",
    "processing_result",
    "event_status",
]


@dataclass
class ImportResult:
    seen: int
    imported: int
    skipped: int
    source_type: str
    duplicate_file: bool = False


def file_sha256(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _detect_encoding(path: str | Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            with open(path, "r", encoding=encoding) as handle:
                while handle.read(1024 * 1024):
                    pass
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin1"


def _header_row(path: str | Path, encoding: str) -> int:
    preview = pd.read_csv(path, header=None, nrows=10, encoding=encoding, dtype=str)
    for index, row in preview.iterrows():
        normalized = {
            str(value).strip().lower()
            for value in row.tolist()
            if value is not None and not pd.isna(value)
        }
        if "event instruction id" in normalized and "reporting time" in normalized:
            return int(index)
    raise ValueError(
        "Could not find the incident header row. Expected 'Event Instruction ID' and 'Reporting Time'."
    )


def detect_source_type(filename: str, requested: str = "AUTO") -> str:
    if requested and requested != DatasetUpload.IncidentType.AUTO:
        return requested
    name = Path(filename).name.upper()
    if "FIRE" in name:
        return Incident.SourceType.FIRE
    if "TRAFFIC" in name:
        return Incident.SourceType.TRAFFIC
    if "GENERAL" in name and "CRIME" in name:
        return Incident.SourceType.CRIME
    if "CRIME" in name:
        return Incident.SourceType.CRIME
    return Incident.SourceType.CCTV


def _clean_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def _valid_coordinate(value, minimum: float, maximum: float):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if minimum <= number <= maximum else None


def read_incident_csv(path: str | Path) -> pd.DataFrame:
    encoding = _detect_encoding(path)
    header = _header_row(path, encoding)
    frame = pd.read_csv(
        path,
        header=header,
        encoding=encoding,
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )
    rename = {}
    for column in frame.columns:
        key = str(column).strip().lower()
        if key in COLUMN_ALIASES:
            rename[column] = COLUMN_ALIASES[key]
    frame = frame.rename(columns=rename)
    required = {"event_id", "reported_at"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(sorted(missing))}")
    return frame


def import_csv(
    path: str | Path,
    requested_source_type: str = "AUTO",
    origin: str = Incident.Origin.UPLOAD,
    batch_size: int = 1000,
) -> ImportResult:
    frame = read_incident_csv(path)
    source_type = detect_source_type(Path(path).name, requested_source_type)
    seen = len(frame.index)
    objects: list[Incident] = []

    for _, row in frame.iterrows():
        event_id = _clean_text(row.get("event_id"))
        reported_at = pd.to_datetime(row.get("reported_at"), dayfirst=True, errors="coerce")
        if not event_id or pd.isna(reported_at):
            continue

        payload = {field: _clean_text(row.get(field)) for field in TEXT_FIELDS}
        payload["police_station"] = normalize_operational_area(payload.get("police_station"))
        payload["governing_branch"] = normalize_operational_area(payload.get("governing_branch"))
        longitude = _valid_coordinate(row.get("longitude"), -180, 180)
        latitude = _valid_coordinate(row.get("latitude"), -90, 90)
        raw = {str(key): _clean_text(value) for key, value in row.to_dict().items()}
        reported_datetime = reported_at.to_pydatetime()
        if timezone.is_naive(reported_datetime):
            reported_datetime = timezone.make_aware(
                reported_datetime, timezone.get_current_timezone()
            )
        objects.append(
            Incident(
                event_id=event_id,
                producer_id="dataset",
                payload_version="csv-v1",
                source_type=source_type,
                origin=origin,
                reported_at=reported_datetime,
                longitude=longitude,
                latitude=latitude,
                raw_data=raw,
                **payload,
            )
        )

    before = Incident.objects.filter(source_type=source_type).count()
    with transaction.atomic():
        Incident.objects.bulk_create(objects, batch_size=batch_size, ignore_conflicts=True)
    after = Incident.objects.filter(source_type=source_type).count()
    imported = max(0, after - before)
    return ImportResult(
        seen=seen,
        imported=imported,
        skipped=max(0, seen - imported),
        source_type=source_type,
    )


def process_path_import(
    upload: DatasetUpload,
    path: str | Path,
    origin: str,
    *,
    skip_known_file: bool = True,
) -> ImportResult:
    path = Path(path)
    upload.status = DatasetUpload.Status.PROCESSING
    upload.started_at = timezone.now()
    logger.info("Dataset import started", extra={"event_id": upload.original_name})
    upload.error_message = ""
    upload.file_hash = file_sha256(path)
    upload.save(update_fields=["status", "started_at", "error_message", "file_hash"])

    if skip_known_file:
        previous = (
            DatasetUpload.objects.filter(
                file_hash=upload.file_hash,
                status=DatasetUpload.Status.COMPLETED,
            )
            .exclude(pk=upload.pk)
            .first()
        )
        if previous:
            previous_source = (
                previous.incident_type
                if previous.incident_type != DatasetUpload.IncidentType.AUTO
                else detect_source_type(previous.original_name)
            )
            # Do not trust import history alone: incidents may have been deleted
            # while the upload record remained in the database.
            if Incident.objects.filter(source_type=previous_source).exists():
                result = ImportResult(
                    seen=previous.rows_seen,
                    imported=0,
                    skipped=previous.rows_seen,
                    source_type=previous_source,
                    duplicate_file=True,
                )
                upload.status = DatasetUpload.Status.COMPLETED
                upload.incident_type = previous_source
                upload.rows_seen = result.seen
                upload.rows_imported = 0
                upload.rows_skipped = result.skipped
                upload.completed_at = timezone.now()
                upload.save(
                    update_fields=[
                        "status",
                        "incident_type",
                        "rows_seen",
                        "rows_imported",
                        "rows_skipped",
                        "completed_at",
                    ]
                )
                return result

    try:
        result = import_csv(path, upload.incident_type, origin)
        upload.status = DatasetUpload.Status.COMPLETED
        upload.incident_type = result.source_type
        upload.rows_seen = result.seen
        upload.rows_imported = result.imported
        upload.rows_skipped = result.skipped
        upload.completed_at = timezone.now()
        upload.save(
            update_fields=[
                "status",
                "incident_type",
                "rows_seen",
                "rows_imported",
                "rows_skipped",
                "completed_at",
            ]
        )
        logger.info(
            "Dataset import completed",
            extra={"event_id": upload.original_name, "status_code": result.imported},
        )
        return result
    except Exception as exc:
        upload.status = DatasetUpload.Status.FAILED
        upload.error_message = str(exc)
        upload.completed_at = timezone.now()
        upload.save(update_fields=["status", "error_message", "completed_at"])
        logger.exception("Dataset import failed", extra={"event_id": upload.original_name})
        raise


@contextmanager
def materialize_uploaded_file(upload: DatasetUpload):
    """Provide a local path for file-system and object-storage backends."""
    if not upload.file:
        raise ValueError("The upload does not contain a stored file.")
    try:
        yield Path(upload.file.path)
        return
    except (AttributeError, NotImplementedError):
        pass

    suffix = Path(upload.original_name).suffix or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
        upload.file.open("rb")
        for chunk in iter(lambda: upload.file.read(1024 * 1024), b""):
            temporary.write(chunk)
        temporary_path = Path(temporary.name)
    try:
        yield temporary_path
    finally:
        upload.file.close()
        temporary_path.unlink(missing_ok=True)


def process_upload(upload: DatasetUpload) -> ImportResult:
    with materialize_uploaded_file(upload) as path:
        return process_path_import(upload, path, Incident.Origin.UPLOAD)
