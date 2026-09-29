from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def deployment_configuration_checks(app_configs, **kwargs):
    messages = []
    database_engine = settings.DATABASES["default"]["ENGINE"]
    if not settings.DEBUG and settings.SECRET_KEY in {"development-only-change-me", ""}:
        messages.append(Error("An insecure DJANGO_SECRET_KEY is configured.", id="platform.E001"))
    if not settings.DEBUG and settings.INGEST_API_TOKEN in {"change-me-ingest-token", ""}:
        messages.append(Error("An insecure INGEST_API_TOKEN is configured.", id="platform.E002"))
    if settings.DEBUG and settings.DEPLOYMENT_ENVIRONMENT == "production":
        messages.append(Error("DEBUG cannot be enabled in production.", id="platform.E003"))
    if settings.DEPLOYMENT_ENVIRONMENT == "production" and "sqlite3" in database_engine:
        messages.append(Error("SQLite is not allowed for production deployment.", id="platform.E004"))
    if settings.DEPLOYMENT_ENVIRONMENT == "production" and not settings.REQUIRE_AUTHENTICATION:
        messages.append(Warning("Operational pages are not protected by login.", id="platform.W002"))
    if settings.DEPLOYMENT_ENVIRONMENT == "production" and not settings.ENFORCE_RBAC:
        messages.append(Warning("Operational role permissions are not enforced.", id="platform.W003"))
    if settings.CHANNEL_LAYERS["default"]["BACKEND"].endswith("InMemoryChannelLayer"):
        messages.append(
            Warning(
                "The in-memory channel layer is suitable only for single-process development.",
                id="platform.W001",
            )
        )
    return messages
