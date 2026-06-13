from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.dependencies import DbDep
from api.schemas import AlertCreate, AlertOut
from core.models import Alert, ProjectKeyword, Project

router = APIRouter(prefix="/projects/{project_id}/alerts", tags=["alerts"])


@router.get("/", response_model=list[AlertOut])
def list_alerts(project_id: int, db: DbDep):
    _get_project_or_404(db, project_id)
    pk_ids = db.scalars(
        select(ProjectKeyword.id).where(ProjectKeyword.project_id == project_id)
    ).all()
    return db.scalars(
        select(Alert).where(
            Alert.project_keyword_id.in_(pk_ids),
            Alert.is_active == True,
        )
    ).all()


@router.post("/", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
def create_alert(project_id: int, body: AlertCreate, db: DbDep):
    _get_project_or_404(db, project_id)

    pk = db.get(ProjectKeyword, body.project_keyword_id)
    if not pk or pk.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="La keyword no pertenece a este proyecto",
        )

    alert = Alert(**body.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(project_id: int, alert_id: int, db: DbDep):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    pk = db.get(ProjectKeyword, alert.project_keyword_id)
    if not pk or pk.project_id != project_id:
        raise HTTPException(status_code=403, detail="No pertenece a este proyecto")
    alert.is_active = False
    db.commit()


def _get_project_or_404(db, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project or not project.is_active:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project
