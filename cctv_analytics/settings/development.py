from .base import *  # noqa: F403,F401
from cctv_analytics.env import env, env_bool, env_int, env_list, sqlite_path

DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = env("DJANGO_SECRET_KEY", "development-only-change-me")
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    ["localhost", "127.0.0.1", "0.0.0.0", "web", "nginx"],
)

if env_bool("USE_POSTGRES", bool(env("POSTGRES_DB"))):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "cctv_analytics"),
            "USER": env("POSTGRES_USER", "cctv"),
            "PASSWORD": env("POSTGRES_PASSWORD", "cctv"),
            "HOST": env("POSTGRES_HOST", "db"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 0),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                "connect_timeout": env_int("DB_CONNECT_TIMEOUT", 10),
                "sslmode": env("POSTGRES_SSLMODE", "prefer"),
            },
        }
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": sqlite_path(BASE_DIR)}}  # noqa: F405

REDIS_URL = env("REDIS_URL", "")
if env_bool("USE_REDIS", bool(REDIS_URL)):
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": env("CACHE_REDIS_URL", "redis://redis:6379/2"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 3,
                "SOCKET_TIMEOUT": 3,
                "IGNORE_EXCEPTIONS": False,
            },
            "KEY_PREFIX": "incident-intelligence-dev",
            "TIMEOUT": ANALYTICS_CACHE_TTL,  # noqa: F405
        }
    }
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [env("CHANNEL_REDIS_URL", "redis://redis:6379/0")],
                "capacity": env_int("CHANNEL_CAPACITY", 1500),
                "expiry": env_int("CHANNEL_EXPIRY_SECONDS", 60),
            },
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    ASYNC_DATASET_IMPORTS = False

if env_bool("ENABLE_DEBUG_TOOLBAR", True):
    INSTALLED_APPS += ["debug_toolbar", "django_extensions"]  # noqa: F405
    MIDDLEWARE.insert(2, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
        "RESULTS_CACHE_SIZE": 100,
        "SQL_WARNING_THRESHOLD": 250,
    }

TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG  # noqa: F405

if env_bool("USE_MAILPIT", False):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", "mailpit")
    EMAIL_PORT = env_int("EMAIL_PORT", 1025)
    EMAIL_USE_TLS = False
    EMAIL_USE_SSL = False
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Development diagnostics should be readable in the terminal by default.
LOGGING["handlers"]["console"]["formatter"] = "json" if env_bool("JSON_LOGS", False) else "console"  # noqa: F405
