from __future__ import annotations

import pytest

from incidents.models import Incident
from incidents.services.analytics import map_points_metadata, map_points_payload


@pytest.mark.django_db
def test_map_points_use_category_and_exclude_outside_uganda(incident_factory):
    valid = incident_factory(
        category="ROBBERIES",
        sub_category="ARMED ROBBERY",
        latitude=0.3476,
        longitude=32.5825,
    )
    incident_factory(
        category="ROBBERIES",
        latitude=10.0,
        longitude=32.5825,
    )

    points = map_points_payload(Incident.objects.all(), limit=100)

    assert len(points) == 1
    assert points[0]["id"] == valid.id
    assert points[0]["map_category"] == "ROBBERIES"
    assert points[0]["category_key"] == "ROBBERIES"
    assert points[0]["category_colour"].startswith("hsl(")
    assert points[0]["case_nature"]
    assert points[0]["reporting_type"]


@pytest.mark.django_db
def test_map_category_uses_subcategory_only_when_category_is_blank(incident_factory):
    incident_factory(category="", sub_category="DOMESTIC VIOLENCE")
    incident_factory(category="THEFTS", sub_category="MOTOR VEHICLE THEFT")
    incident_factory(category="", sub_category="", detection_label="Suspicious movement", case_nature="GENERAL CRIMES")

    points = map_points_payload(Incident.objects.all(), limit=100)
    categories = {point["map_category"] for point in points}

    assert "DOMESTIC VIOLENCE" in categories
    assert "THEFTS" in categories
    assert "MOTOR VEHICLE THEFT" not in categories
    assert "Suspicious movement" not in categories
    assert "GENERAL CRIMES" not in categories
    assert "Uncategorised" in categories


@pytest.mark.django_db
def test_map_metadata_reports_coordinate_coverage(incident_factory):
    incident_factory(latitude=0.3476, longitude=32.5825)
    incident_factory(latitude=None, longitude=None)
    incident_factory(latitude=0.0, longitude=0.0)

    queryset = Incident.objects.all()
    points = map_points_payload(queryset, limit=100)
    metadata = map_points_metadata(queryset, len(points))

    assert metadata["filtered_total"] == 3
    assert metadata["mapped_total"] == 1
    assert metadata["unmapped_or_invalid_total"] == 2
    assert metadata["returned_total"] == 1
    assert metadata["truncated"] is False
