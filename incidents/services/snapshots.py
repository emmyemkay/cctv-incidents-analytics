from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping

from django.conf import settings
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Max

from incidents.models import AnalyticsSnapshot


ANALYTICS_SCHEMA_VERSION = "v6-gis-map-report"


def json_safe(payload):
    return json.loads(json.dumps(payload, cls=DjangoJSONEncoder))


def _version_token(queryset) -> str:
    state = queryset.aggregate(total_count=Count("id"), latest_created=Max("created_at"))
    raw = f"{state['total_count']}:{state['latest_created']}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def cached_payload(
    key: str,
    queryset,
    params: Mapping[str, str],
    builder: Callable,
    *,
    persist: bool = False,
):
    """Cache unfiltered analytics and fall back to a durable snapshot."""
    if any(value for value in params.values()):
        return builder(queryset)

    version = _version_token(queryset)
    cache_key = f"analytics:{ANALYTICS_SCHEMA_VERSION}:{key}:{version}"
    snapshot_key = f"{key}:{ANALYTICS_SCHEMA_VERSION}"
    payload = cache.get(cache_key)
    if payload is not None:
        return payload

    try:
        payload = builder(queryset)
        cache.set(cache_key, payload, settings.ANALYTICS_CACHE_TTL)
        if persist:
            latest = queryset.aggregate(value=Max("reported_at"))["value"]
            AnalyticsSnapshot.objects.update_or_create(
                key=snapshot_key,
                defaults={
                    "payload": json_safe(payload),
                    "source_row_count": queryset.count(),
                    "latest_reported_at": latest,
                },
            )
        return payload
    except Exception:
        if persist:
            snapshot = AnalyticsSnapshot.objects.filter(key=snapshot_key).first()
            if snapshot:
                return snapshot.payload
        raise


def invalidate_analytics_cache():
    # django-redis implements delete_pattern; other cache backends do not.
    delete_pattern = getattr(cache, "delete_pattern", None)
    if callable(delete_pattern):
        delete_pattern("analytics:*")
        cache.delete_many([
            "sidebar:metrics:v2",
            "analytics:filter-options:v2",
            "analytics:filter-options:v3",
            "analytics:filter-options:v4",
            "analytics:filter-options:v5-category-primary",
            "analytics:filter-options:v6-gis-map-report",
        ])
    else:
        cache.clear()
