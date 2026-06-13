"""
Tasks Celery para ingesta de datos DataForSEO (SERP) y competitor_rankings.
"""

import logging
from datetime import date

from celery import shared_task
from sqlalchemy import select

from collector.celery_app import celery_app
from collector.sources.dataforseo_client import DataForSEOClient
from core.database import SessionLocal
from core.models import (
    Project, ProjectKeyword, Ranking,
    Competitor, CompetitorRanking,
)

logger = logging.getLogger(__name__)

# Mapeo de código ISO país → location_code DataForSEO
LOCATION_CODES = {
    "ES": 2724, "US": 2840, "MX": 2484, "AR": 2032,
    "CO": 2170, "CL": 2152, "PE": 2604, "GB": 2826,
    "DE": 2276, "FR": 2250, "IT": 2380,
}


@celery_app.task(bind=True, name="collector.tasks.dataforseo_tasks.run_dataforseo_all_projects", max_retries=2)
def run_dataforseo_all_projects(self):
    """Dispara la ingesta DataForSEO para todos los proyectos activos."""
    db = SessionLocal()
    try:
        projects = db.scalars(
            select(Project).where(Project.is_active == True)
        ).all()
        logger.info("DataForSEO: %d proyectos a ingestar", len(projects))
        for project in projects:
            run_dataforseo_project.delay(project.id)
    finally:
        db.close()


@celery_app.task(bind=True, name="collector.tasks.dataforseo_tasks.run_dataforseo_project", max_retries=3)
def run_dataforseo_project(self, project_id: int):
    """Ingesta DataForSEO para todas las keywords de un proyecto."""
    db = SessionLocal()
    try:
        project = db.get(Project, project_id)
        if not project or not project.is_active:
            logger.warning("DataForSEO: proyecto %d no válido", project_id)
            return

        pks = db.scalars(
            select(ProjectKeyword).where(
                ProjectKeyword.project_id == project_id,
                ProjectKeyword.is_active == True,
            )
        ).all()

        success, errors = 0, 0
        for pk in pks:
            try:
                fetch_and_store_dataforseo_keyword(project_id=project_id, pk_id=pk.id)
                success += 1
            except Exception as exc:
                logger.error(
                    "DataForSEO: error en pk_id=%d: %s", pk.id, exc, exc_info=True
                )
                errors += 1

        logger.info(
            "DataForSEO proyecto %d: %d ok, %d errores", project_id, success, errors
        )
    except Exception as exc:
        logger.error(
            "DataForSEO proyecto %d: fallo general: %s", project_id, exc, exc_info=True
        )
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()


@celery_app.task(bind=True, name="collector.tasks.dataforseo_tasks.fetch_and_store_dataforseo_keyword", max_retries=3)
def fetch_and_store_dataforseo_keyword(self, pk_id: int = None, project_id: int = None):
    """
    Ingesta DataForSEO para una sola project_keyword.
    Persiste el ranking propio y los competitor_rankings.
    """
    db = SessionLocal()
    try:
        pk = db.get(ProjectKeyword, pk_id)
        if not pk or not pk.is_active:
            return

        project = db.get(Project, pk.project_id)
        if not project or not project.is_active:
            return

        location_code = LOCATION_CODES.get(project.country.upper(), 2724)
        client = DataForSEOClient()

        serp = client.fetch_serp_for_project(
            keyword=pk.keyword.keyword,
            own_domain=project.domain,
            location_code=location_code,
            language_code=project.language,
            device=project.device,
        )

        today = date.today()

        # --- Guardar ranking propio ---
        existing = db.scalar(
            select(Ranking).where(
                Ranking.project_keyword_id == pk.id,
                Ranking.check_date == today,
                Ranking.source == "dataforseo",
            )
        )
        if existing:
            existing.position = serp["own_position"]
            existing.url = serp["own_url"]
            existing.raw_payload = serp["raw"]
        else:
            db.add(
                Ranking(
                    project_keyword_id=pk.id,
                    check_date=today,
                    position=serp["own_position"],
                    url=serp["own_url"],
                    source="dataforseo",
                    raw_payload=serp["raw"],
                )
            )

        # --- Guardar competitor_rankings ---
        active_competitors = {
            c.domain: c
            for c in db.scalars(
                select(Competitor).where(
                    Competitor.project_id == project.id,
                    Competitor.is_active == True,
                )
            ).all()
        }

        for comp_data in serp["competitors"]:
            domain = comp_data["domain"]
            # Solo guardar si es un competidor registrado
            if domain not in active_competitors:
                continue

            comp = active_competitors[domain]
            existing_cr = db.scalar(
                select(CompetitorRanking).where(
                    CompetitorRanking.project_keyword_id == pk.id,
                    CompetitorRanking.competitor_id == comp.id,
                    CompetitorRanking.check_date == today,
                )
            )
            if existing_cr:
                existing_cr.position = comp_data["position"]
                existing_cr.url = comp_data["url"]
            else:
                db.add(
                    CompetitorRanking(
                        project_keyword_id=pk.id,
                        competitor_id=comp.id,
                        check_date=today,
                        position=comp_data["position"],
                        url=comp_data["url"],
                    )
                )

        db.commit()
        logger.debug(
            "DataForSEO pk_id=%d: posición=%s", pk.id, serp["own_position"]
        )

    except Exception as exc:
        logger.error(
            "DataForSEO pk_id=%d: error: %s", pk_id, exc, exc_info=True
        )
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()
