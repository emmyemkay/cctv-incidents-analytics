from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from incidents.models import DatasetUpload, Incident
from incidents.services.analytics import dashboard_payload, data_quality_payload
from incidents.services.importer import process_upload
from incidents.services.snapshots import cached_payload, invalidate_analytics_cache

logger = logging.getLogger("incidents.tasks")


@shared_task(bind=True, autoretry_for=(OSError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_dataset_upload(self, upload_id: int):
    upload = DatasetUpload.objects.get(pk=upload_id)
    upload.task_id = self.request.id or upload.task_id
    upload.started_at = timezone.now()
    upload.save(update_fields=["task_id", "started_at"])
    result = process_upload(upload)
    invalidate_analytics_cache()
    logger.info(
        "Dataset import completed",
        extra={"event_id": upload.original_name, "status_code": result.imported},
    )
    return {
        "upload_id": upload.id,
        "seen": result.seen,
        "imported": result.imported,
        "skipped": result.skipped,
        "source_type": result.source_type,
    }


@shared_task
def refresh_analytics_snapshots():
    queryset = Incident.objects.all()
    payload = cached_payload(
        "dashboard-default", queryset, {},
        lambda qs: dashboard_payload(qs, include_map=False), persist=True,
    )
    return {"snapshot": "dashboard-default", "incidents": payload.get("kpis", {}).get("total", 0)}


@shared_task
def run_data_quality_audit():
    queryset = Incident.objects.all()
    payload = cached_payload("data-quality-default", queryset, {}, data_quality_payload, persist=True)
    return {"snapshot": "data-quality-default", "incidents": payload.get("kpis", {}).get("total", 0)}
