#!/bin/sh
set -eu

python /app/scripts/wait_for_services.py db:5432 redis:6379
QUEUES="${CELERY_DEV_QUEUES:-imports,analytics,default,celery}"
CONCURRENCY="${CELERY_DEV_CONCURRENCY:-2}"

exec watchfiles --filter python \
  "celery -A cctv_analytics worker -n celery@%h -Q ${QUEUES} --loglevel=INFO --concurrency=${CONCURRENCY}" \
  /app/cctv_analytics /app/platform_core /app/incidents
