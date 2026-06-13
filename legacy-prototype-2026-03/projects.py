from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from api.dependencies import DbDep, PaginationDep
from api.schemas import ProjectCreate, ProjectOut, ProjectRankingSummary
from core.models import Project, ProjectKeyword, Ranking

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=list[ProjectOut])
def list_projects(db: DbDep, pagination: PaginationDep):
    """Lista todos los proyectos activos."""
    return db.scalars(
        select(Project)
        .where(Project.is_active == True)
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: DbDep):
    """Crea un nuevo proyecto."""
    existing = db.scalar(select(Project).where(Project.domain == body.domain))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un proyecto con el dominio '{body.domain}'",
        )
    project = Project(**body.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: DbDep):
    project = _get_or_404(db, project_id)
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectCreate, db: DbDep):
    project = _get_or_404(db, project_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: DbDep):
    project = _get_or_404(db, project_id)
    project.is_active = False
    db.commit()


@router.get("/{project_id}/summary", response_model=ProjectRankingSummary)
def get_project_summary(project_id: int, db: DbDep):
    """
    Resumen del proyecto para el dashboard:
    total keywords, distribución por posición, avg position.
    """
    project = _get_or_404(db, project_id)

    # Subconsulta: último ranking por project_keyword (fuente: dataforseo o gsc)
    latest_date_subq = (
        select(
            Ranking.project_keyword_id,
            func.max(Ranking.check_date).label("max_date"),
        )
        .join(ProjectKeyword, Ranking.project_keyword_id == ProjectKeyword.id)
        .where(ProjectKeyword.project_id == project_id)
        .group_by(Ranking.project_keyword_id)
        .subquery()
    )

    latest_rankings = db.execute(
        select(Ranking)
        .join(
            latest_date_subq,
            (Ranking.project_keyword_id == latest_date_subq.c.project_keyword_id)
            & (Ranking.check_date == latest_date_subq.c.max_date),
        )
    ).scalars().all()

    positions = [r.position for r in latest_rankings]
    non_null = [p for p in positions if p is not None]

    total_kw = db.scalar(
        select(func.count(ProjectKeyword.id)).where(
            ProjectKeyword.project_id == project_id,
            ProjectKeyword.is_active == True,
        )
    ) or 0

    check_date = latest_rankings[0].check_date if latest_rankings else None

    return ProjectRankingSummary(
        project_id=project.id,
        project_name=project.name,
        domain=project.domain,
        total_keywords=total_kw,
        keywords_top3=sum(1 for p in non_null if p <= 3),
        keywords_top10=sum(1 for p in non_null if p <= 10),
        keywords_top100=len(non_null),
        keywords_not_found=sum(1 for p in positions if p is None),
        avg_position=round(sum(non_null) / len(non_null), 1) if non_null else None,
        check_date=check_date,
    )


def _get_or_404(db, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project or not project.is_active:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project
