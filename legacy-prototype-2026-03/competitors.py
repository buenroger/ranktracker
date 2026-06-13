from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.dependencies import DbDep
from api.schemas import CompetitorCreate, CompetitorOut
from core.models import Competitor, Project

router = APIRouter(prefix="/projects/{project_id}/competitors", tags=["competitors"])


@router.get("/", response_model=list[CompetitorOut])
def list_competitors(project_id: int, db: DbDep):
    _get_project_or_404(db, project_id)
    return db.scalars(
        select(Competitor).where(
            Competitor.project_id == project_id,
            Competitor.is_active == True,
        )
    ).all()


@router.post("/", response_model=CompetitorOut, status_code=status.HTTP_201_CREATED)
def add_competitor(project_id: int, body: CompetitorCreate, db: DbDep):
    _get_project_or_404(db, project_id)

    existing = db.scalar(
        select(Competitor).where(
            Competitor.project_id == project_id,
            Competitor.domain == body.domain,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Competidor ya existe en este proyecto")

    competitor = Competitor(project_id=project_id, **body.model_dump())
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return competitor


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_competitor(project_id: int, competitor_id: int, db: DbDep):
    comp = db.get(Competitor, competitor_id)
    if not comp or comp.project_id != project_id:
        raise HTTPException(status_code=404, detail="Competidor no encontrado")
    comp.is_active = False
    db.commit()


def _get_project_or_404(db, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project or not project.is_active:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project
