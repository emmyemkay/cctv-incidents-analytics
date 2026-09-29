#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py seed_roles
if [ "${AUTO_IMPORT_DATASETS:-1}" = "1" ]; then
  python manage.py import_bundled_datasets || echo "WARNING: bundled dataset import failed; review the migration service logs."
fi
python manage.py check
python manage.py shell -c "from incidents.tasks import refresh_analytics_snapshots; refresh_analytics_snapshots.delay()" || true
