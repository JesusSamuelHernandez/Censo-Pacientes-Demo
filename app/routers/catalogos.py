"""Router de catálogos: diagnósticos, puestos, medicamentos y unidades médicas."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import UsuarioActivo, require_password_cambiado, require_super_admin
from app.config import UNIDAD_MEDICAMENTOS_HABILITADO
from app.database import get_db
from app.models import CatDiagnostico, CatMedicamento, CatPuesto, UnidadMedica, UnidadMedicamento
from app.schemas import (
    DiagnosticoCreate,
    DiagnosticoResponse,
    DiagnosticoUpdate,
    MedicamentoCreate,
    MedicamentoResponse,
    MedicamentoUpdate,
    PuestoResponse,
    UnidadMedicaCreate,
    UnidadMedicaResponse,
    UnidadMedicaUpdate,
)

router = APIRouter(prefix="/catalogos", tags=["Catálogos"])


# ---------------------------------------------------------------------------
# Diagnósticos
# ---------------------------------------------------------------------------

@router.get(
    "/diagnosticos",
    response_model=list[DiagnosticoResponse],
    summary="Lista del catálogo de diagnósticos.",
)
def listar_diagnosticos(
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    query = db.query(CatDiagnostico)
    if solo_activos:
        query = query.filter(CatDiagnostico.es_activo == True)
    return query.order_by(CatDiagnostico.nombre).all()


@router.post(
    "/diagnosticos",
    response_model=DiagnosticoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo diagnóstico en el catálogo. Solo SUPER_ADMIN.",
)
def crear_diagnostico(
    payload: DiagnosticoCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    if db.query(CatDiagnostico).filter(CatDiagnostico.nombre == payload.nombre).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un diagnóstico con el nombre '{payload.nombre}'.",
        )
    nuevo = CatDiagnostico(**payload.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.patch(
    "/diagnosticos/{id_diagnostico}",
    response_model=DiagnosticoResponse,
    summary="Actualizar o desactivar un diagnóstico. Solo SUPER_ADMIN.",
)
def actualizar_diagnostico(
    id_diagnostico: int,
    payload: DiagnosticoUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    diag = db.query(CatDiagnostico).filter(CatDiagnostico.id_diagnostico == id_diagnostico).first()
    if not diag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnóstico no encontrado.")
    for campo, valor in payload.model_dump(exclude_none=True).items():
        setattr(diag, campo, valor)
    db.commit()
    db.refresh(diag)
    return diag


# ---------------------------------------------------------------------------
# Puestos
# ---------------------------------------------------------------------------

@router.get(
    "/puestos",
    response_model=list[PuestoResponse],
    summary="Lista del catálogo de puestos/especialidades médicas.",
)
def listar_puestos(
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    query = db.query(CatPuesto)
    if solo_activos:
        query = query.filter(CatPuesto.es_activo == True)
    return query.order_by(CatPuesto.denominacion_puesto).all()


# ---------------------------------------------------------------------------
# Medicamentos
# ---------------------------------------------------------------------------

@router.get(
    "/medicamentos",
    response_model=list[MedicamentoResponse],
    summary="Lista del catálogo oficial de medicamentos.",
)
def listar_medicamentos(
    solo_activos: bool = Query(True),
    clues: str | None = Query(None, description="Si se indica, devuelve solo medicamentos asignados a esa unidad."),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    query = db.query(CatMedicamento)
    if solo_activos:
        query = query.filter(CatMedicamento.es_activo == True)
    if UNIDAD_MEDICAMENTOS_HABILITADO and clues:
        query = query.join(
            UnidadMedicamento,
            UnidadMedicamento.clave_cnis == CatMedicamento.clave_cnis,
        ).filter(UnidadMedicamento.clues == clues)
    return query.order_by(CatMedicamento.clave_cnis).all()


@router.post(
    "/medicamentos",
    response_model=MedicamentoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar una nueva clave CNIS. Solo SUPER_ADMIN.",
)
def crear_medicamento(
    payload: MedicamentoCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    if db.query(CatMedicamento).filter(
        CatMedicamento.clave_cnis == payload.clave_cnis
    ).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un medicamento con clave CNIS '{payload.clave_cnis}'.",
        )
    nuevo = CatMedicamento(**payload.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.patch(
    "/medicamentos/{clave_cnis}",
    response_model=MedicamentoResponse,
    summary="Actualizar o desactivar un medicamento. Solo SUPER_ADMIN.",
)
def actualizar_medicamento(
    clave_cnis: str,
    payload: MedicamentoUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    medicamento = db.query(CatMedicamento).filter(
        CatMedicamento.clave_cnis == clave_cnis
    ).first()
    if not medicamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicamento no encontrado.")
    for campo, valor in payload.model_dump(exclude_none=True).items():
        setattr(medicamento, campo, valor)
    db.commit()
    db.refresh(medicamento)
    return medicamento


# ---------------------------------------------------------------------------
# Unidades Médicas
# ---------------------------------------------------------------------------

@router.get(
    "/unidades",
    response_model=list[UnidadMedicaResponse],
    summary="Lista de unidades médicas.",
)
def listar_unidades(
    id_entidad: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    query = db.query(UnidadMedica)
    if id_entidad:
        query = query.filter(UnidadMedica.id_entidad == id_entidad)
    return query.order_by(UnidadMedica.id_entidad, UnidadMedica.clues).all()


@router.post(
    "/unidades",
    response_model=UnidadMedicaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva unidad médica. Solo SUPER_ADMIN.",
)
def crear_unidad(
    payload: UnidadMedicaCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    if db.query(UnidadMedica).filter(UnidadMedica.clues == payload.clues).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una unidad con CLUES '{payload.clues}'.",
        )
    nueva = UnidadMedica(**payload.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.patch(
    "/unidades/{clues}",
    response_model=UnidadMedicaResponse,
    summary="Actualizar datos de una unidad médica. Solo SUPER_ADMIN.",
)
def actualizar_unidad(
    clues: str,
    payload: UnidadMedicaUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    unidad = db.query(UnidadMedica).filter(UnidadMedica.clues == clues.upper()).first()
    if not unidad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad médica no encontrada.")
    for campo, valor in payload.model_dump(exclude_none=True).items():
        setattr(unidad, campo, valor)
    db.commit()
    db.refresh(unidad)
    return unidad
