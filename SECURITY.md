# Security Policy

## Supported configuration

Only deployments using `cctv_analytics.settings.production`, PostgreSQL, Redis, HTTPS and changed secrets are considered production configurations. SQLite and the in-memory Channels layer are development-only options.

## Reporting a vulnerability

Report security issues privately to the platform owner or designated security team. Include the affected route or component, reproduction steps, impact and any relevant request ID. Do not include real incident or personal data in a public issue.

## Baseline controls

- Store secrets outside source control.
- Rotate `DJANGO_SECRET_KEY`, database credentials and `INGEST_API_TOKEN` before deployment.
- Restrict PostgreSQL, Redis, metrics and object-storage administration ports to private networks.
- Enable authentication and RBAC in production.
- Terminate TLS at Nginx or the platform ingress.
- Keep dependency, container and operating-system patches current.
- Back up PostgreSQL and verify restoration regularly.
- Limit and audit data exports.
