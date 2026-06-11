"""
Generación única (one-time) del token OAuth2 de Google Search Console.

Ejecuta este script EN LOCAL (necesitas un navegador) para generar
`gsc_token.json`. Luego sube ese fichero al volumen persistente del
servicio `api`/`worker`/`beat` en producción y no tendrás que repetir
este proceso (el cliente refresca el token automáticamente).

Requisitos previos:
  1. Crea credenciales OAuth2 de tipo "Desktop app" en Google Cloud Console
     y descárgalas como `gsc_credentials.json` (junto a este script o en la
     ruta indicada por GSC_CREDENTIALS_FILE).
  2. En "OAuth consent screen", publica la app en estado "In production"
     (no "Testing"). Con el scope de solo lectura usado aquí no requiere
     verificación de Google para uso personal — solo aceptarás el aviso de
     "app no verificada" la primera vez. Esto evita que el refresh_token
     caduque cada 7 días.

Uso:
    python scripts/gsc_auth.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow

from config.settings import settings


def main() -> None:
    creds_path = Path(settings.gsc_credentials_file)
    token_path = Path(settings.gsc_token_file)

    if not creds_path.exists():
        raise SystemExit(
            f"No se encuentra '{creds_path}'. Descárgalo desde Google Cloud "
            "Console (credenciales OAuth2 tipo 'Desktop app')."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(creds_path), settings.gsc_scopes
    )
    # access_type=offline asegura que Google devuelva un refresh_token.
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"Token guardado en '{token_path}'.")
    print("Sube este fichero al volumen persistente del servicio en producción")
    print("y apunta GSC_TOKEN_FILE a su ruta. No vuelvas a ejecutar este script")
    print("salvo que el token sea revocado.")


if __name__ == "__main__":
    main()
