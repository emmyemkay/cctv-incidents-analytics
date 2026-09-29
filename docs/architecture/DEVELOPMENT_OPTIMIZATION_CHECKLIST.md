# Development Optimization Checklist

## Fast default loop

- [x] Only four services start by default
- [x] PostgreSQL and Redis use non-conflicting host ports
- [x] Python source is bind-mounted
- [x] Daphne reloads when Python changes
- [x] Celery reloads when Python changes
- [x] Template, CSS and JavaScript changes do not require an image rebuild
- [x] Migrations and initial development setup are automatic and idempotent

## Debugging and inspection

- [x] Django Debug Toolbar
- [x] Django Extensions and `shell_plus`
- [x] Mailpit email capture profile
- [x] Adminer database-inspection profile
- [x] Flower worker-inspection profile
- [x] Prometheus and Grafana profile
- [x] PostgreSQL and Redis exporters
- [x] Health and readiness endpoints

## Quality and consistency

- [x] Development and runtime Docker targets
- [x] Production Compose file separated from development conveniences
- [x] Pytest factories and fixtures
- [x] Ruff, MyPy, Bandit and dependency-audit dependencies
- [x] Pre-commit configuration
- [x] CI validation for default and optional profiles
- [x] VS Code tasks and Dev Container configuration
- [x] Architecture validation script

## Intentional exclusions

- [x] No PostGIS
- [x] No Kafka
- [x] No Spark
- [x] No Kubernetes requirement for local development

The remaining work before claiming complete production readiness is environment-specific: live Docker execution, load testing, backup restoration, security review and deployment validation on the target infrastructure.
