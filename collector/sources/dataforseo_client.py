"""
Cliente DataForSEO SERP con extracción de posición propia y posiciones de competidores.

Documentación: https://docs.dataforseo.com/v3/serp/google/organic/live/regular/
"""

import logging
import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import settings

logger = logging.getLogger(__name__)

SERP_ENDPOINT = f"{settings.dataforseo_api_url}/serp/google/organic/live/regular"


def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=settings.dataforseo_max_retries,
        backoff_factor=settings.dataforseo_retry_delay,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.auth = (settings.dataforseo_login, settings.dataforseo_password)
    session.headers.update({"Content-Type": "application/json"})
    return session


class DataForSEOClient:
    """Wrapper sobre la API SERP de DataForSEO."""

    def __init__(self):
        self._session = _make_session()

    def fetch_serp(
        self,
        keyword: str,
        location_code: int = 2724,   # España por defecto
        language_code: str = "es",
        device: str = "desktop",
        depth: int = 100,
    ) -> dict:
        """
        Lanza una petición SERP en tiempo real y devuelve el resultado completo.

        Retorna el dict con:
          own_position   — posición del dominio propio (None si no aparece)
          own_url        — URL del resultado propio
          competitors    — lista de {domain, position, url}
          raw            — respuesta completa de la API
        """
        payload = [
            {
                "keyword": keyword,
                "location_code": location_code,
                "language_code": language_code,
                "device": device,
                "depth": depth,
            }
        ]

        response = self._session.post(SERP_ENDPOINT, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        if data.get("status_code") != 20000:
            raise RuntimeError(
                f"DataForSEO error {data.get('status_code')}: {data.get('status_message')}"
            )

        task = data["tasks"][0]
        if task.get("status_code") != 20000:
            raise RuntimeError(
                f"DataForSEO task error {task.get('status_code')}: {task.get('status_message')}"
            )

        items = task.get("result", [{}])[0].get("items", [])
        return self._parse_items(items, raw=data)

    def _parse_items(self, items: list, raw: dict) -> dict:
        """Extrae posición propia y competidores de la lista de resultados SERP."""
        own_domain = None  # se resuelve en la task con el dominio del proyecto
        competitors: list[dict] = []

        organic_items = [i for i in items if i.get("type") == "organic"]

        for item in organic_items:
            domain = item.get("domain", "")
            position = item.get("rank_absolute")
            url = item.get("url", "")
            competitors.append({"domain": domain, "position": position, "url": url})

        return {
            "competitors": competitors,
            "raw": raw,
        }

    def fetch_serp_for_project(
        self,
        keyword: str,
        own_domain: str,
        location_code: int = 2724,
        language_code: str = "es",
        device: str = "desktop",
    ) -> dict:
        """
        Como `fetch_serp` pero filtra la posición del dominio propio del resultado.

        Retorna:
          own_position, own_url, competitors, raw
        """
        result = self.fetch_serp(
            keyword=keyword,
            location_code=location_code,
            language_code=language_code,
            device=device,
        )

        own_position: Optional[int] = None
        own_url: Optional[str] = None
        competitor_list: list[dict] = []

        for item in result["competitors"]:
            domain = item["domain"]
            if own_domain in domain or domain in own_domain:
                own_position = item["position"]
                own_url = item["url"]
            else:
                competitor_list.append(item)

        return {
            "own_position": own_position,
            "own_url": own_url,
            "competitors": competitor_list,
            "raw": result["raw"],
        }
