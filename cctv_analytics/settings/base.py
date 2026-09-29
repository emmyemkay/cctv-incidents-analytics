from __future__ import annotations

from pathlib import Path

from cctv_analytics.env import env, env_bool, env_int, env_list

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = env("DJANGO_SECRET_KEY", "development-only-change-me")
DEBUG = False
ALLOWED_HOSTS: list[str] = []
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "daphne",
    "django_prometheus",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "django_celery_results",
    "django_celery_beat",
    "platform_core.apps.PlatformCoreConfig",
    "incidents.apps.IncidentsConfig",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "platform_core.middleware.RequestIdMiddleware",
    "platform_core.middleware.RequestTimingMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "platform_core.middleware.LoginRequiredMiddleware",
    "platform_core.middleware.RolePermissionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "cctv_analytics.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "incidents.context_processors.sidebar_metrics",
                "platform_core.context_processors.platform_metadata",
            ],
        },
    }
]
WSGI_APPLICATION = "cctv_analytics.wsgi.application"
ASGI_APPLICATION = "cctv_analytics.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Africa/Kampala")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

USE_S3_STORAGE = env_bool("USE_S3_STORAGE", False)
if USE_S3_STORAGE:
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", "us-east-1")
    AWS_S3_ADDRESSING_STYLE = env("AWS_S3_ADDRESSING_STYLE", "path")
    AWS_QUERYSTRING_AUTH = env_bool("AWS_QUERYSTRING_AUTH", True)
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
FILE_UPLOAD_MAX_MEMORY_SIZE = env_int("FILE_UPLOAD_MAX_MEMORY_SIZE", 15 * 1024 * 1024)
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int("DATA_UPLOAD_MAX_MEMORY_SIZE", 110 * 1024 * 1024)
DATA_UPLOAD_MAX_NUMBER_FIELDS = env_int("DATA_UPLOAD_MAX_NUMBER_FIELDS", 2000)

INGEST_API_TOKEN = env("INGEST_API_TOKEN", "change-me-ingest-token")
INGEST_BATCH_LIMIT = env_int("INGEST_BATCH_LIMIT", 1000)
INGEST_RATE_LIMIT_PER_MINUTE = env_int("INGEST_RATE_LIMIT_PER_MINUTE", 6000)
ANALYTICS_CACHE_TTL = env_int("ANALYTICS_CACHE_TTL", 300)
ASYNC_DATASET_IMPORTS = env_bool("ASYNC_DATASET_IMPORTS", True)
PLATFORM_VERSION = env("PLATFORM_VERSION", "3.1.0-dev")
DEPLOYMENT_ENVIRONMENT = env("DEPLOYMENT_ENVIRONMENT", "development")
REQUIRE_AUTHENTICATION = env_bool("REQUIRE_AUTHENTICATION", False)
ENFORCE_RBAC = env_bool("ENFORCE_RBAC", False)
LOGIN_URL = "/admin/login/"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

CELERY_BROKER_URL = env("CELERY_BROKER_URL", env("REDIS_URL", "redis://redis:6379/1"))
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "django-db")
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = env_int("CELERY_TASK_TIME_LIMIT", 30 * 60)
CELERY_TASK_SOFT_TIME_LIMIT = env_int("CELERY_TASK_SOFT_TIME_LIMIT", 25 * 60)
CELERY_WORKER_MAX_TASKS_PER_CHILD = env_int("CELERY_WORKER_MAX_TASKS_PER_CHILD", 250)
CELERY_TASK_ROUTES = {
    "incidents.tasks.process_dataset_upload": {"queue": "imports"},
    "incidents.tasks.refresh_analytics_snapshots": {"queue": "analytics"},
    "incidents.tasks.run_data_quality_audit": {"queue": "analytics"},
}
CELERY_BEAT_SCHEDULE = {
    "refresh-analytics-every-15-minutes": {
        "task": "incidents.tasks.refresh_analytics_snapshots",
        "schedule": 15 * 60,
    },
    "data-quality-audit-every-6-hours": {
        "task": "incidents.tasks.run_data_quality_audit",
        "schedule": 6 * 60 * 60,
    },
}

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "incident-intelligence@localhost")

LOG_LEVEL = env("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "platform_core.logging.RequestIdFilter"}},
    "formatters": {
        "json": {"()": "platform_core.logging.JsonFormatter"},
        "console": {"format": "%(levelname)s %(asctime)s %(name)s request_id=%(request_id)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if env_bool("JSON_LOGS", True) else "console",
            "filters": ["request_id"],
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "incidents": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "platform_core": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

SENTRY_DSN = env("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=DEPLOYMENT_ENVIRONMENT,
        release=PLATFORM_VERSION,
        traces_sample_rate=float(env("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
        send_default_pii=False,
    )

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": CELERY_TASK_TIME_LIMIT + 300}
