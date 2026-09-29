from .base import *  # noqa: F403,F401
from cctv_analytics.env import env, env_bool, env_int, env_list, require_env

DEBUG = False
REQUIRE_AUTHENTICATION = env_bool("REQUIRE_AUTHENTICATION", True)
ENFORCE_RBAC = env_bool("ENFORCE_RBAC", True)
SECRET_KEY = require_env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must contain at least one host in production")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": require_env("POSTGRES_DB"),
        "USER": require_env("POSTGRES_USER"),
        "PASSWORD": require_env("POSTGRES_PASSWORD"),
        "HOST": require_env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 120),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 10,
            "sslmode": env("POSTGRES_SSLMODE", "prefer"),
            "options": f"-c statement_timeout={env_int('DB_STATEMENT_TIMEOUT_MS', 60000)}",
            "pool": {
                "min_size": env_int("DB_POOL_MIN_SIZE", 1),
                "max_size": env_int("DB_POOL_MAX_SIZE", 10),
                "timeout": env_int("DB_POOL_TIMEOUT", 30),
            },
        },
    }
}

REDIS_URL = require_env("REDIS_URL")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("CACHE_REDIS_URL", REDIS_URL.replace("/0", "/2")),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient", "IGNORE_EXCEPTIONS": False},
        "TIMEOUT": ANALYTICS_CACHE_TTL,  # noqa: F405
    }
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("CHANNEL_REDIS_URL", REDIS_URL)],
            "capacity": env_int("CHANNEL_CAPACITY", 3000),
            "expiry": env_int("CHANNEL_EXPIRY", 60),
        },
    }
}
CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL.replace("/0", "/1"))

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

if INGEST_API_TOKEN in {"", "change-me-ingest-token"}:  # noqa: F405
    raise RuntimeError("INGEST_API_TOKEN must be changed in production")

if USE_S3_STORAGE:
    require_env("AWS_ACCESS_KEY_ID")
    require_env("AWS_SECRET_ACCESS_KEY")
    require_env("AWS_STORAGE_BUCKET_NAME")
