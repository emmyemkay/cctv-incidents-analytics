#!/bin/sh
set -eu

python /app/scripts/wait_for_services.py db:5432 redis:6379
NAME="${CELERY_WORKER_NAME:-worker}"
QUEUES="${CELERY_WORKER_QUEUES:-default,celery}"
CONCURRENCY="${CELERY_WORKER_CONCURRENCY:-1}"

exec watchfiles --filter python \
  "celery -A cctv_analytics worker -n ${NAME}@%h -Q ${QUEUES} --loglevel=INFO --concurrency=${CONCURRENCY}" \
  /app/cctv_analytics /app/platform_core /app/incidents
