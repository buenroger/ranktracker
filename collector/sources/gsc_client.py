"""
Cliente Google Search Console con paginación automática y retry.

Requiere:
  - gsc_credentials.json  (OAuth2 client secrets)
  - gsc_token.json        (token persistido tras el primer login)

Si el token no existe, el primer uso lanza el flujo interactivo de OAuth.
"""

import logging
import time
from datetime import date, timedelta
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import settings

logger = logging.getLogger(__name__)


def _get_credentials() -> Credentials:
    """Carga o refresca las credenciales OAuth2 para GSC."""
    import json
    import os

    creds: Optional[Credentials] = None

    if os.path.exists(settings.gsc_token_file):
        creds = Credentials.from_authorized_user_file(
            settings.gsc_token_file, settings.gsc_scopes
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.gsc_credentials_file, settings.gsc_scopes
            )
            creds = flow.run_local_server(port=0)
        with open(settings.gsc_token_file, "w") as token_file:
            token_file.write(creds.to_json())

    return creds


class GSCClient:
    """Wrapper sobre la Search Console API v1."""

    def __init__(self):
        creds = _get_credentials()
        self._service = build("searchconsole", "v1", credentials=creds)

    def fetch_keyword_data(
        self,
        site_url: str,
        keyword: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        country: str = "ESP",
        device: str = "DESKTOP",
    ) -> list[dict]:
        """
        Devuelve datos de rendimiento GSC para una keyword concreta.

        Retorna lista de dicts con:
          date, clicks, impressions, ctr, position
        """
        if end_date is None:
            end_date = date.today() - timedelta(days=3)  # GSC tiene ~3 días de retraso
        if start_date is None:
            start_date = end_date - timedelta(days=settings.gsc_lookback_days - 1)

        rows: list[dict] = []
        start_row = 0

        while True:
            body = {
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "dimensions": ["date"],
                "dimensionFilterGroups": [
                    {
                        "filters": [
                            {
                                "dimension": "query",
                                "operator": "equals",
                                "expression": keyword,
                            },
                            {
                                "dimension": "country",
                                "operator": "equals",
                                "expression": country,
                            },
                            {
                                "dimension": "device",
                                "operator": "equals",
                                "expression": device,
                            },
                        ]
                    }
                ],
                "rowLimit": settings.gsc_row_limit,
                "startRow": start_row,
            }

            response = self._execute_with_retry(
                self._service.searchanalytics().query(siteUrl=site_url, body=body)
            )

            page_rows = response.get("rows", [])
            for row in page_rows:
                rows.append(
                    {
                        "date": row["keys"][0],
                        "clicks": row.get("clicks", 0),
                        "impressions": row.get("impressions", 0),
                        "ctr": row.get("ctr", 0.0),
                        "position": row.get("position"),
                    }
                )

            if len(page_rows) < settings.gsc_row_limit:
                break
            start_row += settings.gsc_row_limit

        return rows

    def _execute_with_retry(self, request, max_retries: int = 3, backoff: float = 2.0):
        """Ejecuta una petición con retry exponencial ante errores 5xx."""
        for attempt in range(max_retries):
            try:
                return request.execute()
            except HttpError as exc:
                if exc.resp.status in (429, 500, 503) and attempt < max_retries - 1:
                    wait = backoff ** attempt
                    logger.warning(
                        "GSC HTTP %s — reintento %d/%d en %.1fs",
                        exc.resp.status, attempt + 1, max_retries, wait,
                    )
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError("GSC: máximo de reintentos alcanzado")
