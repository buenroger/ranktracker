"""
Punto de entrada de la API REST del Rank Tracker.

Arrancar en desarrollo:
    uvicorn api.main:app --reload --port 8000

Arrancar en producción:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

Documentación interactiva (Swagger):
    http://localhost:8000/docs

Documentación alternativa (ReDoc):
    http://localhost:8000/redoc
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import projects, keywords, competitors, alerts, ingest
from config.settings import settings

app = FastAPI(
    title="Rank Tracker API",
    description="API REST para rastreo de posiciones SEO con Search Console y DataForSEO.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(projects.router)
app.include_router(keywords.global_router)
app.include_router(keywords.project_router)
app.include_router(competitors.router)
app.include_router(alerts.router)
app.include_router(ingest.router)


@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}
