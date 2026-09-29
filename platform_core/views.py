from __future__ import annotations

from datetime import datetime, timezone

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse


def _check_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return {"status": "ok"}


def _check_cache():
    key = "health:cache"
    cache.set(key, "ok", 10)
    if cache.get(key) != "ok":
        raise RuntimeError("cache write/read check failed")
    return {"status": "ok"}


async def _round_trip_channel(layer):
    channel_name = await layer.new_channel("health.")
    await layer.send(channel_name, {"type": "health.message", "value": "ok"})
    message = await layer.receive(channel_name)
    if message.get("value") != "ok":
        raise RuntimeError("channel layer round-trip check failed")


def _check_channels():
    layer = get_channel_layer()
    if layer is None:
        raise RuntimeError("channel layer is unavailable")
    async_to_sync(_round_trip_channel)(layer)
    return {"status": "ok"}


def live(request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "incident-intelligence-web",
            "version": settings.PLATFORM_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


def ready(request):
    checks = {}
    failed = False
    for name, check in (("database", _check_database), ("cache", _check_cache), ("channels", _check_channels)):
        try:
            checks[name] = check()
        except Exception as exc:  # readiness must report dependency failures
            checks[name] = {"status": "error", "detail": str(exc)}
            failed = True
    return JsonResponse(
        {
            "status": "error" if failed else "ok",
            "version": settings.PLATFORM_VERSION,
            "environment": settings.DEPLOYMENT_ENVIRONMENT,
            "checks": checks,
        },
        status=503 if failed else 200,
    )
