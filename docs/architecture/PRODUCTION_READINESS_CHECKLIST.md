# Production Readiness Checklist

## Required before production

- Set `DJANGO_SETTINGS_MODULE=cctv_analytics.settings.production`.
- Generate a strong `DJANGO_SECRET_KEY`.
- Replace `INGEST_API_TOKEN` and rotate it through a secret manager.
- Configure real `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- Use strong PostgreSQL credentials and private networking.
- Configure TLS at the load balancer or Nginx.
- Set `DJANGO_SECURE_SSL_REDIRECT=1`.
- Run `python manage.py check --deploy`.
- Disable bundled auto-import.
- Configure external backups and test restoration.
- Configure log aggregation and Prometheus scraping.
- Configure S3/MinIO for persistent uploads where required.
- Run test, lint, dependency and container scans in CI.

## Intentionally not included

- PostGIS
- Kubernetes manifests
- Kafka brokers
- Spark jobs
- High-availability PostgreSQL orchestration

These are later scaling choices and are not prerequisites for a correct production-shaped application architecture.
