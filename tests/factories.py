from __future__ import annotations

from django.utils import timezone
import factory

from incidents.models import DatasetUpload, Incident


class DatasetUploadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DatasetUpload

    original_name = factory.Sequence(lambda number: f"dataset-{number}.csv")
    incident_type = DatasetUpload.IncidentType.CRIME
    import_method = DatasetUpload.ImportMethod.UPLOAD
    status = DatasetUpload.Status.PENDING


class IncidentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Incident

    event_id = factory.Sequence(lambda number: f"TEST-{number:06d}")
    producer_id = "pytest"
    payload_version = "1.0"
    source_type = Incident.SourceType.CRIME
    origin = Incident.Origin.UPLOAD
    reported_at = factory.LazyFunction(timezone.now)
    incident_location = "Kampala Central"
    case_nature = "GENERAL CRIMES"
    category = "THEFTS"
    reporting_type = "CALL OR ASK FOR HELP"
    governing_branch = "KAMPALA METROPOLITAN"
    police_station = "CENTRAL POLICE STATION"
    event_status = "RECEIVED"
    longitude = 32.5825
    latitude = 0.3476
