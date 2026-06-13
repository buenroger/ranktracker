"""
Tasks Celery para ingesta de datos de Google Search Console.
"""

import logging
from datetime import date, datetime

from celery import shared_task
from sqlalchemy import select

from collector.celery_app import celery_app
from collector.sources.gsc_client import GSCClient
from config.settings import settings
from core.database import SessionLocal
from core.models import Project, ProjectKeyword, Keyword, Ranking

logger = logging.getLogger(__name__)

# Mapeo de código de país ISO 3166-1 alpha-2 → código GSC (3 letras)
COUNTRY_MAP = {
    "ES": "ESP", "US": "USA", "MX": "MEX", "AR": "ARG",
    "CO": "COL", "CL": "CHL", "PE": "PER", "GB": "GBR",
    "DE": "DEU", "FR": "FRA", "IT": "ITA",
}

DEVICE_MAP = {
    "desktop": "DESKTOP",
    "mobile": "MOBILE",
    "tablet": "TABLET",
}


@celery_app.task(bind=True, name="collector.tasks.gsc_tasks.run_gsc_all_projects", max_retries=2)
def run_gsc_all_projects(self):
    """Dispara la ingesta GSC para todos los proyectos activos que tengan gsc_site_url."""
    db = SessionLocal()
    try:
        projects = db.scalars(
            select(Project).where(
                Project.is_active == True,
                Project.gsc_site_url.isnot(None),
            )
        ).all()
        logger.info("GSC: %d proyectos a ingestar", len(projects))
        for project in projects:
            run_gsc_project.delay(project.id)
    finally:
        db.close()


@celery_app.task(bind=True, name="collector.tasks.gsc_tasks.run_gsc_project", max_retries=3)
def run_gsc_project(self, project_id: int):
    """Ingesta GSC completa para un proyecto (todas sus keywords activas)."""
    db = SessionLocal()
    try:
        project = db.get(Project, project_id)
        if not project or not project.is_active or not project.gsc_site_url:
            logger.warning("GSC: proyecto %d no válido o sin gsc_site_url", project_id)
            return

        pks = db.scalars(
            select(ProjectKeyword).where(
                ProjectKeyword.project_id == project_id,
                ProjectKeyword.is_active == True,
            )
        ).all()

        client = GSCClient()
        success, errors = 0, 0

        for pk in pks:
            try:
                _ingest_gsc_keyword(db, client, project, pk)
                success += 1
            except Exception as exc:
                logger.error(
                    "GSC: error en keyword pk_id=%d: %s", pk.id, exc, exc_info=True
                )
                errors += 1

        logger.info(
            "GSC proyecto %d: %d ok, %d errores", project_id, success, errors
        )
    except Exception as exc:
        logger.error("GSC proyecto %d: fallo general: %s", project_id, exc, exc_info=True)
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()


def _ingest_gsc_keyword(db, client: GSCClient, project: Project, pk: ProjectKeyword):
    """Descarga y persiste datos GSC para una sola project_keyword."""
    country_code = COUNTRY_MAP.get(project.country.upper(), "ESP")
    device_code = DEVICE_MAP.get(project.device.lower(), "DESKTOP")

    rows = client.fetch_keyword_data(
        site_url=project.gsc_site_url,
        keyword=pk.keyword.keyword,
        country=country_code,
        device=device_code,
    )

    for row in rows:
        check_date = date.fromisoformat(row["date"])
        position = round(row["position"]) if row.get("position") else None

        existing = db.scalar(
            select(Ranking).where(
                Ranking.project_keyword_id == pk.id,
                Ranking.check_date == check_date,
                Ranking.source == "gsc",
            )
        )

        if existing:
            existing.position = position
            existing.impressions = row.get("impressions")
            existing.clicks = row.get("clicks")
            existing.click_through_rate = row.get("ctr")
            existing.avg_position_gsc = row.get("position")
        else:
            ranking = Ranking(
                project_keyword_id=pk.id,
                check_date=check_date,
                position=position,
                impressions=row.get("impressions"),
                clicks=row.get("clicks"),
                click_through_rate=row.get("ctr"),
                avg_position_gsc=row.get("position"),
                source="gsc",
            )
            db.add(ranking)

    db.commit()
