"""
main.py — Punto de entrada de la API.

Configura la instancia FastAPI, CORS, el endpoint de salud y registra
los routers de cada dominio. La lógica de negocio vive en:
  - app/routers/   → endpoints HTTP por dominio
  - app/services/  → helpers puros (sin HTTP)
  - app/schemas/   → validación Pydantic
  - app/models/    → tablas ORM SQLAlchemy
"""
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db  # re-exportado: usado en tests (main.get_db)
from app.rate_limit import limiter
from app.routers import (
    auth,
    catalogos,
    medicos,
    notificaciones,
    pacientes,
    registros,
    reportes,
    usuarios,
)

# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------
app = FastAPI(
    title="API — Medicamentos de Alto Costo",
    description=(
        "Backend para el censo de pacientes y prescripción de medicamentos de alto "
        "costo. Implementa RBAC con tres niveles: SUPER_ADMIN, ADMIN_ESTATAL y "
        "RESPONSABLE_UNIDAD."
    ),
    version="3.0.0",
)

# ---------------------------------------------------------------------------
# Rate limiting (SAST-04) — throttling por IP en endpoints públicos de auth.
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
FRONTEND_URL = os.getenv("FRONTEND_URL", "")
allowed_origins = [url.strip() for url in FRONTEND_URL.split(",") if url.strip()]

if not allowed_origins:
    raise RuntimeError(
        "Variable de entorno FRONTEND_URL no definida. "
        "Configura los origenes permitidos separados por coma."
    )

print(f"OK CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(pacientes.router)
app.include_router(medicos.router)
app.include_router(registros.router)
app.include_router(notificaciones.router)
app.include_router(reportes.router)
app.include_router(catalogos.router)
app.include_router(usuarios.router)

# ---------------------------------------------------------------------------
# Salud
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Sistema"], summary="Verifica la salud de la API y la base de datos.")
def healthcheck(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}