from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import DatasetUpload, Incident
from .services.analytics import dashboard_payload, filtered_incidents, map_points_metadata, map_points_payload
from .services.broadcast import broadcast_incident, incident_payload
from .services.snapshots import cached_payload, invalidate_analytics_cache
from .services.normalization import normalize_operational_area


def _clean_text(value, default=""):
    if value is None:
        return default
    text = str(value).strip()
    return default if text.lower() in {"", "none", "null", "nan"} else text


def _authorized(request):
    supplied = request.headers.get("X-Ingest-Token", "")
    expected = settings.INGEST_API_TOKEN or ""
    return bool(supplied and expected and secrets.compare_digest(supplied, expected))



def _rate_limit_key(request):
    identity = request.headers.get("X-Producer-ID") or request.META.get("REMOTE_ADDR", "unknown")
    minute = timezone.now().strftime("%Y%m%d%H%M")
    return f"ingest-rate:{identity}:{minute}"


def _rate_limit_exceeded(request):
    key = _rate_limit_key(request)
    try:
        value = cache.incr(key)
    except ValueError:
        cache.set(key, 1, 70)
        value = 1
    return value > settings.INGEST_RATE_LIMIT_PER_MINUTE

def _parse_reported_at(value):
    if not value:
        return timezone.now()
    parsed = parse_datetime(str(value))
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError("reported_at must be an ISO-8601 datetime") from exc
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _float_or_none(value, minimum, maximum):
    if value in (None, ""):
        return None
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"coordinate must be between {minimum} and {maximum}")
    return number


def _save_event(item):
    source_type = _clean_text(item.get("source_type"), Incident.SourceType.CCTV).upper()
    if source_type not in Incident.SourceType.values:
        raise ValueError(f"source_type must be one of: {', '.join(Incident.SourceType.values)}")
    event_id = _clean_text(item.get("event_id")) or f"stream-{uuid.uuid4().hex}"
    producer_id = _clean_text(item.get("_producer_id") or item.get("producer_id") or item.get("camera_id"), "unknown")
    defaults = {
        "payload_version": _clean_text(item.get("payload_version"), "1.0"),
        "origin": Incident.Origin.STREAM,
        "reported_at": _parse_reported_at(item.get("reported_at")),
        "incident_location": _clean_text(item.get("incident_location")),
        "case_nature": _clean_text(item.get("case_nature")),
        "category": _clean_text(item.get("category")),
        "sub_category": _clean_text(item.get("sub_category", item.get("subcategory"))),
        "reporting_type": _clean_text(item.get("reporting_type"), "Automated CCTV stream"),
        "description": _clean_text(item.get("description")),
        "governing_branch": normalize_operational_area(item.get("governing_branch", "")),
        "police_station": normalize_operational_area(item.get("police_station", "")),
        "event_status": _clean_text(item.get("event_status"), "New"),
        "longitude": _float_or_none(item.get("longitude"), -180, 180),
        "latitude": _float_or_none(item.get("latitude"), -90, 90),
        "camera_id": _clean_text(item.get("camera_id")),
        "detection_label": _clean_text(item.get("detection_label")),
        "confidence": _float_or_none(item.get("confidence"), 0, 1),
        "snapshot_url": _clean_text(item.get("snapshot_url")),
        "raw_data": item,
    }
    incident, created = Incident.objects.update_or_create(
        source_type=source_type,
        producer_id=producer_id,
        event_id=event_id,
        defaults=defaults,
    )
    transaction.on_commit(lambda: broadcast_incident(incident))
    return incident, created


@csrf_exempt
@require_POST
def ingest_incidents(request):
    if request.content_type != "application/json":
        return JsonResponse({"detail": "Content-Type must be application/json."}, status=415)
    if not _authorized(request):
        return JsonResponse({"detail": "Invalid or missing X-Ingest-Token."}, status=401)
    if _rate_limit_exceeded(request):
        return JsonResponse({"detail": "Ingestion rate limit exceeded."}, status=429)
    try:
        payload = json.loads(request.body or b"{}")
        items = payload if isinstance(payload, list) else [payload]
        if not items or not all(isinstance(item, dict) for item in items):
            raise ValueError("The request body must be an object or a list of objects.")
        if len(items) > settings.INGEST_BATCH_LIMIT:
            raise ValueError(f"A maximum of {settings.INGEST_BATCH_LIMIT} events is allowed per request.")
        results = []
        with transaction.atomic():
            for item in items:
                enriched = dict(item)
                enriched.setdefault("_producer_id", request.headers.get("X-Producer-ID", "unknown"))
                enriched.setdefault("_request_id", getattr(request, "request_id", ""))
                enriched.setdefault("_received_at", timezone.now().isoformat())
                incident, created = _save_event(enriched)
                results.append({"created": created, "incident": incident_payload(incident)})
        invalidate_analytics_cache()
        response = JsonResponse({"accepted": len(results), "results": results}, status=201)
        response["X-Request-ID"] = getattr(request, "request_id", "")
        return response
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


@require_GET
def analytics_summary(request):
    queryset = filtered_incidents(request.GET)
    payload = cached_payload(
        "dashboard-default", queryset, request.GET,
        lambda qs: dashboard_payload(qs, include_map=False), persist=True,
    )
    return JsonResponse(payload, safe=True)


@require_GET
def analytics_map_points(request):
    queryset = filtered_incidents(request.GET)
    try:
        requested = int(request.GET.get("limit", 50000))
    except (TypeError, ValueError):
        requested = 50000
    limit = min(max(requested, 100), 50000)
    points = cached_payload(
        f"dashboard-map-category-v7-gis-report-{limit}", queryset, request.GET,
        lambda qs: map_points_payload(qs, limit=limit), persist=False,
    )
    metadata = map_points_metadata(queryset, len(points))
    return JsonResponse({"count": len(points), "points": points, "metadata": metadata})


@require_GET
def import_status(request):
    uploads = list(
        DatasetUpload.objects.values(
            "id", "original_name", "status", "rows_seen", "rows_imported", "rows_skipped",
            "error_message", "task_id", "uploaded_at", "started_at", "completed_at",
        ).order_by("-uploaded_at")[:30]
    )
    active = sum(1 for item in uploads if item["status"] in {DatasetUpload.Status.PENDING, DatasetUpload.Status.PROCESSING})
    return JsonResponse({"active": active, "uploads": uploads})
