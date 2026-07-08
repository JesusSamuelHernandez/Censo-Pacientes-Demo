"""Router de autenticación: login y autoservicio de acceso."""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import autenticar_usuario, create_access_token, hash_password
from app.database import get_db
from app.email_service import enviar_correo_acceso
from app.models import Usuario, UsuarioPreautorizado
from app.schemas import SolicitarAccesoRequest, SolicitarAccesoResponse, TokenResponse
from app.services.utils import _generar_password_temporal

router = APIRouter(tags=["Autenticación"])


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Inicio de sesión — devuelve JWT + rol del usuario.",
)
def login(
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
    "/auth/solicitar-acceso",
    response_model=SolicitarAccesoResponse,
    summary="Autoservicio de alta — envía password temporal por correo si el email está preautorizado.",
)
def solicitar_acceso(
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

        if usuario is None:
            password_temporal = _generar_password_temporal()
            usuario = Usuario(
                nombre_usuario=None,
                email=email,
                hashed_password=hash_password(password_temporal),
                rol_nombre=preautorizado.rol_nombre,
                clues_unidad_asignada=preautorizado.clues_unidad_asignada,
                id_entidad=preautorizado.id_entidad,
                debe_cambiar_password=True,
            )
            db.add(usuario)
            db.commit()
            enviar_correo_acceso(email, password_temporal)
        elif usuario.debe_cambiar_password:
            # Cuenta creada pero pendiente de primer login — reenvía un nuevo
            # password temporal (por si la persona perdió el correo original).
            password_temporal = _generar_password_temporal()
            usuario.hashed_password = hash_password(password_temporal)
            db.commit()
            enviar_correo_acceso(email, password_temporal)
        # Si la cuenta ya está activa (debe_cambiar_password=False), no se hace nada.

    return SolicitarAccesoResponse()
