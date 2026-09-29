FROM python:3.12-slim AS base-builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements/base.txt requirements/base.txt
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/pip install -r requirements/base.txt

FROM base-builder AS development-builder
COPY requirements/dev.txt requirements/dev.txt
RUN /opt/venv/bin/pip install -r requirements/dev.txt

FROM python:3.12-slim AS runtime-base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=cctv_analytics.settings.development
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl tini netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /bin/bash app \
    && mkdir -p /app/media /app/staticfiles /app/.cache \
    && chown -R app:app /app /home/app
ENTRYPOINT ["/usr/bin/tini", "--", "/app/scripts/entrypoint.sh"]
EXPOSE 8000

FROM runtime-base AS development
COPY --from=development-builder /opt/venv /opt/venv
COPY --chown=app:app . /app
RUN chmod +x /app/scripts/*.sh && chown -R app:app /app
USER app
CMD ["sh", "/app/scripts/dev-web.sh"]

FROM runtime-base AS runtime
ENV DJANGO_SETTINGS_MODULE=cctv_analytics.settings.production
COPY --from=base-builder /opt/venv /opt/venv
COPY --chown=app:app . /app
RUN chmod +x /app/scripts/*.sh && chown -R app:app /app
USER app
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "cctv_analytics.asgi:application"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD curl -fsS http://127.0.0.1:8000/health/live/ || exit 1
