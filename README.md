# Operational Incident Intelligence Platform

A development-optimized Django ASGI platform for Fire, General Crime, Traffic and real-time CCTV incident intelligence. The architecture is designed to remain close to production while keeping the normal developer startup fast and understandable.

PostGIS is intentionally excluded. Coordinates remain validated longitude and latitude fields in standard PostgreSQL.

## Analytical Category Rule

Maps, filters, profiles, charts and exports use the name **Category**. The value comes from `Category` first, then `Sub-Category` only when Category is blank. When both are blank, the record is shown as `Uncategorised`. Case Nature remains reference data and does not control analytical grouping. See `docs/CATEGORY_ANALYTICS_RULE.md`.

## Default development topology

Running `docker compose up` starts only four services:

```text
Browser
  |
  v
Django + Daphne :8001
  |--------------------|
  v                    v
PostgreSQL           Redis
                         |
                         v
                One Celery worker
```

| Service | Development role |
|---|---|
| `web` | Django, Daphne, HTTP, WebSockets, API and dashboard rendering |
| `db` | PostgreSQL 17 system of record |
| `redis` | Channels, Celery broker and analytics cache using separate logical databases |
| `worker` | One Celery worker consuming import, analytics and default queues |

Python changes automatically restart Daphne and Celery through `watchfiles`. Source code is bind-mounted, so image rebuilding is unnecessary for normal Python, template, CSS and JavaScript changes.

## Optional Compose profiles

| Profile | Services | Purpose |
|---|---|---|
| `edge` | Nginx | Reverse-proxy and WebSocket validation |
| `scheduled` | Celery Beat | Scheduled analytics and quality jobs |
| `workers` | Dedicated import and analytics workers | Queue-isolation and scaling tests |
| `storage` | MinIO and bucket initializer | S3-compatible object-storage testing |
| `mail` | Mailpit | Safe development email capture |
| `db-tools` | Adminer | Browser-based PostgreSQL inspection |
| `monitoring` | Flower, Prometheus, Grafana and database/cache exporters | Worker and application observability |
| `ops` | PostgreSQL backup job | Development backup verification |

## First start

```powershell
Copy-Item .env.example .env
.\scripts\dev.ps1
```

Open:

```text
http://127.0.0.1:8001
```

The web bootstrap performs migrations, role seeding, static collection and the idempotent bundled-data import before starting Daphne.

## Full development environment

```powershell
.\scripts\dev-full.ps1
```

This starts all optional infrastructure except the dedicated worker profile. The single combined worker remains active.

Optional interfaces:

| Interface | Address |
|---|---|
| Nginx | `http://127.0.0.1:8080` |
| Mailpit | `http://127.0.0.1:8025` |
| Adminer | `http://127.0.0.1:8081` |
| Flower | `http://127.0.0.1:5555` |
| Prometheus | `http://127.0.0.1:9090` |
| Grafana | `http://127.0.0.1:3000` |
| MinIO console | `http://127.0.0.1:9001` |

## Worker modes

Default combined worker:

```powershell
.\scripts\dev-default-worker.ps1
```

Dedicated queue workers:

```powershell
.\scripts\dev-scaled-workers.ps1
```

The helper scripts prevent the combined and dedicated workers from unnecessarily consuming the same queues at the same time.

## Development features

- Split settings for development, test and production
- Django/Daphne ASGI and Redis-backed WebSockets
- PostgreSQL in normal development instead of SQLite
- One default auto-reloading Celery worker
- Optional dedicated workers and Celery Beat
- Optional Nginx, MinIO, Mailpit, Adminer, Flower, Prometheus, Grafana and database/cache exporters
- Django Debug Toolbar and Django Extensions in the development image
- Structured logging and request correlation
- Liveness, readiness and Prometheus metrics endpoints
- Producer-aware real-time ingestion idempotency
- Background dataset uploads and analytics snapshots
- Streaming CSV and memory-efficient Excel exports
- VS Code recommendations, tasks and native debug configuration
- Pre-commit hooks, Ruff, MyPy, Pytest, Bandit and dependency auditing
- Development and standalone production Docker targets

## Analytics retained and improved

The command overview keeps **Current Reported Incidents** first and includes:

- latest 30-day versus preceding-period movement;
- 90-day daily trends and seven-day rolling average;
- unresolved incident aging;
- category momentum;
- field-station workload concentration;
- category-coloured clustered maps and heatmaps;
- a structured six-section GIS Map Analytics Report with overall distribution, selectable Category layers, a complete Category atlas, repeat-location analysis, coordinate-quality interpretation and operational conclusions;
- points, heat and combined modes on both the main map and the focused Category map, with fit-to-visible and full-screen controls;
- complete incident popups with Category, Sub-Category, Case Nature reference data, station/profile links, source, coordinates, copy action and OpenStreetMap launch;
- deterministic server/browser Category colour identity included in map APIs, WebSocket messages and CSV/Excel exports;
- automatic WebSocket reconnection and idempotent live-marker replacement during repeated ingest updates;
- bounded lazy map loading for both the overall map and selected Category layers;
- specialist hotspot, time, outcomes, GIS map, prediction and data-quality pages.

## Included datasets

| Source | Records | Valid coordinate pairs |
|---|---:|---:|
| Fire | 1,763 | 688 |
| General crime | 29,294 | 10,452 |
| Traffic | 5,019 | 1,876 |
| **Total** | **36,076** | **13,016** |

## Daily commands

```powershell
docker compose up -d
docker compose logs -f web worker
docker compose exec web python manage.py check
docker compose exec web pytest
docker compose exec web python manage.py shell_plus
```

Code quality:

```powershell
docker compose exec web ruff check .
docker compose exec web ruff format --check .
docker compose exec web mypy cctv_analytics platform_core incidents
docker compose exec web bandit -r cctv_analytics platform_core incidents -x incidents/migrations
python scripts/validate_project.py
```

## Health and observability

| Endpoint | Purpose |
|---|---|
| `/health/live/` | Process liveness |
| `/health/ready/` | PostgreSQL, cache and Channels readiness |
| `/metrics/` | Prometheus-format Django metrics |
| `/__debug__/` | Development-only Django Debug Toolbar assets and panels |

## Real-time ingestion

```text
POST /api/v1/incidents/ingest/
X-Ingest-Token: <private token>
X-Producer-ID: <producer identifier>
```

The endpoint applies token validation, producer-aware idempotency, batch limits, atomic writes, cache invalidation and post-commit WebSocket broadcasts.

## Production validation

A standalone production Compose file is included so development conveniences do not leak into production:

```powershell
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Production uses the runtime image target, no source bind mount, dedicated Celery workers, one migration job, Celery Beat and Nginx.

Before deployment:

```powershell
docker compose -f docker-compose.prod.yml exec web python manage.py check --deploy
```

## Documentation

- `docs/CATEGORY_ANALYTICS_RULE.md`
- `docs/MAP_CATEGORY_COLOUR_RULES.md`
- `docs/GIS_MAP_ANALYTICS_REPORT.md`
- `docs/GIS_REPORT_COMPARISON.md`
- `docs/GIS_MAP_DATA_PROFILE.md`
- `docs/IMPROVEMENT_VALIDATION.md`
- `docs/architecture/DEVELOPMENT_PROFILES.md`
- `docs/architecture/DEVELOPMENT_WORKFLOW.md`
- `docs/architecture/DEVELOPMENT_OPTIMIZATION_CHECKLIST.md`
- `docs/architecture/TECHNICAL_ARCHITECTURE.md`
- `docs/architecture/ANALYTICS_MODEL.md`
- `docs/architecture/PRODUCTION_READINESS_CHECKLIST.md`

Do not run `docker compose down -v` unless deleting PostgreSQL, Redis, MinIO and monitoring volumes is intentional.

## Exact CSV Category coordinate map

The operational map plots every valid Uganda coordinate using the resolved CSV `Category` value. `Category` is used first, `Sub-Category` is used only when Category is blank, and `Uncategorised` is used only when both are blank.

The colour identity is the normalized Category name itself. Records with the same Category name always receive the same stable colour across CSV files, years, stations, filters and live updates. Case and harmless whitespace differences are normalized for colour consistency, while the displayed Category name remains unchanged.

Map behaviour:

- Every valid coordinate is plotted.
- Each distinct resolved Category receives its own deterministic colour.
- Identical Category names receive the same colour everywhere.
- Exact Category names remain separate in markers, filters, popups and the legend.
- Mixed-colour cluster rings summarize the exact Category composition inside a coordinate cluster.
- The legend lists each Category with its colour, mapped count and percentage.
- Administrators can search Categories, show all, select the top ten or clear the map.
- Points, heatmap and combined map modes are available on the overall and selected-Category maps.
- Fit-to-visible-coordinates and full-screen controls are available on both map surfaces.
- Map APIs and WebSocket events expose `map_category`, `category_key` and `category_colour` so every surface uses the same identity.
- CSV and Excel exports include the resolved Category colour key and map colour without replacing the visible Category field.
- The current 52 resolved bundled Category names generate 52 distinct colours without collision.
- The current valid coordinate records fit within the 50,000-point map payload.
- Invalid, zero and out-of-bound Uganda coordinates are excluded from the operational map and remain visible in Data Quality analysis.

See `docs/MAP_CATEGORY_COLOUR_RULES.md` for the exact colour-key rule.

## GIS Map Analytics Report

Open the organised report workspace at:

```text
http://127.0.0.1:8001/analytics/map-report/
```

The previous `/analytics/locations/` address remains a backward-compatible redirect to this report.

The page follows a report-style analytical sequence while remaining interactive:

1. Overall distribution of all valid incident coordinates.
2. Separate selectable Category map layers.
3. Mapped-versus-unmapped comparison and a complete Category map atlas.
4. Repeat-location and multi-Category hotspot analysis.
5. Coordinate-quality conclusions and operational use guidance.

The older `/analytics/locations/` address redirects to this organised report so saved bookmarks continue to work.
