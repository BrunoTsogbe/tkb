# syntax=docker/dockerfile:1
# Image unique pour le web (Gunicorn) et le worker (Celery) — KAN-9.

FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY app/requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod
RUN groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/* && rm -rf /wheels
COPY --chown=app:app app/ /app/
COPY --chown=app:app architecture/dream.schema.json /architecture/dream.schema.json
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput \
    && mkdir -p /app/media && chown app:app /app && chown -R app:app /app/media /app/staticfiles
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/healthz/').status != 200)"
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
