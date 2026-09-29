from __future__ import annotations

import logging
import time
import uuid

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from .logging import reset_request_id, set_request_id

logger = logging.getLogger("platform_core.request")


class RequestIdMiddleware:
    header_name = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get(self.header_name) or uuid.uuid4().hex
        request.request_id = request_id
        token = set_request_id(request_id)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response
        finally:
            reset_request_id(token)


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response["Server-Timing"] = f'app;dur={duration_ms}'
        logger.info(
            "%s %s",
            request.method,
            request.path,
            extra={
                "duration_ms": duration_ms,
                "status_code": response.status_code,
                "user_id": getattr(getattr(request, "user", None), "pk", None),
            },
        )
        return response


class LoginRequiredMiddleware:
    """Protect the operational UI in production while keeping health and ingestion endpoints available."""

    exempt_prefixes = (
        "/admin/login/", "/health/", "/metrics/", "/api/v1/incidents/ingest/",
        "/static/", "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.REQUIRE_AUTHENTICATION:
            return self.get_response(request)
        if request.path.startswith(self.exempt_prefixes) or getattr(request.user, "is_authenticated", False):
            return self.get_response(request)
        login_url = reverse("admin:login")
        return redirect(f"{login_url}?next={request.get_full_path()}")


class RolePermissionMiddleware:
    """Apply Django's built-in model permissions at operational boundaries."""

    exempt_prefixes = (
        "/admin/", "/health/", "/metrics/", "/api/v1/incidents/ingest/",
        "/static/", "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.ENFORCE_RBAC or request.path.startswith(self.exempt_prefixes):
            return self.get_response(request)
        user = request.user
        if user.is_superuser:
            return self.get_response(request)
        permission = "incidents.add_datasetupload" if request.path.startswith("/datasets/upload/") else "incidents.view_incident"
        if not user.has_perm(permission):
            raise PermissionDenied(f"Missing required permission: {permission}")
        return self.get_response(request)
