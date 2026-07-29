"""
Servicio de tokens de activación de cuenta (SAST-14).

Reemplaza la contraseña temporal reutilizable enviada por correo por un
enlace de un solo uso con expiración corta: la cuenta se crea con una
contraseña placeholder que nadie conoce (login imposible hasta activar), y
`crear_token_activacion` emite el token real que se manda por correo.
"""
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.crypto import hash_token
from app.models import TokenActivacion, Usuario

TTL_ACTIVACION = timedelta(hours=48)


def crear_token_activacion(db: Session, usuario: Usuario) -> str:
    """
    Genera un token de activación de un solo uso para `usuario` e invalida
    cualquier token pendiente anterior de la misma cuenta, para que solo el
    enlace más reciente sea válido. Devuelve el token en texto plano — solo
    vive en memoria para el envío del correo, nunca se persiste así.

    No hace commit: el llamador decide cuándo confirmar la transacción
    (algunos flujos solo deben persistir si el correo se envía con éxito).
    """
    ahora = datetime.now(timezone.utc)
    db.query(TokenActivacion).filter(
        TokenActivacion.id_usuario == usuario.id_usuario,
        TokenActivacion.usado_en.is_(None),
    ).update({"usado_en": ahora})

    token = secrets.token_urlsafe(32)
    activacion = TokenActivacion(
        id_usuario=usuario.id_usuario,
        token_hash=hash_token(token),
        expira_en=ahora + TTL_ACTIVACION,
    )
    db.add(activacion)
    db.flush()
    return token


def obtener_activacion_valida(db: Session, token: str) -> TokenActivacion | None:
    """
    Busca el token de activación por su hash y lo devuelve solo si existe,
    no ha sido usado y no ha expirado. No lo marca como usado — eso lo hace
    el llamador junto con el resto de los cambios, en el mismo commit, para
    no invalidar el enlace si una validación posterior (ej. nombre de
    usuario faltante) rechaza la solicitud.
    """
    ahora = datetime.now(timezone.utc)
    activacion = (
        db.query(TokenActivacion)
        .filter(TokenActivacion.token_hash == hash_token(token))
        .first()
    )
    if activacion is None or activacion.usado_en is not None or activacion.expira_en <= ahora:
        return None
    return activacion
