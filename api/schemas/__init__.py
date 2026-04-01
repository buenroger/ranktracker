"""
Schemas Pydantic para request/response de la API.
Separados de los modelos SQLAlchemy para no acoplar capas.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# Base helpers
# ---------------------------------------------------------------------------

class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str
    domain: str
    country: str = "ES"
    language: str = "es"
    device: str = "desktop"
    gsc_site_url: Optional[str] = None

    @field_validator("device")
    @classmethod
    def validate_device(cls, v):
        if v not in {"desktop", "mobile", "tablet"}:
            raise ValueError("device debe ser desktop, mobile o tablet")
        return v


class ProjectOut(OrmBase):
    id: int
    name: str
    domain: str
    country: str
    language: str
    device: str
    gsc_site_url: Optional[str]
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

class KeywordCreate(BaseModel):
    keyword: str
    language: str = "es"
    country: str = "ES"


class KeywordOut(OrmBase):
    id: int
    keyword: str
    language: str
    country: str


# ---------------------------------------------------------------------------
# ProjectKeywords
# ---------------------------------------------------------------------------

class ProjectKeywordCreate(BaseModel):
    keyword_id: int
    target_position: Optional[int] = None
    tag: Optional[str] = None


class ProjectKeywordOut(OrmBase):
    id: int
    project_id: int
    keyword_id: int
    keyword: KeywordOut
    target_position: Optional[int]
    tag: Optional[str]
    is_active: bool


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------

class RankingOut(OrmBase):
    id: int
    project_keyword_id: int
    check_date: date
    position: Optional[int]
    url: Optional[str]
    impressions: Optional[int]
    clicks: Optional[int]
    click_through_rate: Optional[float]
    avg_position_gsc: Optional[float]
    source: str


class RankingHistoryPoint(BaseModel):
    """Un punto en la serie temporal de posiciones."""
    check_date: date
    position: Optional[int]
    source: str


class KeywordRankingSummary(BaseModel):
    """Vista resumida de una keyword con su posición actual y tendencia."""
    project_keyword_id: int
    keyword: str
    tag: Optional[str]
    target_position: Optional[int]
    current_position: Optional[int]
    previous_position: Optional[int]
    position_change: Optional[int]       # positivo = subió, negativo = bajó
    best_url: Optional[str]
    impressions: Optional[int]
    clicks: Optional[int]
    ctr: Optional[float]
    last_check: Optional[date]
    source: Optional[str]


class ProjectRankingSummary(BaseModel):
    """Resumen global de un proyecto para el dashboard."""
    project_id: int
    project_name: str
    domain: str
    total_keywords: int
    keywords_top3: int
    keywords_top10: int
    keywords_top100: int
    keywords_not_found: int
    avg_position: Optional[float]
    check_date: Optional[date]


# ---------------------------------------------------------------------------
# Competitors
# ---------------------------------------------------------------------------

class CompetitorCreate(BaseModel):
    domain: str
    name: Optional[str] = None


class CompetitorOut(OrmBase):
    id: int
    project_id: int
    domain: str
    name: Optional[str]
    is_active: bool


class CompetitorRankingPoint(BaseModel):
    competitor_id: int
    competitor_domain: str
    position: Optional[int]
    url: Optional[str]
    check_date: date


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class AlertCreate(BaseModel):
    project_keyword_id: int
    alert_type: str
    threshold_positions: Optional[int] = None
    channel: str = "email"
    channel_config: dict

    @field_validator("alert_type")
    @classmethod
    def validate_alert_type(cls, v):
        valid = {
            "position_drop", "position_gain",
            "entered_top10", "left_top10",
            "entered_top3", "not_found",
        }
        if v not in valid:
            raise ValueError(f"alert_type debe ser uno de: {valid}")
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v):
        if v not in {"email", "webhook", "slack"}:
            raise ValueError("channel debe ser email, webhook o slack")
        return v


class AlertOut(OrmBase):
    id: int
    project_keyword_id: int
    alert_type: str
    threshold_positions: Optional[int]
    channel: str
    is_active: bool


# ---------------------------------------------------------------------------
# Paginación genérica
# ---------------------------------------------------------------------------

class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list
