from typing import Annotated, Generator
from fastapi import Depends, Query
from sqlalchemy.orm import Session
from core.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Inyecta una sesión de BD en cada request y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


class Pagination:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(50, ge=1, le=200, description="Resultados por página"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


PaginationDep = Annotated[Pagination, Depends(Pagination)]
