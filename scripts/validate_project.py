#!/usr/bin/env python3
"""Dependency-free structural validation for CI and offline development."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def fail(message: str) -> None:
    ERRORS.append(message)


def validate_python() -> None:
    roots = (ROOT / "cctv_analytics", ROOT / "platform_core", ROOT / "incidents", ROOT / "scripts")
    for root in roots:
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                fail(f"Python syntax error in {path.relative_to(ROOT)}: {exc}")


def validate_templates() -> None:
    url_text = (ROOT / "incidents" / "urls.py").read_text(encoding="utf-8")
    names = set(re.findall(r'name="([^"]+)"', url_text))
    for path in (ROOT / "incidents" / "templates").rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        opens = len(re.findall(r"{%\s*block\b", text))
        closes = len(re.findall(r"{%\s*endblock\b", text))
        if opens != closes:
            fail(f"Template block mismatch in {path.relative_to(ROOT)}: {opens}/{closes}")
        for name in re.findall(r"{%\s*url\s+['\"]incidents:([^'\"]+)", text):
            if name not in names:
                fail(f"Unknown URL name incidents:{name} in {path.relative_to(ROOT)}")


def compose_service_blocks(text: str) -> dict[str, str]:
    services_match = re.search(r"(?ms)^services:\s*\n(?P<body>.*?)(?=^volumes:\s*$)", text)
    if not services_match:
        fail("docker-compose.yml does not contain a parseable services section")
        return {}
    body = services_match.group("body")
    matches = list(re.finditer(r"(?m)^  ([a-zA-Z0-9_-]+):\s*$", body))
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        blocks[match.group(1)] = body[start:end]
    return blocks


def validate_compose_profiles() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    blocks = compose_service_blocks(compose)

    default_services = {"db", "redis", "web", "worker"}
    optional_profiles = {
        "nginx": "edge",
        "beat": "scheduled",
        "worker-imports": "workers",
        "worker-analytics": "workers",
        "minio": "storage",
        "minio-init": "storage",
        "mailpit": "mail",
        "adminer": "db-tools",
        "flower": "monitoring",
        "postgres-exporter": "monitoring",
        "redis-exporter": "monitoring",
        "prometheus": "monitoring",
        "grafana": "monitoring",
        "backup": "ops",
    }

    for service in default_services:
        block = blocks.get(service)
        if block is None:
            fail(f"Default development service is missing: {service}")
        elif "profiles:" in block:
            fail(f"Default service {service} must not require a Compose profile")

    for service, profile in optional_profiles.items():
        block = blocks.get(service)
        if block is None:
            fail(f"Optional development service is missing: {service}")
        elif not re.search(rf'profiles:\s*\[\s*"{re.escape(profile)}"\s*\]', block):
            fail(f"Service {service} must use profile {profile}")

    unexpected_defaults = {
        name for name, block in blocks.items() if "profiles:" not in block and name not in default_services
    }
    if unexpected_defaults:
        fail(f"Unexpected services start by default: {', '.join(sorted(unexpected_defaults))}")


def validate_architecture() -> None:
    required = (
        "cctv_analytics/settings/base.py",
        "cctv_analytics/settings/development.py",
        "cctv_analytics/settings/production.py",
        "cctv_analytics/settings/test.py",
        "cctv_analytics/celery.py",
        "platform_core/views.py",
        "incidents/tasks.py",
        "deploy/nginx/default.conf",
        "deploy/monitoring/prometheus.yml",
        "deploy/monitoring/grafana/provisioning/datasources/prometheus.yml",
        "docker-compose.yml",
        "docker-compose.prod.yml",
        ".pre-commit-config.yaml",
        ".vscode/tasks.json",
        ".github/workflows/ci.yml",
        "docs/architecture/TECHNICAL_ARCHITECTURE.md",
        "docs/architecture/DEVELOPMENT_PROFILES.md",
        "scripts/dev-web.sh",
        "scripts/dev-worker.sh",
        "scripts/dev-scaled-workers.ps1",
    )
    for relative in required:
        if not (ROOT / relative).exists():
            fail(f"Required architecture file is missing: {relative}")

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    for target in ("development", "runtime"):
        if not re.search(rf"(?m)^FROM\s+\S+\s+AS\s+{target}\s*$", dockerfile):
            fail(f"Dockerfile target is missing: {target}")

    forbidden = (
        "django.contrib.gis",
        "PointField",
        "postgis/postgis",
        "django.contrib.postgres.gis",
    )
    scan_roots = (
        ROOT / "cctv_analytics",
        ROOT / "platform_core",
        ROOT / "incidents",
        ROOT / "docker-compose.yml",
        ROOT / "docker-compose.prod.yml",
    )
    for item in scan_roots:
        paths = [item] if item.is_file() else item.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix not in {".py", ".yml", ".yaml"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in forbidden:
                if token in text:
                    fail(f"PostGIS/GIS token {token!r} found in {path.relative_to(ROOT)}")

    if (ROOT / "cctv_analytics" / "settings.py").exists():
        fail("Legacy monolithic cctv_analytics/settings.py must not exist")

    validate_compose_profiles()



def validate_gis_contract() -> None:
    analytics_path = ROOT / "incidents" / "services" / "analytics.py"
    categories_path = ROOT / "incidents" / "services" / "categories.py"
    urls_path = ROOT / "incidents" / "urls.py"
    template_path = ROOT / "incidents" / "templates" / "incidents" / "map_analytics_report.html"
    map_js_path = ROOT / "incidents" / "static" / "incidents" / "js" / "map-report.js"
    colours_js_path = ROOT / "incidents" / "static" / "incidents" / "js" / "map-colors.js"

    for required in (analytics_path, categories_path, urls_path, template_path, map_js_path, colours_js_path):
        if not required.exists():
            fail(f"Required GIS contract file is missing: {required.relative_to(ROOT)}")
            return

    analytics_text = analytics_path.read_text(encoding="utf-8")
    analytics_tree = ast.parse(analytics_text)
    analytics_functions = {
        node.name for node in analytics_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if len(analytics_functions) < 37:
        fail(f"Analytics service function count regressed below 37: {len(analytics_functions)}")
    for name in (
        "with_analytical_category", "filtered_incidents", "map_points_payload",
        "map_report_payload", "location_intelligence_payload", "dashboard_payload",
        "station_profile_payload", "category_profile_payload",
    ):
        if name not in analytics_functions:
            fail(f"Required analytics service function is missing: {name}")

    categories_text = categories_path.read_text(encoding="utf-8")
    for token in ("resolve_category", "category_colour_key", "category_colour", "UNCATEGORISED_LABEL"):
        if token not in categories_text:
            fail(f"Shared Category service is missing token: {token}")

    urls_text = urls_path.read_text(encoding="utf-8")
    for route in ('analytics/map-report/', 'analytics/locations/', 'api/v1/analytics/map-points/'):
        if route not in urls_text:
            fail(f"Backward-compatible GIS route is missing: {route}")

    template_text = template_path.read_text(encoding="utf-8")
    for section_id in (
        "overall-distribution", "category-layers", "category-comparison",
        "repeat-locations", "coordinate-quality", "conclusion",
    ):
        if f'id="{section_id}"' not in template_text:
            fail(f"GIS report section is missing: {section_id}")

    map_js_text = map_js_path.read_text(encoding="utf-8")
    for token in (
        "data-category-mode", "categoryHeat", "fullscreenCategoryMap",
        "copy-coordinate", "openstreetmap.org", "Case Nature", "Data source",
    ):
        if token not in map_js_text and token not in template_text:
            fail(f"Focused Category map capability is missing: {token}")

    colours_js_text = colours_js_path.read_text(encoding="utf-8")
    for token in ("stableHash", "keyFor", "colorFor"):
        if token not in colours_js_text:
            fail(f"Deterministic map colour capability is missing: {token}")

def main() -> int:
    validate_python()
    validate_templates()
    validate_architecture()
    validate_gis_contract()
    if ERRORS:
        for error in ERRORS:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Project structure validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
