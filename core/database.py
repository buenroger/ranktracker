"""
Engine y session factory SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Context manager / generador para inyectar sesión en FastAPI y en tareas Celery."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
