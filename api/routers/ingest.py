"""
Endpoints para disparar tareas de ingesta manualmente desde la API.
Útil para el panel de administración o para forzar un refresh sin esperar el schedule.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/ingest", tags=["ingesta"])


class IngestResponse(BaseModel):
    status: str
    detail: str


@router.post("/all", response_model=IngestResponse)
def trigger_full_ingest():
    """Lanza la ingesta completa (GSC + DataForSEO) para todos los proyectos."""
    try:
        from collector.tasks.gsc_tasks import run_gsc_all_projects
        from collector.tasks.dataforseo_tasks import run_dataforseo_all_projects

        run_gsc_all_projects.delay()
        run_dataforseo_all_projects.delay()

        return IngestResponse(
            status="queued",
            detail="Tareas de ingesta enviadas a la cola. Revisa Celery para el estado.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/gsc", response_model=IngestResponse)
def trigger_gsc_project(project_id: int):
    """Dispara la ingesta GSC para un proyecto concreto."""
    try:
        from collector.tasks.gsc_tasks import run_gsc_project
        run_gsc_project.delay(project_id)
        return IngestResponse(
            status="queued",
            detail=f"Ingesta GSC del proyecto {project_id} enviada a la cola.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/dataforseo", response_model=IngestResponse)
def trigger_dataforseo_project(project_id: int):
    """Dispara la ingesta DataForSEO para un proyecto concreto."""
    try:
        from collector.tasks.dataforseo_tasks import run_dataforseo_project
        run_dataforseo_project.delay(project_id)
        return IngestResponse(
            status="queued",
            detail=f"Ingesta DataForSEO del proyecto {project_id} enviada a la cola.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keywords/{pk_id}/dataforseo", response_model=IngestResponse)
def trigger_dataforseo_keyword(pk_id: int):
    """Dispara la ingesta DataForSEO para una keyword concreta. Útil para debugar."""
    try:
        from collector.tasks.dataforseo_tasks import fetch_and_store_dataforseo_keyword
        fetch_and_store_dataforseo_keyword.delay(pk_id)
        return IngestResponse(
            status="queued",
            detail=f"Ingesta DataForSEO de la keyword {pk_id} enviada a la cola.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
