# Development Profiles

The default development topology deliberately starts only four services:

```text
Django/Daphne + PostgreSQL + Redis + one Celery worker
```

This is the fastest setup that still exercises the real ASGI, WebSocket, database, caching and asynchronous-processing paths.

## Core profile: default

```powershell
docker compose up -d --build
```

Services:

| Service | Purpose | Host access |
|---|---|---|
| `web` | Django ASGI through Daphne with Python auto-reload | `http://127.0.0.1:8001` |
| `db` | Standard PostgreSQL 17 | `127.0.0.1:5433` |
| `redis` | Channels, Celery broker and cache using logical databases | `127.0.0.1:6380` |
| `worker` | One auto-reloading Celery worker consuming all development queues | internal |

The web service runs migrations, seeds roles, collects static files and performs the idempotent bundled-data import before starting Daphne.

## Optional profile catalogue

| Profile | Services | Purpose |
|---|---|---|
| `edge` | `nginx` | Validate reverse proxy, WebSocket headers, static/media routing and upload limits |
| `scheduled` | `beat` | Run periodic analytics and data-quality jobs |
| `workers` | `worker-imports`, `worker-analytics` | Test isolated queue routing and worker scaling |
| `storage` | `minio`, `minio-init` | Exercise S3-compatible object storage |
| `mail` | `mailpit` | Capture development email without sending externally |
| `db-tools` | `adminer` | Inspect PostgreSQL through a browser |
| `monitoring` | `flower`, `postgres-exporter`, `redis-exporter`, `prometheus`, `grafana` | Inspect Celery, metrics and dashboards |
| `ops` | `backup` | Create a PostgreSQL dump in `backups/` |

## Start selected profiles

```powershell
docker compose --profile edge up -d nginx
docker compose --profile scheduled up -d beat
docker compose --profile mail up -d mailpit
docker compose --profile storage up -d minio minio-init
docker compose --profile db-tools up -d adminer
docker compose --profile monitoring up -d flower prometheus grafana
```

## Dedicated workers

Do not run the combined `worker` and dedicated workers simultaneously during normal development because they consume the same queues.

Switch to dedicated workers:

```powershell
.\scripts\dev-scaled-workers.ps1
```

Return to the default worker:

```powershell
.\scripts\dev-default-worker.ps1
```

## Full integration environment

```powershell
.\scripts\dev-full.ps1
```

This starts all optional infrastructure except the dedicated worker profile. The combined worker remains active. Mailpit and MinIO are available, but the application remains on console email and local media until `dev-mailpit.ps1` or `dev-minio.ps1` is run.

## Optional-service URLs

| Tool | URL |
|---|---|
| Nginx | `http://127.0.0.1:8080` |
| Mailpit | `http://127.0.0.1:8025` |
| Adminer | `http://127.0.0.1:8081` |
| Flower | `http://127.0.0.1:5555` |
| Prometheus | `http://127.0.0.1:9090` |
| Grafana | `http://127.0.0.1:3000` |
| MinIO console | `http://127.0.0.1:9001` |

PostGIS is not part of any profile.
