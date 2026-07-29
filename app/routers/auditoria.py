"""Router de auditoría: lectura del audit trail de seguridad. Solo SUPER_ADMIN (SAST-13)."""
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import UsuarioActivo, require_super_admin
from app.database import get_db
from app.models import EventoSeguridad
from app.schemas import EventoSeguridadListResponse, EventoSeguridadResponse

router = APIRouter(prefix="/auditoria", tags=["Auditoría"])


@router.get(
    "/eventos",
    response_model=EventoSeguridadListResponse,
    summary="Consulta el audit trail de seguridad. Solo SUPER_ADMIN.",
)
def listar_eventos_seguridad(
    id_usuario: int | None = Query(None, description="Filtra por el usuario que ejecutó la acción."),
    accion: str | None = Query(None, description="Ej. 'login_fallido', 'acceso_denegado'."),
    fecha_inicio: date | None = Query(None),
    fecha_fin: date | None = Query(None),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    query = db.query(EventoSeguridad)

    if id_usuario is not None:
        query = query.filter(EventoSeguridad.id_usuario == id_usuario)
    if accion is not None:
        query = query.filter(EventoSeguridad.accion == accion)
    if fecha_inicio is not None:
        query = query.filter(
            EventoSeguridad.fecha >= datetime.combine(fecha_inicio, time.min, tzinfo=timezone.utc)
        )
    if fecha_fin is not None:
        query = query.filter(
            EventoSeguridad.fecha <= datetime.combine(fecha_fin, time.max, tzinfo=timezone.utc)
        )

    total = query.count()
    eventos = (
        query.order_by(EventoSeguridad.fecha.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    return EventoSeguridadListResponse(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        resultados=[EventoSeguridadResponse.model_validate(e) for e in eventos],
    )
