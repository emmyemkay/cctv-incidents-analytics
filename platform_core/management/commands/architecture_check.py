from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Verify core development architecture dependencies and configuration."

    def handle(self, *args, **options):
        self.stdout.write(f"Environment: {settings.DEPLOYMENT_ENVIRONMENT}")
        self.stdout.write(f"Settings: {settings.SETTINGS_MODULE if hasattr(settings, 'SETTINGS_MODULE') else 'configured'}")
        self.stdout.write(f"Database engine: {connection.settings_dict['ENGINE']}")
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        self.stdout.write(self.style.SUCCESS("Database: ready"))
        cache.set("architecture-check", "ok", 10)
        if cache.get("architecture-check") != "ok":
            self.stderr.write(self.style.ERROR("Cache: failed"))
        else:
            self.stdout.write(self.style.SUCCESS("Cache: ready"))
        self.stdout.write(f"Channel backend: {settings.CHANNEL_LAYERS['default']['BACKEND']}")
        self.stdout.write(f"Celery broker: {settings.CELERY_BROKER_URL}")
        self.stdout.write(self.style.SUCCESS("Architecture check completed"))
