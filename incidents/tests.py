import json
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils.datastructures import MultiValueDict

from .forms import DatasetBulkUploadForm
from .models import DatasetUpload, Incident
from .services.importer import detect_source_type, import_csv


CSV_HEADER = (
    "Event Instruction ID,Reporting Time,Incident Location,Case Nature,Category,Sub-Category,"
    "Reporting Type,Contact Name,Contact No.,Description,Governing Branch,Police Station,"
    "Create Room,Feedback Content,Processing Result,Event Status,X Coordinate,Y Coordinate\n"
)


def csv_content(title: str, event_id: str) -> bytes:
    return (
        f"{title},,,,,,,,,,,,,,,,,\n"
        + CSV_HEADER
        + f"{event_id},12/05/2024 09:21,Kampala,Fire,Male Fire,,Call,,,,COMMAND CENTER,Central,,,,Accepted,32.58,0.31\n"
    ).encode("utf-8")


class CsvImportTests(TestCase):
    def test_source_detection_supports_numbered_filenames(self):
        self.assertEqual(detect_source_type("FIRE-INCIDENTS-2020-2024(2).csv"), Incident.SourceType.FIRE)
        self.assertEqual(detect_source_type("GENERAL-CRIME-2020-2024(2).csv"), Incident.SourceType.CRIME)
        self.assertEqual(detect_source_type("TRAFFIC-INCIDENTS-2020-2024(2).csv"), Incident.SourceType.TRAFFIC)

    def test_operational_area_aliases_normalize_to_command_center(self):
        from .services.normalization import normalize_operational_area

        for label in ("COMMAND CENTER", "command centre", "  CONTROL   ROOM  ", "Headquarters"):
            self.assertEqual(normalize_operational_area(label), "Command Center")

    def test_importer_handles_title_row(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "FIRE-INCIDENTS.csv"
            path.write_bytes(csv_content("FIRE INCIDENTS REPORT", "EVT-001"))
            result = import_csv(path)
        self.assertEqual(result.imported, 1)
        incident = Incident.objects.get(event_id="EVT-001")
        self.assertEqual(incident.source_type, Incident.SourceType.FIRE)
        self.assertAlmostEqual(incident.longitude, 32.58)

    def test_bulk_upload_form_accepts_three_csv_files(self):
        files = MultiValueDict(
            {
                "files": [
                    SimpleUploadedFile("FIRE-INCIDENTS-2020-2024(2).csv", csv_content("FIRE", "F-1")),
                    SimpleUploadedFile("GENERAL-CRIME-2020-2024(2).csv", csv_content("CRIME", "C-1")),
                    SimpleUploadedFile("TRAFFIC-INCIDENTS-2020-2024(2).csv", csv_content("TRAFFIC", "T-1")),
                ]
            }
        )
        form = DatasetBulkUploadForm(data={"incident_type": "AUTO"}, files=files)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["files"]), 3)

    def test_bundled_import_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            data_dir = Path(folder)
            (data_dir / "FIRE-INCIDENTS-2020-2024.csv").write_bytes(csv_content("FIRE", "F-1"))
            (data_dir / "GENERAL-CRIME-2020-2024.csv").write_bytes(csv_content("CRIME", "C-1"))
            (data_dir / "TRAFFIC-INCIDENTS-2020-2024.csv").write_bytes(csv_content("TRAFFIC", "T-1"))
            call_command("import_bundled_datasets", data_dir=str(data_dir))
            call_command("import_bundled_datasets", data_dir=str(data_dir))

        self.assertEqual(Incident.objects.count(), 3)
        self.assertEqual(DatasetUpload.objects.filter(import_method="BUNDLED").count(), 3)


@override_settings(INGEST_API_TOKEN="test-token")
class IngestApiTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_ingest_requires_token(self):
        response = self.client.post(
            "/api/v1/incidents/ingest/",
            data=json.dumps({"camera_id": "CAM-1"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_cctv_event_is_created(self):
        response = self.client.post(
            "/api/v1/incidents/ingest/",
            data=json.dumps(
                {
                    "event_id": "CCTV-001",
                    "source_type": "CCTV",
                    "camera_id": "CAM-1",
                    "detection_label": "vehicle collision",
                    "confidence": 0.91,
                    "longitude": 32.58,
                    "latitude": 0.31,
                }
            ),
            content_type="application/json",
            HTTP_X_INGEST_TOKEN="test-token",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Incident.objects.filter(event_id="CCTV-001", source_type="CCTV").exists())

    def test_same_producer_retry_is_idempotent(self):
        payload = {"event_id": "RETRY-001", "source_type": "CCTV", "camera_id": "CAM-1"}
        for _ in range(2):
            response = self.client.post(
                "/api/v1/incidents/ingest/",
                data=json.dumps(payload),
                content_type="application/json",
                HTTP_X_INGEST_TOKEN="test-token",
                HTTP_X_PRODUCER_ID="VMS-A",
            )
            self.assertEqual(response.status_code, 201)
        self.assertEqual(Incident.objects.filter(event_id="RETRY-001", producer_id="VMS-A").count(), 1)

    def test_different_producers_can_reuse_event_id(self):
        payload = {"event_id": "SHARED-001", "source_type": "CCTV"}
        for producer in ("VMS-A", "VMS-B"):
            response = self.client.post(
                "/api/v1/incidents/ingest/",
                data=json.dumps(payload),
                content_type="application/json",
                HTTP_X_INGEST_TOKEN="test-token",
                HTTP_X_PRODUCER_ID=producer,
            )
            self.assertEqual(response.status_code, 201)
        self.assertEqual(Incident.objects.filter(event_id="SHARED-001").count(), 2)

    def test_ingest_groups_command_center_as_command_center(self):
        response = self.client.post(
            "/api/v1/incidents/ingest/",
            data=json.dumps(
                {
                    "event_id": "CCTV-HQ-001",
                    "source_type": "CCTV",
                    "police_station": "CONTROL ROOM",
                }
            ),
            content_type="application/json",
            HTTP_X_INGEST_TOKEN="test-token",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            Incident.objects.get(event_id="CCTV-HQ-001").police_station,
            "Command Center",
        )




class AnalyticsDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()
        records = [
            ("C-001", "Mukono", "Thefts", now - timedelta(days=40), "Command Center"),
            ("C-002", "Mukono", "Thefts", now - timedelta(days=10), "Command Center"),
            ("C-003", "Wakiso", "Assaults", now, "Wakiso"),
            ("C-004", "COMMAND CENTER", "Thefts", now, "CONTROL ROOM"),
        ]
        for event_id, station, category, reported_at, branch in records:
            Incident.objects.create(
                event_id=event_id,
                source_type=Incident.SourceType.CRIME,
                origin=Incident.Origin.UPLOAD,
                reported_at=reported_at,
                police_station=station,
                governing_branch=branch,
                category=category,
                event_status="Accepted",
                longitude=32.58,
                latitude=0.31,
            )

    def test_manual_capture_route_is_removed(self):
        self.assertEqual(self.client.get("/incidents/create/").status_code, 404)

    def test_home_page_is_unified_command_dashboard(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Current Reported Incidents")
        self.assertContains(response, "Operational incident map")
        self.assertContains(response, "Focused workspaces")
        self.assertNotContains(response, "Open operations dashboard")

    def test_legacy_dashboard_redirects_to_home(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    def test_simplified_operational_pages_are_available(self):
        pages = {
            "/live/": "Live CCTV and Streaming Events",
            "/analytics/hotspots-patterns/": "Hotspots and Incident Patterns",
            "/analytics/operations-outcomes/": "Operations and Outcome Intelligence",
            "/analytics/data-quality/": "Data Quality Monitoring",
            "/analytics/map-report/": "GIS Map Analytics Report",
            "/analytics/predictive/": "Predictive and Anomaly Intelligence",
        }
        for url, text in pages.items():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertContains(response, text)

        legacy_map = self.client.get("/analytics/locations/")
        self.assertEqual(legacy_map.status_code, 302)
        self.assertEqual(legacy_map.url, "/analytics/map-report/")

    def test_gis_map_report_is_organised_into_operational_sections(self):
        response = self.client.get("/analytics/map-report/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overall Incident Distribution")
        self.assertContains(response, "Category Map Layers")
        self.assertContains(response, "Complete Category map atlas")
        self.assertContains(response, "Repeat Locations and Category Concentration")
        self.assertContains(response, "What the Map Can and Cannot Represent")
        self.assertContains(response, "How to Use the Map Analytics")
        self.assertContains(response, 'data-category-mode="heat"')
        self.assertContains(response, 'id="fullscreenCategoryMap"')

    def test_map_report_payload_reconciles_category_coordinate_coverage(self):
        from .services.analytics import map_report_payload

        from django.utils import timezone

        Incident.objects.create(
            event_id="UNMAPPED-1", source_type=Incident.SourceType.CRIME,
            reported_at=timezone.now(), category="Thefts", police_station="Mukono",
            longitude=None, latitude=None,
        )
        payload = map_report_payload(Incident.objects.all(), include_map=False)
        theft = next(row for row in payload["category_layers"] if row["category"] == "Thefts")
        self.assertEqual(theft["total"], 4)
        self.assertEqual(theft["mapped"], 3)
        self.assertEqual(theft["unmapped"], 1)
        self.assertIn("priority_layers", payload)
        self.assertIn("category_coverage", payload)
        self.assertIn("coordinate_quality", payload)
        self.assertEqual(payload["coordinate_quality"]["valid"], 4)
        self.assertEqual(payload["coordinate_quality"]["missing_both"], 1)
        self.assertIn("category_colour", theft)
        self.assertIn("category_key", theft)

    def test_legacy_analytics_pages_redirect_to_consolidated_pages(self):
        hotspot_routes = [
            "/analytics/areas-categories/",
            "/analytics/categories-time/",
            "/analytics/time-patterns/",
        ]
        for url in hotspot_routes:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertEqual(response.url, "/analytics/hotspots-patterns/")

        operations_routes = [
            "/analytics/command-center/",
            "/analytics/dispatch/",
            "/analytics/status-outcomes/",
        ]
        for url in operations_routes:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertEqual(response.url, "/analytics/operations-outcomes/")

    def test_station_and_category_profiles_are_available(self):
        self.assertEqual(self.client.get("/analytics/stations/Mukono/").status_code, 200)
        self.assertEqual(self.client.get("/analytics/categories/Thefts/").status_code, 200)

    def test_exports_are_available(self):
        csv_response = self.client.get("/incidents/export/csv/")
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(csv_response["Content-Type"], "text/csv")
        xlsx_response = self.client.get("/incidents/export/xlsx/")
        self.assertEqual(xlsx_response.status_code, 200)
        self.assertIn("spreadsheetml", xlsx_response["Content-Type"])

    def test_command_center_aliases_are_grouped(self):
        from .services.analytics import dashboard_payload

        payload = dashboard_payload(Incident.objects.all())
        hotspot_names = [row["police_station"] for row in payload["by_hotspot"]]
        self.assertNotIn("COMMAND CENTER", hotspot_names)
        self.assertIn("Command Center", hotspot_names)
        command_center = next(row for row in payload["by_hotspot"] if row["police_station"] == "Command Center")
        self.assertEqual(command_center["total"], 1)
        self.assertIn("time_patterns", payload)
        self.assertIn("insights", payload)


class DecisionSupportAnalyticsTests(TestCase):
    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone

        latest = timezone.now()
        for index, days in enumerate((0, 2, 8, 31, 45, 61, 92)):
            Incident.objects.create(
                event_id=f"DS-{index}",
                source_type=Incident.SourceType.CRIME,
                reported_at=latest - timedelta(days=days),
                category="Theft" if index < 4 else "Assault",
                police_station="Mukono" if index % 2 == 0 else "Wakiso",
                event_status="Accepted",
                longitude=32.5,
                latitude=0.3,
            )

    def test_dashboard_contains_dataset_relative_decision_support(self):
        from .services.analytics import dashboard_payload

        payload = dashboard_payload(Incident.objects.all())
        decision = payload["decision_support"]
        self.assertIn("current_30", decision)
        self.assertIn("previous_30", decision)
        self.assertEqual(len(decision["aging"]), 5)
        self.assertTrue(decision["daily_labels"])
        self.assertIn("station_pareto", __import__("incidents.services.analytics", fromlist=["area_category_payload"]).area_category_payload(Incident.objects.all()))


class AnalyticsSnapshotTests(TestCase):
    def test_refresh_snapshot_task_persists_dashboard_payload(self):
        from .models import AnalyticsSnapshot
        from .tasks import refresh_analytics_snapshots

        refresh_analytics_snapshots()
        self.assertTrue(AnalyticsSnapshot.objects.filter(key__startswith="dashboard-default:v6-gis-map-report").exists())
