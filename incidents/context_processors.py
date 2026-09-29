from datetime import timedelta

from django.core.cache import cache
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone

from .models import DatasetUpload, Incident


def sidebar_metrics(request):
    cache_key = "sidebar:metrics:v2"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        payload = {
            "sidebar_incident_count": Incident.objects.count(),
            "sidebar_live_count": Incident.objects.filter(
                origin=Incident.Origin.STREAM,
                created_at__gte=timezone.now() - timedelta(days=1),
            ).count(),
            "sidebar_failed_imports": DatasetUpload.objects.filter(status=DatasetUpload.Status.FAILED).count(),
            "sidebar_pending_imports": DatasetUpload.objects.filter(
                status__in=[DatasetUpload.Status.PENDING, DatasetUpload.Status.PROCESSING]
            ).count(),
        }
        cache.set(cache_key, payload, 30)
        return payload
    except (OperationalError, ProgrammingError):
        return {
            "sidebar_incident_count": 0,
            "sidebar_live_count": 0,
            "sidebar_failed_imports": 0,
            "sidebar_pending_imports": 0,
        }
