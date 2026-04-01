"""
Aplicación Celery con beat schedule para ingesta automática.

Schedule:
  - GSC        → todos los días a las 06:00 (UTC)
  - DataForSEO → todos los días a las 07:00 (UTC)
  - Alertas    → cada hora
"""

from celery import Celery
from celery.schedules import crontab

from config.settings import settings

celery_app = Celery(
    "ranktracker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "collector.tasks.gsc_tasks",
        "collector.tasks.dataforseo_tasks",
        "collector.tasks.alert_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 24h
)

celery_app.conf.beat_schedule = {
    "gsc-daily-06:00": {
        "task": "collector.tasks.gsc_tasks.run_gsc_all_projects",
        "schedule": crontab(hour=6, minute=0),
    },
    "dataforseo-daily-07:00": {
        "task": "collector.tasks.dataforseo_tasks.run_dataforseo_all_projects",
        "schedule": crontab(hour=7, minute=0),
    },
    "alerts-hourly": {
        "task": "collector.tasks.alert_tasks.run_all_alerts",
        "schedule": crontab(minute=0),  # cada hora en punto
    },
}
