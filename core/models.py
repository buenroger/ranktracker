"""
Modelos SQLAlchemy — 8 tablas del dominio rank tracker.

Tablas:
  projects            — proyectos SEO a monitorizar
  keywords            — catálogo global de keywords
  project_keywords    — relación proyecto ↔ keyword + metadatos
  rankings            — histórico de posiciones (GSC + DataForSEO)
  competitors         — competidores por proyecto
  competitor_rankings — posiciones de competidores por keyword
  alerts              — reglas de alerta por keyword
  alert_events        — log de alertas disparadas
"""

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Enum,
    Float, ForeignKey, Index, Integer, JSON, String, Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class Project(Base):
    __tablename__ = "projects"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String(255), nullable=False)
    domain: str = Column(String(255), nullable=False, unique=True)
    country: str = Column(String(10), nullable=False, default="ES")
    language: str = Column(String(10), nullable=False, default="es")
    device: str = Column(
        Enum("desktop", "mobile", "tablet", name="device_enum"),
        nullable=False,
        default="desktop",
    )
    gsc_site_url: Optional[str] = Column(String(500), nullable=True)
    is_active: bool = Column(Boolean, nullable=False, default=True)
    created_at: datetime = Column(DateTime, nullable=False, default=func.now())
    updated_at: datetime = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    project_keywords: list["ProjectKeyword"] = relationship(
        "ProjectKeyword", back_populates="project", passive_deletes=True
    )
    competitors: list["Competitor"] = relationship(
        "Competitor", back_populates="project", passive_deletes=True
    )


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

class Keyword(Base):
    __tablename__ = "keywords"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    keyword: str = Column(String(500), nullable=False)
    language: str = Column(String(10), nullable=False, default="es")
    country: str = Column(String(10), nullable=False, default="ES")

    __table_args__ = (
        Index("uq_keyword_lang_country", "keyword", "language", "country", unique=True),
    )

    project_keywords: list["ProjectKeyword"] = relationship(
        "ProjectKeyword", back_populates="keyword"
    )


# ---------------------------------------------------------------------------
# ProjectKeywords
# ---------------------------------------------------------------------------

class ProjectKeyword(Base):
    __tablename__ = "project_keywords"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    project_id: int = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    keyword_id: int = Column(
        Integer, ForeignKey("keywords.id", ondelete="RESTRICT"), nullable=False
    )
    target_position: Optional[int] = Column(Integer, nullable=True)
    tag: Optional[str] = Column(String(100), nullable=True)
    is_active: bool = Column(Boolean, nullable=False, default=True)
    created_at: datetime = Column(DateTime, nullable=False, default=func.now())

    __table_args__ = (
        Index("uq_project_keyword", "project_id", "keyword_id", unique=True),
    )

    project: "Project" = relationship("Project", back_populates="project_keywords")
    keyword: "Keyword" = relationship("Keyword", back_populates="project_keywords")
    rankings: list["Ranking"] = relationship(
        "Ranking", back_populates="project_keyword", passive_deletes=True
    )
    competitor_rankings: list["CompetitorRanking"] = relationship(
        "CompetitorRanking", back_populates="project_keyword", passive_deletes=True
    )
    alerts: list["Alert"] = relationship(
        "Alert", back_populates="project_keyword", passive_deletes=True
    )


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------

class Ranking(Base):
    __tablename__ = "rankings"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    project_keyword_id: int = Column(
        Integer, ForeignKey("project_keywords.id", ondelete="CASCADE"), nullable=False
    )
    check_date: date = Column(Date, nullable=False)
    position: Optional[int] = Column(Integer, nullable=True)
    url: Optional[str] = Column(Text, nullable=True)
    impressions: Optional[int] = Column(Integer, nullable=True)
    clicks: Optional[int] = Column(Integer, nullable=True)
    click_through_rate: Optional[float] = Column(Float, nullable=True)
    avg_position_gsc: Optional[float] = Column(Float, nullable=True)
    source: str = Column(
        Enum("gsc", "dataforseo", name="ranking_source_enum"),
        nullable=False,
        default="dataforseo",
    )
    raw_payload: Optional[dict] = Column(JSON, nullable=True)

    __table_args__ = (
        Index(
            "uq_ranking_date_source",
            "project_keyword_id", "check_date", "source",
            unique=True,
        ),
        Index("idx_ranking_pk_date", "project_keyword_id", "check_date"),
    )

    project_keyword: "ProjectKeyword" = relationship(
        "ProjectKeyword", back_populates="rankings"
    )


# ---------------------------------------------------------------------------
# Competitors
# ---------------------------------------------------------------------------

class Competitor(Base):
    __tablename__ = "competitors"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    project_id: int = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    domain: str = Column(String(255), nullable=False)
    name: Optional[str] = Column(String(255), nullable=True)
    is_active: bool = Column(Boolean, nullable=False, default=True)
    created_at: datetime = Column(DateTime, nullable=False, default=func.now())

    __table_args__ = (
        Index("uq_project_competitor", "project_id", "domain", unique=True),
    )

    project: "Project" = relationship("Project", back_populates="competitors")
    competitor_rankings: list["CompetitorRanking"] = relationship(
        "CompetitorRanking", back_populates="competitor", passive_deletes=True
    )


# ---------------------------------------------------------------------------
# CompetitorRankings
# ---------------------------------------------------------------------------

class CompetitorRanking(Base):
    __tablename__ = "competitor_rankings"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    project_keyword_id: int = Column(
        Integer, ForeignKey("project_keywords.id", ondelete="CASCADE"), nullable=False
    )
    competitor_id: int = Column(
        Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    check_date: date = Column(Date, nullable=False)
    position: Optional[int] = Column(Integer, nullable=True)
    url: Optional[str] = Column(Text, nullable=True)

    __table_args__ = (
        Index(
            "uq_competitor_ranking_date",
            "project_keyword_id", "competitor_id", "check_date",
            unique=True,
        ),
    )

    project_keyword: "ProjectKeyword" = relationship(
        "ProjectKeyword", back_populates="competitor_rankings"
    )
    competitor: "Competitor" = relationship(
        "Competitor", back_populates="competitor_rankings"
    )


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class Alert(Base):
    __tablename__ = "alerts"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    project_keyword_id: int = Column(
        Integer, ForeignKey("project_keywords.id", ondelete="CASCADE"), nullable=False
    )
    alert_type: str = Column(
        Enum(
            "position_drop", "position_gain",
            "entered_top10", "left_top10",
            "entered_top3", "not_found",
            name="alert_type_enum",
        ),
        nullable=False,
    )
    threshold_positions: Optional[int] = Column(Integer, nullable=True)
    channel: str = Column(
        Enum("email", "webhook", "slack", name="alert_channel_enum"),
        nullable=False,
        default="email",
    )
    channel_config: dict = Column(JSON, nullable=False, default=dict)
    is_active: bool = Column(Boolean, nullable=False, default=True)
    created_at: datetime = Column(DateTime, nullable=False, default=func.now())

    project_keyword: "ProjectKeyword" = relationship(
        "ProjectKeyword", back_populates="alerts"
    )
    events: list["AlertEvent"] = relationship(
        "AlertEvent", back_populates="alert", passive_deletes=True
    )


# ---------------------------------------------------------------------------
# AlertEvents
# ---------------------------------------------------------------------------

class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    alert_id: int = Column(
        Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    triggered_at: datetime = Column(DateTime, nullable=False, default=func.now())
    previous_position: Optional[int] = Column(Integer, nullable=True)
    current_position: Optional[int] = Column(Integer, nullable=True)
    message: Optional[str] = Column(Text, nullable=True)
    sent: bool = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_alert_event_alert_date", "alert_id", "triggered_at"),
    )

    alert: "Alert" = relationship("Alert", back_populates="events")
