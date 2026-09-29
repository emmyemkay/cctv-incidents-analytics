from __future__ import annotations

import pytest

from incidents.models import Incident
from incidents.services.analytics import (
    analytical_category_values,
    count_series,
    filtered_incidents,
)


@pytest.mark.django_db
def test_category_has_priority_over_subcategory(incident_factory):
    incident_factory(category="THEFTS", sub_category="MOTOR VEHICLE THEFT")

    row = count_series(Incident.objects.all(), "category", 10)[0]

    assert row == {"category": "THEFTS", "total": 1}


@pytest.mark.django_db
def test_subcategory_is_used_only_when_category_is_blank(incident_factory):
    incident_factory(category="", sub_category="DOMESTIC VIOLENCE")

    assert analytical_category_values() == ["DOMESTIC VIOLENCE"]
    assert filtered_incidents({"category": "DOMESTIC VIOLENCE"}).count() == 1


@pytest.mark.django_db
def test_both_blank_becomes_uncategorised(incident_factory):
    incident_factory(category="", sub_category="")

    assert analytical_category_values() == ["Uncategorised"]
    assert filtered_incidents({"category": "Uncategorised"}).count() == 1
