from django.core.management.base import BaseCommand

from incidents.tasks import refresh_analytics_snapshots, run_data_quality_audit


class Command(BaseCommand):
    help = "Build durable dashboard and data-quality analytics snapshots."

    def handle(self, *args, **options):
        dashboard = refresh_analytics_snapshots()
        quality = run_data_quality_audit()
        self.stdout.write(self.style.SUCCESS(f"Analytics snapshots refreshed: {dashboard}; {quality}"))
