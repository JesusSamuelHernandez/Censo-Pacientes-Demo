"""
audit.py — Registro estructurado de eventos de seguridad (SAST-13).

Inserta en `eventos_seguridad` (tabla de solo escritura desde la app: no hay
endpoints de UPDATE/DELETE). Un fallo al registrar un evento NUNCA debe tumbar
la operación que se está auditando — se hace best-effort y se registra en el
logger de la aplicación si falla.

Regla dura: nunca pasar CURP, contraseñas, JWT ni diagnósticos en `detalle`
ni en `objeto_id`. Solo identificadores internos (id_paciente, id_medico,
email institucional) y metadatos de la operación (motivo de rechazo RBAC,
qué campos cambiaron, etc.).
"""
import logging

from sqlalchemy.orm import Session

from app.models import EventoSeguridad

logger = logging.getLogger("app.audit")


class Accion:
    LOGIN_EXITOSO = "login_exitoso"
    LOGIN_FALLIDO = "login_fallido"
    LOGIN_BLOQUEADO = "login_bloqueado"
    LOGOUT = "logout"
    CAMBIO_PASSWORD = "cambio_password"
    CAMBIO_ROL = "cambio_rol"
    USUARIO_CREADO = "usuario_creado"
    USUARIO_ELIMINADO = "usuario_eliminado"
    CUENTA_ACTIVADA = "cuenta_activada"
    ACTIVACION_FALLIDA = "activacion_fallida"
    CONSULTA_PACIENTE = "consulta_paciente"
    CONSULTA_MEDICO = "consulta_medico"
    TRANSFERENCIA_PACIENTE = "transferencia_paciente"
    EXPORTACION = "exportacion"
    ACCESO_DENEGADO = "acceso_denegado"


class Resultado:
    EXITO = "exito"
    FALLO = "fallo"
    DENEGADO = "denegado"


def registrar_evento(
    db: Session,
    *,
    accion: str,
    resultado: str = Resultado.EXITO,
    id_usuario: int | None = None,
    objeto_tipo: str | None = None,
    objeto_id: int | str | None = None,
    ip_origen: str | None = None,
    detalle: str | None = None,
) -> None:
    """
    Inserta un evento de auditoría y confirma la escritura de inmediato.

    Se llama siempre DESPUÉS de que la operación principal ya haya hecho su
    propio commit (o, en endpoints de solo lectura, sin ningún commit
    pendiente antes) — así un fallo al auditar nunca revierte cambios de
    negocio ya confirmados.
    """
    try:
        evento = EventoSeguridad(
            id_usuario=id_usuario,
            accion=accion,
            resultado=resultado,
            objeto_tipo=objeto_tipo,
            objeto_id=str(objeto_id) if objeto_id is not None else None,
            ip_origen=ip_origen,
            detalle=detalle,
        )
        db.add(evento)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("No se pudo registrar evento de auditoria.")


def ip_de_request(request) -> str | None:
    """Extrae la IP del cliente de un objeto Request de FastAPI/Starlette."""
    return request.client.host if request.client else None
