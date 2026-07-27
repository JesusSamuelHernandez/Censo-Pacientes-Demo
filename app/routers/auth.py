"""Router de autenticación: login y autoservicio de acceso."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import (
    UsuarioActivo,
    autenticar_usuario,
    create_access_token,
    hash_password,
    require_cualquier_rol,
)
from app.database import get_db
from app.email_service import enviar_correo_acceso
from app.models import Usuario, UsuarioPreautorizado
from app.rate_limit import limiter
from app.schemas import SolicitarAccesoRequest, SolicitarAccesoResponse, TokenResponse
from app.services.utils import _generar_password_temporal

router = APIRouter(tags=["Autenticación"])

# Ventana mínima entre solicitudes de acceso para una misma cuenta pendiente.
# Evita que una solicitud anónima repetida invalide continuamente la
# contraseña temporal más reciente antes de que la persona alcance a usarla.
SOLICITUD_ACCESO_COOLDOWN = timedelta(minutes=5)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Inicio de sesión — devuelve JWT + rol del usuario.",
)
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    usuario = autenticar_usuario(
        email=form_data.username,
        password=form_data.password,
        db=db,
    )
    token = create_access_token(usuario)
    return TokenResponse(
        access_token=token,
        rol_nombre=usuario.rol_nombre,
        id_usuario=usuario.id_usuario,
        debe_cambiar_password=usuario.debe_cambiar_password,
        email=usuario.email,
        nombre_usuario=usuario.nombre_usuario,
        clues_unidad_asignada=usuario.clues_unidad_asignada,
        nombre_unidad=(
            usuario.unidad_asignada.nombre_de_la_unidad
            if usuario.unidad_asignada else None
        ),
        id_entidad=usuario.id_entidad,
    )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cierra la sesión: invalida en el servidor todos los tokens emitidos para esta cuenta.",
)
def logout(
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    """
    Incrementa token_version en BD, así que el JWT usado en esta misma
    llamada (y cualquier otro token ya emitido para esta cuenta) deja de
    ser válido de inmediato en get_current_user, sin esperar a su exp.
    """
    usuario = db.query(Usuario).filter(Usuario.id_usuario == current_user.id_usuario).first()
    usuario.token_version += 1
    db.commit()


@router.post(
    "/auth/solicitar-acceso",
    response_model=SolicitarAccesoResponse,
    summary="Autoservicio de alta — envía password temporal por correo si el email está preautorizado.",
)
@limiter.limit("3/hour")
def solicitar_acceso(
    request: Request,
    payload: SolicitarAccesoRequest,
    db: Session = Depends(get_db),
):
    """
    Sin autenticación, como /auth/login. Responde siempre el mismo mensaje
    genérico, sin importar el caso (no revela qué correos están
    preautorizados ni si una cuenta ya existe — evita enumeración).
    """
    email = str(payload.email).strip().lower()

    preautorizado = (
        db.query(UsuarioPreautorizado)
        .filter(func.lower(UsuarioPreautorizado.email) == email)
        .first()
    )

    if preautorizado:
        usuario = db.query(Usuario).filter(func.lower(Usuario.email) == email).first()
        ahora = datetime.now(timezone.utc)

        if usuario is None:
            # El correo se intenta ANTES de escribir en BD: si falla, no queda
            # una cuenta con una contraseña que nadie recibió.
            password_temporal = _generar_password_temporal()
            if enviar_correo_acceso(email, password_temporal):
                usuario = Usuario(
                    nombre_usuario=None,
                    email=email,
                    hashed_password=hash_password(password_temporal),
                    rol_nombre=preautorizado.rol_nombre,
                    clues_unidad_asignada=preautorizado.clues_unidad_asignada,
                    id_entidad=preautorizado.id_entidad,
                    debe_cambiar_password=True,
                    fecha_ultima_solicitud_acceso=ahora,
                )
                db.add(usuario)
                db.commit()

        elif usuario.debe_cambiar_password:
            # Cuenta creada pero pendiente de primer login. Si ya se emitió una
            # contraseña temporal hace poco, no se rota de nuevo: evita que una
            # solicitud anónima repetida invalide continuamente la credencial
            # más reciente antes de que la persona alcance a usarla.
            solicitud_reciente = (
                usuario.fecha_ultima_solicitud_acceso is not None
                and ahora - usuario.fecha_ultima_solicitud_acceso < SOLICITUD_ACCESO_COOLDOWN
            )
            if not solicitud_reciente:
                password_temporal = _generar_password_temporal()
                if enviar_correo_acceso(email, password_temporal):
                    usuario.hashed_password = hash_password(password_temporal)
                    usuario.fecha_ultima_solicitud_acceso = ahora
                    usuario.token_version += 1
                    db.commit()
        # Si la cuenta ya está activa (debe_cambiar_password=False), no se hace nada.

    return SolicitarAccesoResponse()
