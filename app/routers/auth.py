"""Router de autenticación: login y autoservicio de acceso."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.audit import Accion, Resultado, ip_de_request, registrar_evento
from app.auth import (
    UsuarioActivo,
    autenticar_usuario,
    create_access_token,
    hash_password,
    require_cualquier_rol,
)
from app.database import get_db
from app.email_service import enviar_correo_activacion
from app.models import Usuario, UsuarioPreautorizado
from app.rate_limit import limiter
from app.schemas import (
    ActivarCuentaRequest,
    SolicitarAccesoRequest,
    SolicitarAccesoResponse,
    TokenResponse,
)
from app.services.activacion import crear_token_activacion, obtener_activacion_valida
from app.services.utils import _generar_password_placeholder

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
    ip = ip_de_request(request)
    try:
        usuario = autenticar_usuario(
            email=form_data.username,
            password=form_data.password,
            db=db,
        )
    except HTTPException:
        registrar_evento(
            db, accion=Accion.LOGIN_FALLIDO, resultado=Resultado.FALLO,
            ip_origen=ip, detalle=f"email intentado: {form_data.username.strip().lower()}",
        )
        raise

    token = create_access_token(usuario)
    registrar_evento(
        db, accion=Accion.LOGIN_EXITOSO, resultado=Resultado.EXITO,
        id_usuario=usuario.id_usuario, ip_origen=ip,
    )
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
    request: Request,
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
    registrar_evento(
        db, accion=Accion.LOGOUT, id_usuario=current_user.id_usuario,
        ip_origen=ip_de_request(request),
    )


@router.post(
    "/auth/solicitar-acceso",
    response_model=SolicitarAccesoResponse,
    summary="Autoservicio de alta — envía un enlace de activación por correo si el email está preautorizado.",
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
            # El correo se intenta ANTES de comprometer la transacción: si
            # falla, no queda una cuenta con un enlace que nadie recibió.
            nuevo = Usuario(
                nombre_usuario=None,
                email=email,
                hashed_password=hash_password(_generar_password_placeholder()),
                rol_nombre=preautorizado.rol_nombre,
                clues_unidad_asignada=preautorizado.clues_unidad_asignada,
                id_entidad=preautorizado.id_entidad,
                debe_cambiar_password=True,
                fecha_ultima_solicitud_acceso=ahora,
            )
            db.add(nuevo)
            db.flush()
            token = crear_token_activacion(db, nuevo)
            if enviar_correo_activacion(email, token):
                db.commit()
            else:
                db.rollback()

        elif usuario.debe_cambiar_password:
            # Cuenta creada pero pendiente de activación. Si ya se emitió un
            # enlace hace poco, no se rota de nuevo: evita que una solicitud
            # anónima repetida invalide continuamente el enlace más reciente
            # antes de que la persona alcance a usarlo.
            solicitud_reciente = (
                usuario.fecha_ultima_solicitud_acceso is not None
                and ahora - usuario.fecha_ultima_solicitud_acceso < SOLICITUD_ACCESO_COOLDOWN
            )
            if not solicitud_reciente:
                token = crear_token_activacion(db, usuario)
                if enviar_correo_activacion(email, token):
                    usuario.fecha_ultima_solicitud_acceso = ahora
                    db.commit()
                else:
                    db.rollback()
        # Si la cuenta ya está activa (debe_cambiar_password=False), no se hace nada.

    return SolicitarAccesoResponse()


@router.post(
    "/auth/activar",
    response_model=TokenResponse,
    summary="Activa la cuenta con el enlace del correo y establece la contraseña definitiva.",
)
@limiter.limit("10/minute")
def activar_cuenta(
    request: Request,
    payload: ActivarCuentaRequest,
    db: Session = Depends(get_db),
):
    """
    Sin autenticación: el token del correo hace las veces de credencial.
    Sustituye a la contraseña temporal reutilizable — el token es de un
    solo uso y expira a las 48h (SAST-14). Al activarse con éxito, deja la
    sesión iniciada (mismo shape que /auth/login) para no pedir un login
    adicional inmediatamente después.
    """
    ip = ip_de_request(request)
    activacion = obtener_activacion_valida(db, payload.token)
    if activacion is None:
        registrar_evento(
            db, accion=Accion.ACTIVACION_FALLIDA, resultado=Resultado.FALLO,
            ip_origen=ip, detalle="token invalido, usado o expirado",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de activación no es válido o ya expiró. Solicita uno nuevo.",
        )

    usuario = activacion.usuario
    if usuario.nombre_usuario is None:
        if not payload.nombre_usuario or not payload.nombre_usuario.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes indicar tu nombre de usuario.",
            )
        usuario.nombre_usuario = payload.nombre_usuario.strip()
    elif payload.nombre_usuario and payload.nombre_usuario.strip():
        usuario.nombre_usuario = payload.nombre_usuario.strip()

    usuario.hashed_password = hash_password(payload.password_nueva)
    usuario.debe_cambiar_password = False
    usuario.token_version += 1
    activacion.usado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(usuario)

    registrar_evento(
        db, accion=Accion.CUENTA_ACTIVADA, id_usuario=usuario.id_usuario, ip_origen=ip,
    )

    nuevo_token = create_access_token(usuario)
    return TokenResponse(
        access_token=nuevo_token,
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
