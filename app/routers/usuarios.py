"""Router de usuarios: CRUD de cuentas y cambio de contraseña."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.audit import Accion, registrar_evento
from app.auth import (
    UsuarioActivo,
    create_access_token,
    hash_password,
    require_cualquier_rol,
    require_super_admin,
    verify_password,
)
from app.database import get_db
from app.email_service import enviar_correo_acceso
from app.models import Usuario
from app.schemas import (
    CambiarPasswordRequest,
    CambiarPasswordResponse,
    UsuarioCreate,
    UsuarioCreateResponse,
    UsuarioResponse,
    UsuarioUpdate,
)
from app.services.utils import _generar_password_temporal

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("", response_model=list[UsuarioResponse], summary="Lista de usuarios. Solo SUPER_ADMIN.")
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    return db.query(Usuario).order_by(Usuario.id_usuario).all()


@router.post(
    "",
    response_model=UsuarioCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una cuenta de usuario. Solo SUPER_ADMIN. Devuelve contraseña temporal.",
)
def crear_usuario(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    email = str(payload.email).strip().lower()
    if db.query(Usuario).filter(func.lower(Usuario.email) == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un usuario con email '{email}'.",
        )
    password_temporal = _generar_password_temporal()
    nuevo = Usuario(
        nombre_usuario=None,
        email=email,
        hashed_password=hash_password(password_temporal),
        rol_nombre=payload.rol_nombre,
        clues_unidad_asignada=payload.clues_unidad_asignada,
        id_entidad=payload.id_entidad,
        debe_cambiar_password=True,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    enviar_correo_acceso(nuevo.email, password_temporal)
    registrar_evento(
        db, accion=Accion.USUARIO_CREADO, id_usuario=current_user.id_usuario,
        objeto_tipo="usuario", objeto_id=nuevo.id_usuario,
        detalle=f"rol: {nuevo.rol_nombre}",
    )
    return UsuarioCreateResponse(
        id_usuario=nuevo.id_usuario,
        nombre_usuario=nuevo.nombre_usuario,
        email=nuevo.email,
        rol_nombre=nuevo.rol_nombre,
        clues_unidad_asignada=nuevo.clues_unidad_asignada,
        id_entidad=nuevo.id_entidad,
        debe_cambiar_password=nuevo.debe_cambiar_password,
        password_temporal=password_temporal,
    )


@router.post(
    "/me/cambiar-password",
    response_model=CambiarPasswordResponse,
    summary="Cambiar contraseña propia. Obligatorio tras el primer login.",
)
def cambiar_password(
    payload: CambiarPasswordRequest,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == current_user.id_usuario).first()
    if not verify_password(payload.password_actual, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta.",
        )
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
    db.commit()
    db.refresh(usuario)
    registrar_evento(
        db, accion=Accion.CAMBIO_PASSWORD, id_usuario=current_user.id_usuario,
        objeto_tipo="usuario", objeto_id=usuario.id_usuario, detalle="cambio propio",
    )

    # token_version cambió: el JWT con el que se hizo esta llamada ya quedó
    # invalidado. Se emite uno nuevo para que la sesión pueda continuar.
    nuevo_token = create_access_token(usuario)
    return CambiarPasswordResponse(
        **UsuarioResponse.model_validate(usuario).model_dump(),
        access_token=nuevo_token,
    )


@router.patch(
    "/{id_usuario}",
    response_model=UsuarioResponse,
    summary="Actualizar datos de un usuario. Solo SUPER_ADMIN.",
)
def actualizar_usuario(
    id_usuario: int,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    datos = payload.model_dump(exclude_none=True)
    cambio_password = "password" in datos
    campos_rol = {"rol_nombre", "clues_unidad_asignada", "id_entidad"}
    cambio_rol = campos_rol & datos.keys()

    if cambio_password:
        usuario.hashed_password = hash_password(datos.pop("password"))
        usuario.token_version += 1
    for campo, valor in datos.items():
        setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)

    if cambio_password:
        registrar_evento(
            db, accion=Accion.CAMBIO_PASSWORD, id_usuario=current_user.id_usuario,
            objeto_tipo="usuario", objeto_id=usuario.id_usuario,
            detalle=f"cambiada por SUPER_ADMIN id_usuario={current_user.id_usuario}",
        )
    if cambio_rol:
        registrar_evento(
            db, accion=Accion.CAMBIO_ROL, id_usuario=current_user.id_usuario,
            objeto_tipo="usuario", objeto_id=usuario.id_usuario,
            detalle=f"campos modificados: {sorted(cambio_rol)}",
        )
    return usuario


@router.delete(
    "/{id_usuario}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una cuenta de usuario. Solo SUPER_ADMIN.",
)
def eliminar_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    if id_usuario == current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar su propia cuenta.",
        )
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    db.delete(usuario)
    db.commit()
    registrar_evento(
        db, accion=Accion.USUARIO_ELIMINADO, id_usuario=current_user.id_usuario,
        objeto_tipo="usuario", objeto_id=id_usuario,
    )
