# Technical Architecture

## Design target

The platform uses one codebase with separate development, test and production execution paths. Development remains production-shaped by using PostgreSQL, Redis, Daphne, Channels and Celery, but optional infrastructure is excluded from the default startup to reduce resource usage and debugging complexity.

PostGIS is deliberately not included in this release.

## Default development topology

```text
Browser / API producer
         |
         v
Django + Daphne
HTTP, WebSockets, API, templates
         |
   +-----+----------+
   |                |
   v                v
PostgreSQL        Redis
system record     channels/cache/broker
                      |
                      v
             One Celery worker
       imports + analytics + default
```

The `web` process owns development initialization. It waits for PostgreSQL and Redis, applies migrations, seeds roles, collects static files, performs the idempotent bundled-data import, validates the application and then starts Daphne under `watchfiles`.

The default worker also runs under `watchfiles`, so Python changes restart both long-running development processes.

## Optional development profiles

```text
edge        -> Nginx
scheduled   -> Celery Beat
workers     -> dedicated import and analytics workers
storage     -> MinIO and bucket initializer
mail        -> Mailpit
DB tools    -> Adminer
monitoring  -> Flower, Prometheus, Grafana and database/cache exporters
ops         -> PostgreSQL backup job
```

Optional profiles allow realistic integration testing without making every developer run all services continuously.

## Production topology

The standalone `docker-compose.prod.yml` intentionally differs from development:

```text
Nginx
  |
  v
Django + Daphne
  |
  +--> PostgreSQL
  +--> Redis
  +--> dedicated import worker
  +--> dedicated analytics worker
  +--> Celery Beat
```

Production uses a one-shot migration service, the non-development runtime target, no source bind mounts and strict production settings.

## Container targets

| Target | Purpose |
|---|---|
| `development` | Includes test, lint, debugging, auto-reload and Flower dependencies |
| `runtime` | Includes only application runtime dependencies and runs as a non-root user |

Both targets use the same Python version and base runtime libraries, reducing environment drift.

## Configuration boundaries

```text
cctv_analytics/settings/
  base.py          shared application, Celery, logging and storage settings
  development.py   PostgreSQL/Redis development settings and developer tooling
  production.py    strict secrets, HTTPS and production database settings
  test.py          deterministic test configuration
```

## Application boundaries

```text
platform_core/
  request IDs
  structured logging
  health endpoints
  environment checks

incidents/
  incident and upload models
  ingestion API
  analytics selectors and services
  background tasks
  normalization/import pipeline
  WebSocket consumers
  durable analytics snapshots
```

The platform remains a modular monolith. This is the correct development trade-off until deployment scale justifies extracting independent services.

## Data architecture

- PostgreSQL is authoritative.
- Redis is transient and split logically across Channels, Celery and caching.
- Local media storage is the default.
- MinIO can be activated to test the S3-compatible storage path.
- Analytics snapshots provide a durable fallback for selected expensive payloads.
- Map payloads are bounded and lazy-loaded.
- Coordinates remain ordinary longitude and latitude columns.

## Ingestion path

### Uploaded datasets

```text
Upload
  -> DatasetUpload record
  -> imports queue
  -> validation and normalization
  -> bulk insert
  -> rejection/error accounting
  -> cache invalidation
  -> progress state update
```

### Live producers

```text
Producer
  -> token and rate-limit validation
  -> producer-aware idempotency
  -> database transaction
  -> cache invalidation
  -> WebSocket broadcast after commit
```

## Developer-experience controls

- Bind-mounted source tree
- `watchfiles` restart loop for Daphne and Celery
- Debug Toolbar and `shell_plus`
- VS Code tasks and extension recommendations
- Mailpit for safe email inspection
- Adminer for database inspection
- Flower for Celery inspection
- Prometheus and Grafana for metrics
- Pre-commit checks and CI parity
- Separate helper scripts for combined and dedicated workers

## Reliability and security controls

- PostgreSQL and Redis health checks
- Application liveness and readiness endpoints
- Worker health checks
- Request IDs and request-duration logging
- Non-root runtime target
- Production secret validation
- Bounded task time limits and worker recycling
- Object-storage abstraction
- Streaming exports
- Controlled production migration job

## Deferred capabilities

- PostGIS
- Kafka
- Spark
- Kubernetes manifests
- Multi-node PostgreSQL and Redis high availability
- External identity provider

These are deployment-scale decisions, not requirements for a high-quality development architecture.
