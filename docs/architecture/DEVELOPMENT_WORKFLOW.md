# Development Workflow

## First start

```powershell
Copy-Item .env.example .env
.\scripts\dev.ps1
```

Open `http://127.0.0.1:8001`.

The source tree is bind-mounted into the development containers. `watchfiles` restarts Daphne and the Celery worker when Python files change. Template, CSS and JavaScript changes are available immediately after refreshing the browser. Rebuild the image only after changing Python dependencies, the Dockerfile or operating-system packages.

## Daily commands

```powershell
docker compose up -d
docker compose logs -f web worker
docker compose ps
docker compose exec web python manage.py check
docker compose exec web pytest
docker compose exec web python manage.py shell_plus
```

## Database access

The development database is exposed at `127.0.0.1:5433` to avoid colliding with a locally installed PostgreSQL server. Redis is exposed at `127.0.0.1:6380` for the same reason.

Start Adminer:

```powershell
docker compose --profile db-tools up -d adminer
```

Open `http://127.0.0.1:8081` and use server `db`.

## Email testing

```powershell
.\scripts\dev-mailpit.ps1
```

Open `http://127.0.0.1:8025`. Messages are captured locally and are never sent to real recipients.

## Object-storage testing

```powershell
.\scripts\dev-minio.ps1
```

Open `http://127.0.0.1:9001`. The initialization container creates the configured bucket idempotently.

## Monitoring

```powershell
docker compose --profile monitoring up -d flower prometheus grafana
```

Django exposes `/metrics/`; Prometheus scrapes the web container; Grafana is provisioned with Prometheus as the default data source.

## Quality checks

```powershell
docker compose exec web ruff check .
docker compose exec web ruff format --check .
docker compose exec web mypy cctv_analytics platform_core incidents
docker compose exec web pytest
docker compose exec web bandit -r cctv_analytics platform_core incidents -x incidents/migrations
python scripts/validate_project.py
```

Install the pre-commit hooks for native development:

```powershell
pre-commit install
pre-commit run --all-files
```

## Safe shutdown

```powershell
docker compose down
```

Do not use `docker compose down -v` unless deleting PostgreSQL, Redis, MinIO and monitoring data is intentional.

See `DEVELOPMENT_PROFILES.md` for the complete profile catalogue.
