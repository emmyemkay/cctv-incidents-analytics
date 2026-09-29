from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger("incidents.broadcast")


def incident_payload(incident):
    return {
        "id": incident.id,
        "event_id": incident.event_id,
        "producer_id": incident.producer_id,
        "payload_version": incident.payload_version,
        "source_type": incident.source_type,
        "origin": incident.origin,
        "reported_at": incident.reported_at.isoformat(),
        "incident_location": incident.incident_location,
        "case_nature": incident.case_nature,
        "category": incident.category,
        "sub_category": incident.sub_category,
        "map_category": incident.analytical_category,
        "category_key": incident.analytical_category_key,
        "category_colour": incident.analytical_category_colour,
        "reporting_type": incident.reporting_type,
        "description": incident.description,
        "governing_branch": incident.governing_branch,
        "police_station": incident.police_station,
        "event_status": incident.event_status,
        "longitude": incident.longitude,
        "latitude": incident.latitude,
        "camera_id": incident.camera_id,
        "detection_label": incident.detection_label,
        "confidence": incident.confidence,
        "snapshot_url": incident.snapshot_url,
    }


def broadcast_incident(incident):
    layer = get_channel_layer()
    if layer is None:
        logger.warning("Incident broadcast skipped because no channel layer is configured", extra={"event_id": incident.event_id})
        return
    try:
        async_to_sync(layer.group_send)(
            "incident_stream",
            {"type": "incident.created", "incident": incident_payload(incident)},
        )
    except Exception:
        # The database write must not be rolled back because a dashboard client is unavailable.
        logger.exception("Incident broadcast failed", extra={"event_id": incident.event_id})
