from django.contrib import admin

from .models import AnalyticsSnapshot, DatasetUpload, Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("event_id", "producer_id", "source_type", "reported_at", "category", "police_station", "event_status")
    list_filter = ("source_type", "origin", "event_status", "reported_at")
    search_fields = ("event_id", "producer_id", "incident_location", "description", "police_station", "camera_id")
    date_hierarchy = "reported_at"
    list_per_page = 50


@admin.register(DatasetUpload)
class DatasetUploadAdmin(admin.ModelAdmin):
    list_display = (
        "original_name", "incident_type", "import_method", "status",
        "rows_imported", "rows_skipped", "uploaded_at", "completed_at",
    )
    list_filter = ("status", "incident_type", "import_method")
    search_fields = ("original_name", "file_hash", "task_id")
    readonly_fields = (
        "file_hash", "rows_seen", "rows_imported", "rows_skipped", "error_message",
        "task_id", "started_at", "completed_at",
    )


@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = ("key", "source_row_count", "latest_reported_at", "generated_at")
    readonly_fields = ("key", "payload", "source_row_count", "latest_reported_at", "generated_at")
