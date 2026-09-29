#!/bin/sh
set -eu

python /app/scripts/wait_for_services.py db:5432 redis:6379
python manage.py migrate --noinput
python manage.py seed_roles
python manage.py collectstatic --noinput

if [ "${AUTO_IMPORT_DATASETS:-1}" = "1" ]; then
  python manage.py import_bundled_datasets || echo "WARNING: bundled dataset import failed; review the web logs."
fi

python manage.py check
python manage.py shell -c "from incidents.tasks import refresh_analytics_snapshots; refresh_analytics_snapshots.delay()" || true

exec watchfiles --filter python \
  "daphne -b 0.0.0.0 -p 8000 cctv_analytics.asgi:application" \
  /app/cctv_analytics /app/platform_core /app/incidents
