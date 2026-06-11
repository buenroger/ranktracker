"""
Bootstrap de la base de datos: aplica schema.sql (idempotente) contra MySQL.

Se ejecuta al arrancar cualquiera de los servicios (api/worker/beat) antes de
levantar el proceso principal. Es seguro ejecutarlo varias veces y desde
varios contenedores a la vez: schema.sql usa `CREATE TABLE IF NOT EXISTS`
y `CREATE OR REPLACE VIEW`.
"""

import logging
from pathlib import Path

import pymysql

from config.settings import settings

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


def _wait_for_mysql(max_attempts: int = 30, delay: float = 2.0) -> None:
    import time

    for attempt in range(1, max_attempts + 1):
        try:
            conn = pymysql.connect(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
            )
            conn.close()
            return
        except pymysql.err.OperationalError as exc:
            logger.info("Esperando a MySQL (%d/%d): %s", attempt, max_attempts, exc)
            time.sleep(delay)
    raise RuntimeError("No se pudo conectar a MySQL tras varios intentos")


def _split_statements(sql: str) -> list[str]:
    """Divide schema.sql en sentencias individuales, ignorando comentarios."""
    statements = []
    for raw_stmt in sql.split(";"):
        lines = [
            line for line in raw_stmt.splitlines()
            if not line.strip().startswith("--")
        ]
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)
    return statements


def init_db() -> None:
    _wait_for_mysql()

    # Crea la base de datos configurada (DB_NAME) si no existe.
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        autocommit=True,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        conn.close()

    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [
        stmt for stmt in _split_statements(sql)
        if not stmt.upper().startswith("CREATE DATABASE")
        and not stmt.upper().startswith("USE ")
    ]

    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        autocommit=True,
    )
    try:
        with conn.cursor() as cursor:
            for stmt in statements:
                cursor.execute(stmt)
        logger.info("Base de datos '%s' inicializada (%d sentencias aplicadas)", settings.db_name, len(statements))
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    init_db()
