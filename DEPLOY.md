# Despliegue en EasyPanel (VPS propio)

Esta guía despliega Rank Tracker (API + worker + beat + frontend) usando
EasyPanel sobre un VPS, a partir de las imágenes Docker de este repo.

## Arquitectura de servicios

| Servicio EasyPanel | Origen | Dominio público | Notas |
|---|---|---|---|
| `mysql`    | plantilla EasyPanel (MySQL 8) | — | volumen persistente |
| `redis`    | plantilla EasyPanel (Redis) | — | volumen persistente |
| `api`      | `Dockerfile` (raíz del repo), `APP_MODE=api` | `api.tudominio.com` | |
| `worker`   | mismo `Dockerfile`, `APP_MODE=worker` | — | |
| `beat`     | mismo `Dockerfile`, `APP_MODE=beat` | — | **una sola réplica** |
| `frontend` | `frontend/Dockerfile` | `app.tudominio.com` | |

`api`, `worker` y `beat` comparten la misma imagen — el script `entrypoint.sh`
decide qué proceso arrancar según `APP_MODE`, y siempre ejecuta primero
`python -m core.init_db` para crear/actualizar el esquema de MySQL
(idempotente, seguro desde varios contenedores a la vez).

## 0. Prerrequisitos

- VPS con EasyPanel instalado y un dominio (o subdominios) apuntando a su IP.
- Repo en GitHub: `https://github.com/buenroger/ranktracker` (o tu fork).
- Credenciales de DataForSEO (login/password de tu cuenta).
- Si vas a usar Google Search Console: ver sección 9 (`gsc_token.json`),
  generado **una sola vez en local**.

## 1. Servicio MySQL

1. EasyPanel → **+ Service → Templates → MySQL**.
2. Asigna nombre (p. ej. `ranktracker-mysql`), establece la contraseña root.
3. Crea una base de datos `ranktracker`, usuario `ranktracker` y su
   contraseña (o usa root, pero un usuario dedicado es más seguro).
4. Anota el **nombre interno del servicio** (EasyPanel resuelve los
   contenedores por nombre, p. ej. `ranktracker-mysql`); lo usarás como
   `DB_HOST`.
5. Activa volumen persistente (viene por defecto en la plantilla).

## 2. Servicio Redis

1. EasyPanel → **+ Service → Templates → Redis**.
2. Nombre, p. ej. `ranktracker-redis`. Sin contraseña es suficiente si está
   en la red interna de EasyPanel (no expongas el puerto públicamente).
3. Anota el nombre interno del servicio → lo usarás en `REDIS_URL`.

## 3. Servicio `api`

1. EasyPanel → **+ Service → App → From Git Repository**.
2. Repo: `https://github.com/buenroger/ranktracker`, rama `main`.
3. Build: **Dockerfile** (usa el `Dockerfile` de la raíz).
4. Puerto del contenedor: `8000`.
5. Variables de entorno:

   ```
   APP_MODE=api
   DB_HOST=ranktracker-mysql
   DB_PORT=3306
   DB_NAME=ranktracker
   DB_USER=ranktracker
   DB_PASSWORD=<password elegido en paso 1>
   REDIS_URL=redis://ranktracker-redis:6379/0
   DATAFORSEO_LOGIN=<tu login>
   DATAFORSEO_PASSWORD=<tu password>
   GSC_CREDENTIALS_FILE=/app/secrets/gsc_credentials.json
   GSC_TOKEN_FILE=/app/secrets/gsc_token.json
   GSC_LOOKBACK_DAYS=3
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=<tu cuenta gmail>
   SMTP_PASSWORD=<app password>
   ALERT_FROM_EMAIL=ranktracker@tudominio.com
   CORS_ORIGINS=["https://app.tudominio.com"]
   DEBUG=false
   APP_ENV=production
   ```

   (sustituye `ranktracker-mysql` / `ranktracker-redis` por los nombres
   internos reales de los servicios creados en los pasos 1 y 2).

6. **Volumen**: monta un volumen persistente en `/app/secrets` (compartirás
   este volumen con `worker` y `beat` para `gsc_credentials.json` /
   `gsc_token.json` — ver sección 9).
7. Dominio: añade `api.tudominio.com` apuntando al puerto `8000`, con HTTPS
   (Let's Encrypt automático de EasyPanel).
8. Despliega y comprueba `https://api.tudominio.com/health` → `{"status":"ok"}`
   y `https://api.tudominio.com/docs`.

## 4. Servicio `worker`

1. Igual que `api`: mismo repo, mismo `Dockerfile`.
2. Variables de entorno: **idénticas** a `api`, pero `APP_MODE=worker`.
3. Mismo volumen persistente montado en `/app/secrets` (read-only o
   read-write, debe poder leer `gsc_token.json`; si quieres que el refresco
   automático del token se persista, móntalo en read-write).
4. Sin dominio público.

## 5. Servicio `beat`

1. Igual que `api`/`worker`, `APP_MODE=beat`.
2. Mismas variables de entorno y volumen `/app/secrets`.
3. **Importante**: configura **réplicas = 1**. Celery Beat no debe correr
   duplicado o se programarán tareas repetidas.
4. Sin dominio público.

## 6. Servicio `frontend`

1. EasyPanel → **+ Service → App → From Git Repository**, mismo repo.
2. Build: **Dockerfile**, ruta `frontend/Dockerfile` (contexto de build:
   `frontend/`).
3. Build arg:

   ```
   VITE_API_URL=https://api.tudominio.com
   ```

   (Vite incrusta esta URL en el bundle en tiempo de build — si la cambias,
   tienes que reconstruir la imagen).
4. Puerto del contenedor: `80`.
5. Dominio: `app.tudominio.com`, con HTTPS.
6. Despliega y comprueba que `https://app.tudominio.com` carga el dashboard
   y las llamadas a la API funcionan (pestaña Network del navegador).

## 7. CORS

Asegúrate de que `CORS_ORIGINS` en `api`/`worker`/`beat` incluye el dominio
real del frontend (`https://app.tudominio.com`), si no las peticiones del
navegador serán bloqueadas.

## 8. Proteger el acceso (HTTP Basic Auth)

Como es un panel de uso personal expuesto a internet, activa **Basic Auth**
a nivel de proxy en EasyPanel para los dominios `api.tudominio.com` y
`app.tudominio.com`:

1. En la configuración de cada servicio (`api` y `frontend`) → pestaña
   **Domains/Proxy** → middleware de **Basic Auth** (Traefik).
2. Define usuario/contraseña. Esto protege tanto el dashboard como
   `/docs` y los endpoints de la API sin tocar código.

## 9. Google Search Console — token (configuración única)

1. En local (con navegador): crea credenciales OAuth2 tipo "Desktop app" en
   Google Cloud Console y descárgalas como `gsc_credentials.json`.
2. En "OAuth consent screen", pon la app en estado **"In production"**
   (no "Testing") — con scope de solo lectura y uso personal no requiere
   verificación de Google. Esto evita que el `refresh_token` caduque cada
   7 días.
3. Ejecuta en local:

   ```bash
   pip install -r requirements.txt
   python scripts/gsc_auth.py
   ```

   Esto abre el navegador, completas el login y se genera `gsc_token.json`.
4. Sube **ambos ficheros** (`gsc_credentials.json` y `gsc_token.json`) al
   volumen `/app/secrets` del servicio `api` (usa el gestor de archivos de
   EasyPanel o `docker cp` al contenedor/volumen). El mismo volumen debe
   estar montado en `worker` y `beat`.
5. A partir de aquí el token se renueva solo indefinidamente — no hace falta
   repetir este proceso.

## 10. Verificación final

- `curl https://api.tudominio.com/health` → `{"status":"ok"}`.
- `https://app.tudominio.com` carga el dashboard, lista proyectos.
- Crea un proyecto desde el dashboard (botón "Nuevo proyecto"), añade
  keywords, dispara "Ingestar ahora" y comprueba en los logs de `worker`
  que procesa las tareas de DataForSEO.
- Si configuraste GSC: `POST /ingest/projects/{id}/gsc` (vía `/docs` o
  desde el dashboard) y comprueba filas con `source='gsc'` en `rankings`.
- Logs de `beat`: confirma que las tareas programadas (`gsc-daily-06:00`,
  `dataforseo-daily-07:00`, `alerts-hourly`) se disparan a su hora.

## 11. Mantenimiento

- **Redeploy**: cualquier push a `main` puede configurarse para
  auto-redeploy en EasyPanel (webhook de GitHub).
- **Backups**: programa copias del volumen de `mysql` (EasyPanel permite
  backups de volúmenes, o usa `mysqldump` vía cron en el propio contenedor).
- **Logs**: cada servicio tiene su pestaña de logs en EasyPanel — útil para
  depurar Celery (`worker`/`beat`) y errores de la API.
