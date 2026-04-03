#!/bin/sh
# Selecciona el modo de arranque según la variable APP_MODE:
#   api     → FastAPI con Gunicorn (por defecto)
#   worker  → Celery worker
#   beat    → Celery beat scheduler

set -e

case "${APP_MODE:-api}" in
  worker)
    echo "Iniciando Celery Worker..."
    exec celery -A collector.celery_app worker \
      --loglevel=info \
      --concurrency=2 \
      -E
    ;;
  beat)
    echo "Iniciando Celery Beat..."
    exec celery -A collector.celery_app beat \
      --loglevel=info \
      --scheduler celery.beat:PersistentScheduler
    ;;
  *)
    echo "Iniciando API (Gunicorn)..."
    exec gunicorn api.main:app \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind 0.0.0.0:8000 \
      --workers 2 \
      --timeout 120
    ;;
esac
