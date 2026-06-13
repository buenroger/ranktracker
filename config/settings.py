"""
Configuración centralizada con pydantic-settings.
Los valores se leen de variables de entorno o del archivo .env.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---------------------------------------------------------------------------
    # Base de datos MySQL
    # ---------------------------------------------------------------------------
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "ranktracker"
    db_user: str = "ranktracker"
    db_password: str = "secret"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    # ---------------------------------------------------------------------------
    # Redis / Celery
    # ---------------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url

    # ---------------------------------------------------------------------------
    # Google Search Console
    # ---------------------------------------------------------------------------
    gsc_credentials_file: str = "gsc_credentials.json"
    gsc_token_file: str = "gsc_token.json"
    # Scope de solo lectura para GSC
    gsc_scopes: list[str] = ["https://www.googleapis.com/auth/webmasters.readonly"]
    # Días hacia atrás a pedir en cada ingesta
    gsc_lookback_days: int = 3
    # Filas máximas por petición a la API de GSC
    gsc_row_limit: int = 25000

    # ---------------------------------------------------------------------------
    # DataForSEO
    # ---------------------------------------------------------------------------
    dataforseo_login: str = ""
    dataforseo_password: str = ""
    dataforseo_api_url: str = "https://api.dataforseo.com/v3"
    # Tiempo de espera entre reintentos (segundos)
    dataforseo_retry_delay: float = 5.0
    dataforseo_max_retries: int = 3

    # ---------------------------------------------------------------------------
    # Alertas por email
    # ---------------------------------------------------------------------------
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_from_email: str = "ranktracker@example.com"

    # ---------------------------------------------------------------------------
    # CORS
    # ---------------------------------------------------------------------------
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # ---------------------------------------------------------------------------
    # General
    # ---------------------------------------------------------------------------
    debug: bool = False
    app_env: str = "production"


settings = Settings()
