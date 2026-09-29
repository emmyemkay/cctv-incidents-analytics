from django.urls import path

from . import api, views

app_name = "incidents"
urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("live/", views.live_monitoring, name="live_monitoring"),
    path("analytics/hotspots-patterns/", views.hotspot_patterns, name="hotspot_patterns"),
    path("analytics/operations-outcomes/", views.operations_outcomes, name="operations_outcomes"),
    path("analytics/areas-categories/", views.area_category_analytics, name="area_category"),
    path("analytics/categories-time/", views.category_time_analytics, name="category_time"),
    path("analytics/time-patterns/", views.time_patterns, name="time_patterns"),
    path("analytics/command-center/", views.command_center_analysis, name="command_center"),
    path("analytics/dispatch/", views.dispatch_analysis, name="dispatch"),
    path("analytics/data-quality/", views.data_quality, name="data_quality"),
    path("analytics/status-outcomes/", views.status_outcomes, name="status_outcomes"),
    path("analytics/map-report/", views.map_analytics_report, name="map_report"),
    path("analytics/locations/", views.location_intelligence, name="location_intelligence"),
    path("analytics/predictive/", views.predictive_intelligence, name="predictive_intelligence"),
    path("analytics/stations/<path:station>/", views.station_profile, name="station_profile"),
    path("analytics/categories/<path:category>/", views.category_profile, name="category_profile"),
    path("analytics/case-natures/<path:category>/", views.category_profile, name="case_nature_profile_legacy"),
    path("incidents/", views.incident_list, name="incident_list"),
    path("incidents/export/csv/", views.export_incidents_csv, name="export_csv"),
    path("incidents/export/xlsx/", views.export_incidents_xlsx, name="export_xlsx"),
    path("reports/print/", views.printable_report, name="print_report"),
    path("datasets/upload/", views.upload_dataset, name="upload"),
    path("api/v1/incidents/ingest/", api.ingest_incidents, name="api_ingest"),
    path("api/v1/analytics/summary/", api.analytics_summary, name="api_analytics"),
    path("api/v1/analytics/map-points/", api.analytics_map_points, name="api_map_points"),
    path("api/v1/datasets/import-status/", api.import_status, name="api_import_status"),
]
