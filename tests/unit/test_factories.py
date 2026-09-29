import pytest

from incidents.models import DatasetUpload, Incident


@pytest.mark.django_db
def test_incident_factory_creates_valid_incident(incident_factory):
    incident = incident_factory()

    assert incident.pk is not None
    assert incident.source_type == Incident.SourceType.CRIME
    assert incident.has_coordinates is True


@pytest.mark.django_db
def test_dataset_upload_factory_creates_pending_upload(dataset_upload_factory):
    upload = dataset_upload_factory()

    assert upload.pk is not None
    assert upload.status == DatasetUpload.Status.PENDING
