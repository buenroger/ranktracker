from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func, and_

from api.dependencies import DbDep, PaginationDep
from api.schemas import (
    KeywordCreate, KeywordOut,
    ProjectKeywordCreate, ProjectKeywordOut,
    KeywordRankingSummary, RankingHistoryPoint,
    CompetitorRankingPoint,
)
from core.models import (
    Keyword, Project, ProjectKeyword, Ranking,
    Competitor, CompetitorRanking,
)

router = APIRouter(tags=["keywords"])


# ---------------------------------------------------------------------------
# Catálogo global de keywords
# ---------------------------------------------------------------------------

global_router = APIRouter(prefix="/keywords")


@global_router.get("/", response_model=list[KeywordOut])
def list_keywords(db: DbDep, pagination: PaginationDep, q: Optional[str] = None):
    """Lista el catálogo global de keywords, con búsqueda opcional."""
    stmt = select(Keyword).offset(pagination.offset).limit(pagination.page_size)
    if q:
        stmt = stmt.where(Keyword.keyword.ilike(f"%{q}%"))
    return db.scalars(stmt).all()


@global_router.post("/", response_model=KeywordOut, status_code=status.HTTP_201_CREATED)
def create_keyword(body: KeywordCreate, db: DbDep):
    """Crea una keyword en el catálogo global (o devuelve la existente)."""
    existing = db.scalar(
        select(Keyword).where(
            Keyword.keyword == body.keyword,
            Keyword.language == body.language,
            Keyword.country == body.country,
        )
    )
    if existing:
        return existing
    kw = Keyword(**body.model_dump())
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return kw


# ---------------------------------------------------------------------------
# Keywords por proyecto
# ---------------------------------------------------------------------------

project_router = APIRouter(prefix="/projects/{project_id}/keywords")


@project_router.get("/", response_model=list[KeywordRankingSummary])
def list_project_keywords(
    project_id: int,
    db: DbDep,
    pagination: PaginationDep,
    tag: Optional[str] = Query(None),
    source: Optional[str] = Query(None, description="gsc | dataforseo"),
    days: int = Query(2, ge=1, le=90, description="Días atrás para calcular la variación"),
):
    """
    Lista las keywords del proyecto con su posición actual y variación.
    Ideal para la tabla principal del dashboard.
    """
    _get_project_or_404(db, project_id)

    stmt = (
        select(ProjectKeyword)
        .where(
            ProjectKeyword.project_id == project_id,
            ProjectKeyword.is_active == True,
        )
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    if tag:
        stmt = stmt.where(ProjectKeyword.tag == tag)

    pks = db.scalars(stmt).all()
    results = []

    for pk in pks:
        summary = _build_keyword_summary(db, pk, days=days, source=source)
        results.append(summary)

    return results


@project_router.post(
    "/", response_model=ProjectKeywordOut, status_code=status.HTTP_201_CREATED
)
def add_keyword_to_project(project_id: int, body: ProjectKeywordCreate, db: DbDep):
    """Añade una keyword existente del catálogo al proyecto."""
    _get_project_or_404(db, project_id)

    kw = db.get(Keyword, body.keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword no encontrada en el catálogo")

    existing = db.scalar(
        select(ProjectKeyword).where(
            ProjectKeyword.project_id == project_id,
            ProjectKeyword.keyword_id == body.keyword_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="La keyword ya está en este proyecto")

    pk = ProjectKeyword(project_id=project_id, **body.model_dump())
    db.add(pk)
    db.commit()
    db.refresh(pk)
    return pk


@project_router.delete("/{pk_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_keyword_from_project(project_id: int, pk_id: int, db: DbDep):
    """Desactiva una keyword del proyecto (no borra el histórico)."""
    pk = _get_pk_or_404(db, project_id, pk_id)
    pk.is_active = False
    db.commit()


@project_router.get("/{pk_id}/history", response_model=list[RankingHistoryPoint])
def get_keyword_history(
    project_id: int,
    pk_id: int,
    db: DbDep,
    days: int = Query(30, ge=1, le=365),
    source: Optional[str] = Query(None),
):
    """
    Serie temporal de posiciones para una keyword.
    Úsalo para renderizar el gráfico de evolución.
    """
    _get_pk_or_404(db, project_id, pk_id)

    since = date.today() - timedelta(days=days)
    stmt = (
        select(Ranking)
        .where(
            Ranking.project_keyword_id == pk_id,
            Ranking.check_date >= since,
        )
        .order_by(Ranking.check_date.asc())
    )
    if source:
        stmt = stmt.where(Ranking.source == source)

    rankings = db.scalars(stmt).all()
    return [
        RankingHistoryPoint(
            check_date=r.check_date,
            position=r.position,
            source=r.source,
        )
        for r in rankings
    ]


@project_router.get("/{pk_id}/competitors", response_model=list[CompetitorRankingPoint])
def get_keyword_competitors(
    project_id: int,
    pk_id: int,
    db: DbDep,
    days: int = Query(30, ge=1, le=90),
):
    """
    Posiciones de los competidores para una keyword en los últimos N días.
    """
    _get_pk_or_404(db, project_id, pk_id)

    since = date.today() - timedelta(days=days)
    rows = db.execute(
        select(
            CompetitorRanking.competitor_id,
            CompetitorRanking.position,
            CompetitorRanking.url,
            CompetitorRanking.check_date,
            Competitor.domain,
        )
        .join(Competitor, CompetitorRanking.competitor_id == Competitor.id)
        .where(
            CompetitorRanking.project_keyword_id == pk_id,
            CompetitorRanking.check_date >= since,
        )
        .order_by(CompetitorRanking.check_date.asc())
    ).all()

    return [
        CompetitorRankingPoint(
            competitor_id=row.competitor_id,
            competitor_domain=row.domain,
            position=row.position,
            url=row.url,
            check_date=row.check_date,
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _build_keyword_summary(
    db, pk: ProjectKeyword, days: int, source: Optional[str]
) -> KeywordRankingSummary:
    """Construye el resumen de posición actual + variación para una keyword."""

    # Ranking más reciente
    stmt_latest = (
        select(Ranking)
        .where(Ranking.project_keyword_id == pk.id)
        .order_by(Ranking.check_date.desc())
        .limit(1)
    )
    if source:
        stmt_latest = stmt_latest.where(Ranking.source == source)
    latest = db.scalars(stmt_latest).first()

    # Ranking de hace N días (para calcular variación)
    stmt_prev = (
        select(Ranking)
        .where(
            Ranking.project_keyword_id == pk.id,
            Ranking.check_date <= date.today() - timedelta(days=days),
        )
        .order_by(Ranking.check_date.desc())
        .limit(1)
    )
    if source:
        stmt_prev = stmt_prev.where(Ranking.source == source)
    prev = db.scalars(stmt_prev).first()

    curr_pos = latest.position if latest else None
    prev_pos = prev.position if prev else None

    # Variación: positivo = subió (número bajó), negativo = bajó
    change = None
    if curr_pos is not None and prev_pos is not None:
        change = prev_pos - curr_pos

    return KeywordRankingSummary(
        project_keyword_id=pk.id,
        keyword=pk.keyword.keyword,
        tag=pk.tag,
        target_position=pk.target_position,
        current_position=curr_pos,
        previous_position=prev_pos,
        position_change=change,
        best_url=latest.url if latest else None,
        impressions=latest.impressions if latest else None,
        clicks=latest.clicks if latest else None,
        ctr=float(latest.click_through_rate) if latest and latest.click_through_rate else None,
        last_check=latest.check_date if latest else None,
        source=latest.source if latest else None,
    )


def _get_project_or_404(db, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project or not project.is_active:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


def _get_pk_or_404(db, project_id: int, pk_id: int) -> ProjectKeyword:
    pk = db.get(ProjectKeyword, pk_id)
    if not pk or pk.project_id != project_id:
        raise HTTPException(status_code=404, detail="Keyword no encontrada en este proyecto")
    return pk
