"""Router de médicos: CRUD con RBAC geográfico."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import UsuarioActivo, apply_rbac_filter, require_password_cambiado, require_super_admin
from app.crypto import hash_sha256
from app.database import get_db
from app.models import CatPuesto, Medico, UnidadMedica
from app.schemas import MedicoCreate, MedicoResponse, MedicoUpdate
from app.services.medicos import (
    _medico_to_response,
    _obtener_medico_o_404,
    _verificar_acceso_medico,
)

router = APIRouter(prefix="/medicos", tags=["Médicos"])


@router.get(
    "",
    response_model=list[MedicoResponse],
    summary="Catálogo de médicos filtrado por rol (RBAC).",
)
def listar_medicos(
    clues_adscripcion: str | None = Query(None, description="Filtrar por unidad médica (solo SUPER_ADMIN puede usarlo libremente)."),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    filtro = apply_rbac_filter(current_user)
    query = db.query(Medico).filter(Medico.es_activo == True)

    if filtro.filtrar_por_clues:
        # RESPONSABLE_UNIDAD — solo su unidad, ignora el param opcional
        query = query.filter(Medico.clues_adscripcion == filtro.valor_clues)
    elif filtro.filtrar_por_entidad:
        # ADMIN_ESTATAL — médicos de su estado, con sub-filtro por CLUES opcional
        query = query.join(UnidadMedica, UnidadMedica.clues == Medico.clues_adscripcion).filter(
            UnidadMedica.id_entidad == filtro.valor_entidad
        )
        if clues_adscripcion:
            query = query.filter(Medico.clues_adscripcion == clues_adscripcion.upper())
    else:
        # SUPER_ADMIN — sin restricción, sub-filtro opcional disponible
        if clues_adscripcion:
            query = query.filter(Medico.clues_adscripcion == clues_adscripcion.upper())

    return [_medico_to_response(m) for m in query.all()]


@router.post(
    "",
    response_model=MedicoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un médico. ADMIN_ESTATAL (su estado) o SUPER_ADMIN.",
)
def crear_medico(
    payload: MedicoCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    clues = payload.clues_adscripcion.strip().upper()

    if current_user.es_responsable_unidad:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para registrar médicos. Contacte a su administrador estatal.",
        )
    elif current_user.es_admin_estatal:
        unidad = db.query(UnidadMedica).filter(UnidadMedica.clues == clues).first()
        if not unidad or unidad.id_entidad != current_user.id_entidad:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede registrar médicos en unidades de su estado.",
            )

    cedula_hash = hash_sha256(payload.cedula)
    if db.query(Medico).filter(Medico.cedula_hash == cedula_hash).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un médico con cédula '{payload.cedula}'.",
        )

    curp_hash = hash_sha256(payload.curp)
    if db.query(Medico).filter(Medico.curp_hash == curp_hash).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un médico con CURP '{payload.curp}'.",
        )

    if not db.query(CatPuesto).filter(CatPuesto.codigo == payload.id_puesto).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Puesto '{payload.id_puesto}' no encontrado en el catálogo.",
        )

    nuevo = Medico(
        cedula_hash=cedula_hash,
        nombre_medico=payload.nombre_medico,
        cedula=payload.cedula,
        curp_hash=curp_hash,
        curp=payload.curp,
        id_puesto=payload.id_puesto,
        email=payload.email,
        clues_adscripcion=payload.clues_adscripcion,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return _medico_to_response(nuevo)


@router.get("/{id_medico}", response_model=MedicoResponse, summary="Perfil del médico.")
def obtener_medico(
    id_medico: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    medico = _obtener_medico_o_404(id_medico, db)
    _verificar_acceso_medico(medico, current_user, db)
    return _medico_to_response(medico)


@router.patch(
    "/{id_medico}",
    response_model=MedicoResponse,
    summary="Actualizar datos o dar de baja un médico. Todos los roles con RBAC geográfico.",
)
def actualizar_medico(
    id_medico: int,
    payload: MedicoUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    medico = _obtener_medico_o_404(id_medico, db)
    _verificar_acceso_medico(medico, current_user, db)

    datos = payload.model_dump(exclude_none=True)
    if "nombre_medico" in datos:
        medico.nombre_medico = datos.pop("nombre_medico")
    if "cedula" in datos:
        nueva_cedula = datos.pop("cedula")
        medico.cedula = nueva_cedula
        medico.cedula_hash = hash_sha256(nueva_cedula)
    if "curp" in datos:
        nueva_curp = datos.pop("curp")
        nueva_curp_hash = hash_sha256(nueva_curp)
        duplicado = (
            db.query(Medico)
            .filter(Medico.curp_hash == nueva_curp_hash, Medico.id_medico != medico.id_medico)
            .first()
        )
        if duplicado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un médico con CURP '{nueva_curp}'.",
            )
        medico.curp = nueva_curp
        medico.curp_hash = nueva_curp_hash
    if "id_puesto" in datos:
        if not db.query(CatPuesto).filter(CatPuesto.codigo == datos["id_puesto"]).first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Puesto '{datos['id_puesto']}' no encontrado en el catálogo.",
            )
    for campo, valor in datos.items():
        setattr(medico, campo, valor)
    db.commit()
    db.refresh(medico)
    return _medico_to_response(medico)


@router.delete(
    "/{id_medico}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un médico. Solo SUPER_ADMIN.",
)
def eliminar_medico(
    id_medico: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    medico = _obtener_medico_o_404(id_medico, db)
    db.delete(medico)
    db.commit()
