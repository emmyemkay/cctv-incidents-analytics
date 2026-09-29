from __future__ import annotations

import pytest

from tests.factories import DatasetUploadFactory, IncidentFactory


@pytest.fixture
def incident_factory():
    return IncidentFactory


@pytest.fixture
def dataset_upload_factory():
    return DatasetUploadFactory
