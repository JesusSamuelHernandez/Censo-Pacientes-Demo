"""
main.py — Punto de entrada de la API. Define todos los endpoints del Blueprint.

Módulos cubiertos:
    5.1  /auth/login                      → Autenticación JWT
    5.2  /pacientes                       → Gestión clínica de pacientes
    5.3  /suministros                     → Censo de asignación de tratamiento
    5.4  /reportes/resumen-detallado      → Datos crudos para Excel/PDF
         /reportes/estatal                → Agregados por unidad (Admin Estatal)
    5.5  /catalogos/medicamentos          → Catálogo CNIS (Solo Super Admin)
         /catalogos/unidades              → Unidades médicas (Solo Super Admin)
         /usuarios                        → Cuentas de plataforma (Solo Super Admin)

Soft Delete:
    DELETE /pacientes/{curp}              → es_activo = False  (nunca borra físico)
    DELETE /suministros/{id}              → es_activo = False  (nunca borra físico)

RBAC (Blueprint sección 4):
    apply_rbac_filter() se llama en cada query de datos para garantizar que:
        RESPONSABLE_UNIDAD → solo ve su unidad  (clues_unidad_asignada)
        ADMIN_ESTATAL      → solo ve su estado  (id_entidad)
        SUPER_ADMIN        → sin restricciones
"""
from datetime import date, datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth import (
    UsuarioActivo,
    apply_rbac_filter,
    autenticar_usuario,
    create_access_token,
    hash_password,
    require_admin_estatal_o_superior,
    require_cualquier_rol,
    require_super_admin,
)
from app.database import engine, get_db
from app.models import Base, CatMedicamento, Paciente, Suministro, UnidadMedica, Usuario
from app.schemas import (
    LoginRequest,
    MedicamentoCreate,
    MedicamentoResponse,
    MedicamentoUpdate,
    PacienteCreate,
    PacienteListResponse,
    PacienteResponse,
    PacienteUpdate,
    SuministroCreate,
    SuministroListResponse,
    SuministroResponse,
    SuministroUpdate,
    TokenResponse,
    UnidadMedicaCreate,
    UnidadMedicaResponse,
    UnidadMedicaUpdate,
    UsuarioCreate,
    UsuarioResponse,
    UsuarioUpdate,
)

# ---------------------------------------------------------------------------
# Inicialización
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)  # Crea tablas si no existen (desarrollo).

app = FastAPI(
    title="API — Medicamentos de Alto Costo",
    description=(
        "Backend para el censo de pacientes y asignación de medicamentos de alto "
        "costo. Implementa RBAC con tres niveles: SUPER_ADMIN, ADMIN_ESTATAL y "
        "RESPONSABLE_UNIDAD."
    ),
    version="1.0.0",
)


# ===========================================================================
# 5.1  AUTENTICACIÓN
# ===========================================================================

@app.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["5.1 Autenticación"],
    summary="Inicio de sesión — devuelve JWT + rol del usuario.",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Recibe credenciales (email + password), valida contra la BD y entrega:
      - access_token : JWT firmado con claims RBAC.
      - token_type   : "bearer"
      - rol_nombre   : rol del usuario autenticado.
      - id_usuario   : PK del usuario.
    """
    # OAuth2PasswordRequestForm envía el email en el campo 'username'.
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
    )


# ===========================================================================
# 5.2  PACIENTES
# ===========================================================================

@app.get(
    "/pacientes",
    response_model=PacienteListResponse,
    tags=["5.2 Pacientes"],
    summary="Lista de pacientes filtrada automáticamente por rol.",
)
def listar_pacientes(
    solo_activos: bool = Query(True, description="False para incluir pacientes dados de baja."),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    """
    RBAC automático (Blueprint §4):
      - RESPONSABLE_UNIDAD → WHERE clues_unidad_adscripcion = su CLUES.
      - ADMIN_ESTATAL      → JOIN unidades_medicas WHERE id_entidad = su entidad.
      - SUPER_ADMIN        → Sin filtro geográfico.
    """
    filtro = apply_rbac_filter(current_user)
    query = db.query(Paciente)

    if solo_activos:
        query = query.filter(Paciente.es_activo == True)

    if filtro.filtrar_por_clues:
        query = query.filter(
            Paciente.clues_unidad_adscripcion == filtro.valor_clues
        )
    elif filtro.filtrar_por_entidad:
        query = query.join(UnidadMedica).filter(
            UnidadMedica.id_entidad == filtro.valor_entidad
        )

    total = query.count()
    pacientes = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    resultados = []
    for p in pacientes:
        datos = PacienteResponse.model_validate(p)
        datos.dias_adherencia = p.dias_adherencia
        resultados.append(datos)

    return PacienteListResponse(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        resultados=resultados,
    )


@app.post(
    "/pacientes",
    response_model=PacienteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["5.2 Pacientes"],
    summary="Registro de un nuevo paciente.",
)
def crear_paciente(
    payload: PacienteCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    """
    Solo RESPONSABLE_UNIDAD puede crear pacientes, y únicamente en su propia unidad.
    SUPER_ADMIN puede crear en cualquier unidad.
    """
    # Validación RBAC: el RESPONSABLE_UNIDAD solo puede registrar en su unidad.
    if current_user.es_responsable_unidad:
        if payload.clues_unidad_adscripcion != current_user.clues_unidad_asignada:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede registrar pacientes en su propia unidad médica.",
            )

    if db.query(Paciente).filter(Paciente.curp_paciente == payload.curp_paciente).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un paciente con CURP '{payload.curp_paciente}'.",
        )

    nuevo_paciente = Paciente(
        curp_paciente=payload.curp_paciente,
        nombre_completo=payload.nombre_completo,
        diagnostico_actual=payload.diagnostico_actual,
        fecha_inicio_tratamiento=payload.fecha_inicio_tratamiento,
        clues_unidad_adscripcion=payload.clues_unidad_adscripcion,
        es_activo=True,
        id_usuario_registro=current_user.id_usuario,
    )
    db.add(nuevo_paciente)
    db.commit()
    db.refresh(nuevo_paciente)

    respuesta = PacienteResponse.model_validate(nuevo_paciente)
    respuesta.dias_adherencia = nuevo_paciente.dias_adherencia
    return respuesta


@app.get(
    "/pacientes/{curp_paciente}",
    response_model=PacienteResponse,
    tags=["5.2 Pacientes"],
    summary="Detalle completo de un paciente y su historial de suministros.",
)
def obtener_paciente(
    curp_paciente: str,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    paciente = (
        db.query(Paciente)
        .options(joinedload(Paciente.suministros).joinedload(Suministro.medicamento))
        .filter(Paciente.curp_paciente == curp_paciente.upper())
        .first()
    )
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")

    # Verificar que el usuario tiene acceso a este paciente.
    _verificar_acceso_paciente(paciente, current_user, db)

    respuesta = PacienteResponse.model_validate(paciente)
    respuesta.dias_adherencia = paciente.dias_adherencia
    return respuesta


@app.patch(
    "/pacientes/{curp_paciente}",
    response_model=PacienteResponse,
    tags=["5.2 Pacientes"],
    summary="Actualización parcial de datos del paciente (diagnóstico, nombre, etc.).",
)
def actualizar_paciente(
    curp_paciente: str,
    payload: PacienteUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    paciente = db.query(Paciente).filter(
        Paciente.curp_paciente == curp_paciente.upper()
    ).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")

    _verificar_acceso_paciente(paciente, current_user, db)

    datos_actualizar = payload.model_dump(exclude_none=True)
    for campo, valor in datos_actualizar.items():
        setattr(paciente, campo, valor)

    # Auditoría: actualiza quién hizo el último cambio.
    paciente.id_usuario_registro = current_user.id_usuario
    db.commit()
    db.refresh(paciente)

    respuesta = PacienteResponse.model_validate(paciente)
    respuesta.dias_adherencia = paciente.dias_adherencia
    return respuesta


@app.delete(
    "/pacientes/{curp_paciente}",
    response_model=PacienteResponse,
    tags=["5.2 Pacientes"],
    summary="Soft Delete: da de baja al paciente (es_activo = False). No elimina el registro.",
)
def dar_baja_paciente(
    curp_paciente: str,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    """
    Blueprint §3 — Soft Delete:
    Ningún DELETE físico. Solo cambia es_activo = False y registra quién lo hizo.
    """
    paciente = db.query(Paciente).filter(
        Paciente.curp_paciente == curp_paciente.upper()
    ).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")

    _verificar_acceso_paciente(paciente, current_user, db)

    if not paciente.es_activo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El paciente ya se encuentra dado de baja.",
        )

    # ── SOFT DELETE ──────────────────────────────────────────────────────────
    paciente.es_activo = False
    paciente.id_usuario_registro = current_user.id_usuario  # Trazabilidad.
    # ─────────────────────────────────────────────────────────────────────────

    db.commit()
    db.refresh(paciente)

    respuesta = PacienteResponse.model_validate(paciente)
    respuesta.dias_adherencia = paciente.dias_adherencia
    return respuesta


# ===========================================================================
# 5.3  SUMINISTROS
# ===========================================================================

@app.get(
    "/suministros",
    response_model=SuministroListResponse,
    tags=["5.3 Suministros"],
    summary="Historial de asignaciones de medicamentos filtrado por rol.",
)
def listar_suministros(
    solo_activos: bool = Query(True, description="False para incluir registros anulados."),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    """
    RBAC automático (Blueprint §4):
      - RESPONSABLE_UNIDAD → suministros de pacientes de su unidad.
      - ADMIN_ESTATAL      → suministros de pacientes de su estado.
      - SUPER_ADMIN        → todos los suministros del país.
    """
    filtro = apply_rbac_filter(current_user)

    query = (
        db.query(Suministro)
        .join(Paciente, Suministro.curp_paciente == Paciente.curp_paciente)
        .options(joinedload(Suministro.medicamento))
    )

    if solo_activos:
        query = query.filter(Suministro.es_activo == True)

    if filtro.filtrar_por_clues:
        query = query.filter(
            Paciente.clues_unidad_adscripcion == filtro.valor_clues
        )
    elif filtro.filtrar_por_entidad:
        query = query.join(
            UnidadMedica,
            Paciente.clues_unidad_adscripcion == UnidadMedica.clues,
        ).filter(UnidadMedica.id_entidad == filtro.valor_entidad)

    total = query.count()
    suministros = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    return SuministroListResponse(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        resultados=[SuministroResponse.model_validate(s) for s in suministros],
    )


@app.post(
    "/suministros",
    response_model=SuministroResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["5.3 Suministros"],
    summary="Registrar la asignación de un medicamento a un paciente.",
)
def crear_suministro(
    payload: SuministroCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    # Verificar que el paciente existe y el usuario tiene acceso a él.
    paciente = db.query(Paciente).filter(
        Paciente.curp_paciente == payload.curp_paciente,
        Paciente.es_activo == True,
    ).first()
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado o dado de baja.",
        )
    _verificar_acceso_paciente(paciente, current_user, db)

    # Verificar que el medicamento existe y está activo en el catálogo.
    if not db.query(CatMedicamento).filter(
        CatMedicamento.clave_cnis == payload.clave_cnis_med,
        CatMedicamento.es_activo == True,
    ).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicamento con clave CNIS '{payload.clave_cnis_med}' no encontrado en el catálogo activo.",
        )

    nuevo_suministro = Suministro(
        curp_paciente=payload.curp_paciente,
        clave_cnis_med=payload.clave_cnis_med,
        dosis_administrada=payload.dosis_administrada,
        fecha_primera_administracion=payload.fecha_primera_administracion,
        id_usuario_registro=current_user.id_usuario,
        es_activo=True,
    )
    db.add(nuevo_suministro)
    db.commit()
    db.refresh(nuevo_suministro)

    # Recargar con relación al medicamento para poblar el campo embebido.
    db.refresh(nuevo_suministro)
    return SuministroResponse.model_validate(nuevo_suministro)


@app.delete(
    "/suministros/{id_suministro}",
    response_model=SuministroResponse,
    tags=["5.3 Suministros"],
    summary="Soft Delete: anula un suministro por error de captura (es_activo = False).",
)
def anular_suministro(
    id_suministro: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    """
    Blueprint §3 — Soft Delete:
    Anula el registro de suministro por error de captura.
    No elimina el dato; cambia es_activo = False para mantener la trazabilidad.
    """
    suministro = (
        db.query(Suministro)
        .options(joinedload(Suministro.medicamento))
        .filter(Suministro.id_suministro == id_suministro)
        .first()
    )
    if not suministro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suministro no encontrado.")

    # Verificar acceso al paciente al que pertenece el suministro.
    paciente = db.query(Paciente).filter(
        Paciente.curp_paciente == suministro.curp_paciente
    ).first()
    _verificar_acceso_paciente(paciente, current_user, db)

    if not suministro.es_activo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El suministro ya se encuentra anulado.",
        )

    # ── SOFT DELETE ──────────────────────────────────────────────────────────
    suministro.es_activo = False
    suministro.id_usuario_registro = current_user.id_usuario  # Trazabilidad.
    # ─────────────────────────────────────────────────────────────────────────

    db.commit()
    db.refresh(suministro)
    return SuministroResponse.model_validate(suministro)


# ===========================================================================
# 5.4  REPORTES
# ===========================================================================

@app.get(
    "/reportes/resumen-detallado",
    tags=["5.4 Reportes"],
    summary="Datos crudos con filtros de fecha. Para generación de Excel/PDF en el frontend.",
)
def reporte_resumen_detallado(
    fecha_inicio: date | None = Query(None, description="Filtrar suministros desde esta fecha."),
    fecha_fin: date | None = Query(None, description="Filtrar suministros hasta esta fecha."),
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    """
    Entrega un JSON con el detalle de suministros, paciente y medicamento
    para que el frontend genere reportes Excel/PDF.

    Aplica RBAC automático + filtros opcionales de fecha.
    """
    filtro = apply_rbac_filter(current_user)

    query = (
        db.query(Suministro)
        .join(Paciente, Suministro.curp_paciente == Paciente.curp_paciente)
        .join(CatMedicamento, Suministro.clave_cnis_med == CatMedicamento.clave_cnis)
        .options(
            joinedload(Suministro.paciente),
            joinedload(Suministro.medicamento),
        )
    )

    if solo_activos:
        query = query.filter(Suministro.es_activo == True, Paciente.es_activo == True)

    if filtro.filtrar_por_clues:
        query = query.filter(
            Paciente.clues_unidad_adscripcion == filtro.valor_clues
        )
    elif filtro.filtrar_por_entidad:
        query = query.join(
            UnidadMedica,
            Paciente.clues_unidad_adscripcion == UnidadMedica.clues,
        ).filter(UnidadMedica.id_entidad == filtro.valor_entidad)

    if fecha_inicio:
        query = query.filter(Suministro.fecha_primera_administracion >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Suministro.fecha_primera_administracion <= fecha_fin)

    suministros = query.all()

    return {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "total_registros": len(suministros),
        "filtros_aplicados": {
            "fecha_inicio": str(fecha_inicio) if fecha_inicio else None,
            "fecha_fin": str(fecha_fin) if fecha_fin else None,
            "solo_activos": solo_activos,
            "rbac_clues": filtro.valor_clues,
            "rbac_entidad": filtro.valor_entidad,
        },
        "datos": [
            {
                "id_suministro": s.id_suministro,
                "curp_paciente": s.curp_paciente,
                "nombre_paciente": s.paciente.nombre_completo,
                "diagnostico": s.paciente.diagnostico_actual,
                "clues_unidad": s.paciente.clues_unidad_adscripcion,
                "dias_adherencia": s.paciente.dias_adherencia,
                "clave_cnis": s.clave_cnis_med,
                "descripcion_medicamento": s.medicamento.descripcion if s.medicamento else None,
                "dosis_administrada": s.dosis_administrada,
                "fecha_primera_administracion": (
                    s.fecha_primera_administracion.isoformat()
                    if s.fecha_primera_administracion else None
                ),
                "fecha_registro_sistema": s.fecha_registro_sistema.isoformat(),
                "es_activo": s.es_activo,
            }
            for s in suministros
        ],
    }


@app.get(
    "/reportes/estatal",
    tags=["5.4 Reportes"],
    summary="Datos agregados por unidad médica. Exclusivo para Admin Estatal y Superior.",
)
def reporte_estatal(
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_admin_estatal_o_superior),
):
    """
    Entrega sumatorias por unidad médica dentro del ámbito del usuario:
      - ADMIN_ESTATAL → solo unidades de su estado.
      - SUPER_ADMIN   → todas las unidades del país.
    """
    filtro = apply_rbac_filter(current_user)

    query = (
        db.query(
            UnidadMedica.clues,
            UnidadMedica.nombre_de_la_unidad,
            UnidadMedica.id_entidad,
            func.count(Paciente.curp_paciente.distinct()).label("total_pacientes"),
            func.count(Suministro.id_suministro.distinct()).label("total_suministros"),
        )
        .outerjoin(Paciente, Paciente.clues_unidad_adscripcion == UnidadMedica.clues)
        .outerjoin(Suministro, Suministro.curp_paciente == Paciente.curp_paciente)
        .filter(Paciente.es_activo == True)
    )

    if filtro.filtrar_por_entidad:
        query = query.filter(UnidadMedica.id_entidad == filtro.valor_entidad)

    resultados = query.group_by(
        UnidadMedica.clues,
        UnidadMedica.nombre_de_la_unidad,
        UnidadMedica.id_entidad,
    ).all()

    return {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "ambito": filtro.valor_entidad if filtro.filtrar_por_entidad else "Nacional",
        "total_unidades": len(resultados),
        "unidades": [
            {
                "clues": r.clues,
                "nombre_de_la_unidad": r.nombre_de_la_unidad,
                "id_entidad": r.id_entidad,
                "total_pacientes_activos": r.total_pacientes,
                "total_suministros_activos": r.total_suministros,
            }
            for r in resultados
        ],
    }


# ===========================================================================
# 5.5  CATÁLOGOS — Solo SUPER_ADMIN
# ===========================================================================

@app.get(
    "/catalogos/medicamentos",
    response_model=list[MedicamentoResponse],
    tags=["5.5 Catálogos"],
    summary="Lista del catálogo oficial de medicamentos (Clave CNIS).",
)
def listar_medicamentos(
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    """Lectura permitida a los 3 roles. Gestión solo para SUPER_ADMIN."""
    query = db.query(CatMedicamento)
    if solo_activos:
        query = query.filter(CatMedicamento.es_activo == True)
    return query.order_by(CatMedicamento.clave_cnis).all()


@app.post(
    "/catalogos/medicamentos",
    response_model=MedicamentoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["5.5 Catálogos"],
    summary="Agregar una nueva clave CNIS al catálogo oficial. Solo SUPER_ADMIN.",
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


@app.patch(
    "/catalogos/medicamentos/{clave_cnis}",
    response_model=MedicamentoResponse,
    tags=["5.5 Catálogos"],
    summary="Actualizar o desactivar un medicamento del catálogo. Solo SUPER_ADMIN.",
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


# ===========================================================================
# CATÁLOGOS — Unidades Médicas (Solo SUPER_ADMIN)
# ===========================================================================

@app.get(
    "/catalogos/unidades",
    response_model=list[UnidadMedicaResponse],
    tags=["5.5 Catálogos"],
    summary="Lista de unidades médicas registradas.",
)
def listar_unidades(
    id_entidad: str | None = Query(None, description="Filtrar por estado."),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    query = db.query(UnidadMedica)
    if id_entidad:
        query = query.filter(UnidadMedica.id_entidad == id_entidad)
    return query.order_by(UnidadMedica.id_entidad, UnidadMedica.clues).all()


@app.post(
    "/catalogos/unidades",
    response_model=UnidadMedicaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["5.5 Catálogos"],
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


@app.patch(
    "/catalogos/unidades/{clues}",
    response_model=UnidadMedicaResponse,
    tags=["5.5 Catálogos"],
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


# ===========================================================================
# USUARIOS — Solo SUPER_ADMIN
# ===========================================================================

@app.get(
    "/usuarios",
    response_model=list[UsuarioResponse],
    tags=["5.5 Catálogos"],
    summary="Lista de usuarios de la plataforma. Solo SUPER_ADMIN.",
)
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    return db.query(Usuario).order_by(Usuario.id_usuario).all()


@app.post(
    "/usuarios",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["5.5 Catálogos"],
    summary="Crear una cuenta de usuario. Solo SUPER_ADMIN.",
)
def crear_usuario(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    if db.query(Usuario).filter(Usuario.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un usuario con email '{payload.email}'.",
        )
    nuevo = Usuario(
        nombre_usuario=payload.nombre_usuario,
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
        rol_nombre=payload.rol_nombre,
        clues_unidad_asignada=payload.clues_unidad_asignada,
        id_entidad=payload.id_entidad,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.patch(
    "/usuarios/{id_usuario}",
    response_model=UsuarioResponse,
    tags=["5.5 Catálogos"],
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
    if "password" in datos:
        usuario.hashed_password = hash_password(datos.pop("password"))
    for campo, valor in datos.items():
        setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)
    return usuario


@app.delete(
    "/usuarios/{id_usuario}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["5.5 Catálogos"],
    summary="Eliminar una cuenta de usuario. Solo SUPER_ADMIN.",
)
def eliminar_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    """
    Usuarios no tienen Soft Delete en el Blueprint; se eliminan físicamente.
    No se permite que el SUPER_ADMIN se elimine a sí mismo.
    """
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


# ===========================================================================
# Helpers internos
# ===========================================================================

def _verificar_acceso_paciente(
    paciente: Paciente,
    usuario: UsuarioActivo,
    db: Session,
) -> None:
    """
    Aplica el filtro de pertenencia del Blueprint (§4) a nivel de registro individual.
    Lanza 403 si el usuario no tiene acceso al paciente solicitado.
    """
    if usuario.es_super_admin:
        return

    if usuario.es_responsable_unidad:
        if paciente.clues_unidad_adscripcion != usuario.clues_unidad_asignada:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a pacientes de otra unidad médica.",
            )
        return

    if usuario.es_admin_estatal:
        unidad = db.query(UnidadMedica).filter(
            UnidadMedica.clues == paciente.clues_unidad_adscripcion
        ).first()
        if not unidad or unidad.id_entidad != usuario.id_entidad:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a pacientes de otro estado.",
            )
