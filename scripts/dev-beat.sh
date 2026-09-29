#!/bin/sh
set -eu

python /app/scripts/wait_for_services.py db:5432 redis:6379
exec celery -A cctv_analytics beat \
  --loglevel=INFO \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler \
  --pidfile=/tmp/celerybeat.pid
