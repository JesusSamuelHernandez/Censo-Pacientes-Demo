"""
main.py — Punto de entrada de la API. Define todos los endpoints del Blueprint v5.

Módulos cubiertos:
    /auth/login                      → Autenticación JWT
    /pacientes                       → Gestión clínica de pacientes
    /medicos                         → Gestión de personal médico
    /recetas                         → Censo de prescripción de medicamentos
    /reportes/resumen-detallado      → Datos crudos para Excel/PDF
    /reportes/estatal                → Agregados por unidad (Admin Estatal)
    /catalogos/medicamentos          → Catálogo CNIS (Solo Super Admin)
    /catalogos/unidades              → Unidades médicas (Solo Super Admin)
    /usuarios                        → Cuentas de plataforma (Solo Super Admin)

Soft Delete:
    DELETE /pacientes/{curp}         → es_activo = False
    DELETE /recetas/{id_receta}      → es_activo = False

RBAC (Blueprint §4):
    apply_rbac_filter() se llama en cada query para garantizar:
        RESPONSABLE_UNIDAD → solo ve su unidad
        ADMIN_ESTATAL      → solo ve su estado
        SUPER_ADMIN        → sin restricciones

Adherencia:
    Calculada en endpoint desde la receta activa más reciente del paciente:
    (date.today() - receta.fecha_inicio_tratamiento).days
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
from app.models import Base, CatMedicamento, Medico, Paciente, Receta, UnidadMedica, Usuario
from app.schemas import (
    LoginRequest,
    MedicoCreate,
    MedicoResponse,
    MedicoUpdate,
    MedicamentoCreate,
    MedicamentoResponse,
    MedicamentoUpdate,
    PacienteCreate,
    PacienteListResponse,
    PacienteResponse,
    PacienteUpdate,
    RecetaCreate,
    RecetaListResponse,
    RecetaResponse,
    RecetaUpdate,
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
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API — Medicamentos de Alto Costo",
    description=(
        "Backend para el censo de pacientes y prescripción de medicamentos de alto "
        "costo. Implementa RBAC con tres niveles: SUPER_ADMIN, ADMIN_ESTATAL y "
        "RESPONSABLE_UNIDAD."
    ),
    version="2.0.0",
)


# ===========================================================================
# AUTENTICACIÓN
# ===========================================================================

@app.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["Autenticación"],
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
    )


# ===========================================================================
# PACIENTES
# ===========================================================================

@app.get(
    "/pacientes",
    response_model=PacienteListResponse,
    tags=["Pacientes"],
    summary="Lista de pacientes filtrada automáticamente por rol.",
)
def listar_pacientes(
    solo_activos: bool = Query(True),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    filtro = apply_rbac_filter(current_user)
    query = db.query(Paciente)

    if solo_activos:
        query = query.filter(Paciente.es_activo == True)

    if filtro.filtrar_por_clues:
        query = query.filter(Paciente.clues_unidad_adscripcion == filtro.valor_clues)
    elif filtro.filtrar_por_entidad:
        query = query.join(UnidadMedica).filter(
            UnidadMedica.id_entidad == filtro.valor_entidad
        )

    total = query.count()
    pacientes = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    resultados = []
    for p in pacientes:
        datos = PacienteResponse.model_validate(p)
        datos.dias_adherencia = _calcular_adherencia(p.curp_paciente, db)
        resultados.append(datos)

    return PacienteListResponse(
        total=total, pagina=pagina, por_pagina=por_pagina, resultados=resultados
    )


@app.post(
    "/pacientes",
    response_model=PacienteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Pacientes"],
    summary="Registro de un nuevo paciente.",
)
def crear_paciente(
    payload: PacienteCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
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

    nuevo = Paciente(
        curp_paciente=payload.curp_paciente,
        nombre_completo=payload.nombre_completo,
        diagnostico_actual=payload.diagnostico_actual,
        clues_unidad_adscripcion=payload.clues_unidad_adscripcion,
        es_activo=True,
        id_usuario_registro=current_user.id_usuario,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    respuesta = PacienteResponse.model_validate(nuevo)
    respuesta.dias_adherencia = _calcular_adherencia(nuevo.curp_paciente, db)
    return respuesta


@app.get(
    "/pacientes/{curp_paciente}",
    response_model=PacienteResponse,
    tags=["Pacientes"],
    summary="Detalle completo de un paciente.",
)
def obtener_paciente(
    curp_paciente: str,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    paciente = db.query(Paciente).filter(
        Paciente.curp_paciente == curp_paciente.upper()
    ).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")

    _verificar_acceso_paciente(paciente, current_user, db)

    respuesta = PacienteResponse.model_validate(paciente)
    respuesta.dias_adherencia = _calcular_adherencia(paciente.curp_paciente, db)
    return respuesta


@app.patch(
    "/pacientes/{curp_paciente}",
    response_model=PacienteResponse,
    tags=["Pacientes"],
    summary="Actualización parcial de datos del paciente.",
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

    for campo, valor in payload.model_dump(exclude_none=True).items():
        setattr(paciente, campo, valor)

    paciente.id_usuario_registro = current_user.id_usuario
    db.commit()
    db.refresh(paciente)

    respuesta = PacienteResponse.model_validate(paciente)
    respuesta.dias_adherencia = _calcular_adherencia(paciente.curp_paciente, db)
    return respuesta


@app.delete(
    "/pacientes/{curp_paciente}",
    response_model=PacienteResponse,
    tags=["Pacientes"],
    summary="Soft Delete: da de baja al paciente.",
)
def dar_baja_paciente(
    curp_paciente: str,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
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

    paciente.es_activo = False
    paciente.id_usuario_registro = current_user.id_usuario
    db.commit()
    db.refresh(paciente)

    respuesta = PacienteResponse.model_validate(paciente)
    respuesta.dias_adherencia = None
    return respuesta


# ===========================================================================
# MÉDICOS
# ===========================================================================

@app.get(
    "/medicos",
    response_model=list[MedicoResponse],
    tags=["Médicos"],
    summary="Catálogo de médicos. Lectura para todos los roles.",
)
def listar_medicos(
    clues_adscripcion: str | None = Query(None, description="Filtrar por unidad médica."),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    query = db.query(Medico)
    if clues_adscripcion:
        query = query.filter(Medico.clues_adscripcion == clues_adscripcion.upper())
    return query.order_by(Medico.nombre_medico).all()


@app.post(
    "/medicos",
    response_model=MedicoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Médicos"],
    summary="Registrar un médico. RESPONSABLE_UNIDAD (su unidad) o SUPER_ADMIN.",
)
def crear_medico(
    payload: MedicoCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    # ADMIN_ESTATAL no puede crear médicos.
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no puede registrar médicos.",
        )

    # RESPONSABLE_UNIDAD solo puede registrar médicos de su propia unidad.
    if current_user.es_responsable_unidad:
        if payload.clues_adscripcion != current_user.clues_unidad_asignada:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede registrar médicos de su propia unidad médica.",
            )

    if db.query(Medico).filter(Medico.cedula == payload.cedula).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un médico con cédula '{payload.cedula}'.",
        )

    nuevo = Medico(**payload.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.get(
    "/medicos/{id_medico}",
    response_model=MedicoResponse,
    tags=["Médicos"],
    summary="Perfil del médico.",
)
def obtener_medico(
    id_medico: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médico no encontrado.")
    return medico


@app.patch(
    "/medicos/{id_medico}",
    response_model=MedicoResponse,
    tags=["Médicos"],
    summary="Actualizar datos de un médico. Solo SUPER_ADMIN.",
)
def actualizar_medico(
    id_medico: int,
    payload: MedicoUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médico no encontrado.")

    for campo, valor in payload.model_dump(exclude_none=True).items():
        setattr(medico, campo, valor)
    db.commit()
    db.refresh(medico)
    return medico


@app.delete(
    "/medicos/{id_medico}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Médicos"],
    summary="Eliminar un médico. Solo SUPER_ADMIN.",
)
def eliminar_medico(
    id_medico: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médico no encontrado.")
    db.delete(medico)
    db.commit()


# ===========================================================================
# RECETAS
# ===========================================================================

@app.get(
    "/recetas",
    response_model=RecetaListResponse,
    tags=["Recetas"],
    summary="Historial de recetas filtrado por rol.",
)
def listar_recetas(
    solo_activos: bool = Query(True),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    filtro = apply_rbac_filter(current_user)

    query = (
        db.query(Receta)
        .options(
            joinedload(Receta.medicamento),
            joinedload(Receta.medico),
        )
    )

    if solo_activos:
        query = query.filter(Receta.es_activo == True)

    if filtro.filtrar_por_clues:
        query = query.filter(Receta.clues == filtro.valor_clues)
    elif filtro.filtrar_por_entidad:
        query = query.join(
            UnidadMedica, Receta.clues == UnidadMedica.clues
        ).filter(UnidadMedica.id_entidad == filtro.valor_entidad)

    total = query.count()
    recetas = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    return RecetaListResponse(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        resultados=[RecetaResponse.model_validate(r) for r in recetas],
    )


@app.post(
    "/recetas",
    response_model=RecetaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Recetas"],
    summary="Registrar una nueva receta.",
)
def crear_receta(
    payload: RecetaCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    # ADMIN_ESTATAL no puede crear recetas.
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no puede registrar recetas.",
        )

    # RESPONSABLE_UNIDAD solo puede crear recetas en su unidad.
    if current_user.es_responsable_unidad:
        if payload.clues != current_user.clues_unidad_asignada:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede registrar recetas en su propia unidad médica.",
            )

    if db.query(Receta).filter(Receta.id_receta == payload.id_receta).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una receta con folio '{payload.id_receta}'.",
        )

    # Verificar que el paciente existe y está activo.
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

    # Verificar que el médico existe.
    if not db.query(Medico).filter(Medico.id_medico == payload.id_medico).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Médico con id '{payload.id_medico}' no encontrado.",
        )

    # Verificar que el medicamento existe y está activo.
    if not db.query(CatMedicamento).filter(
        CatMedicamento.clave_cnis == payload.clave_cnis,
        CatMedicamento.es_activo == True,
    ).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicamento '{payload.clave_cnis}' no encontrado en catálogo activo.",
        )

    nueva = Receta(
        id_receta=payload.id_receta,
        id_medico=payload.id_medico,
        curp_paciente=payload.curp_paciente,
        clave_cnis=payload.clave_cnis,
        clues=payload.clues,
        fecha_inicio_tratamiento=payload.fecha_inicio_tratamiento,
        fecha_primera_admin=payload.fecha_primera_admin,
        dosis_administrada=payload.dosis_administrada,
        id_usuario_registro=current_user.id_usuario,
        es_activo=True,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)

    # Recargar con relaciones embebidas.
    receta = (
        db.query(Receta)
        .options(joinedload(Receta.medicamento), joinedload(Receta.medico))
        .filter(Receta.id_receta == nueva.id_receta)
        .first()
    )
    return RecetaResponse.model_validate(receta)


@app.get(
    "/recetas/{id_receta}",
    response_model=RecetaResponse,
    tags=["Recetas"],
    summary="Detalle completo de una receta.",
)
def obtener_receta(
    id_receta: str,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    receta = (
        db.query(Receta)
        .options(joinedload(Receta.medicamento), joinedload(Receta.medico))
        .filter(Receta.id_receta == id_receta)
        .first()
    )
    if not receta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada.")

    _verificar_acceso_receta(receta, current_user, db)
    return RecetaResponse.model_validate(receta)


@app.patch(
    "/recetas/{id_receta}",
    response_model=RecetaResponse,
    tags=["Recetas"],
    summary="Actualización parcial de una receta.",
)
def actualizar_receta(
    id_receta: str,
    payload: RecetaUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no puede modificar recetas.",
        )

    receta = (
        db.query(Receta)
        .options(joinedload(Receta.medicamento), joinedload(Receta.medico))
        .filter(Receta.id_receta == id_receta)
        .first()
    )
    if not receta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada.")

    _verificar_acceso_receta(receta, current_user, db)

    for campo, valor in payload.model_dump(exclude_none=True).items():
        setattr(receta, campo, valor)
    receta.id_usuario_registro = current_user.id_usuario
    db.commit()
    db.refresh(receta)
    return RecetaResponse.model_validate(receta)


@app.delete(
    "/recetas/{id_receta}",
    response_model=RecetaResponse,
    tags=["Recetas"],
    summary="Soft Delete: anula una receta por error de captura.",
)
def anular_receta(
    id_receta: str,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no puede anular recetas.",
        )

    receta = (
        db.query(Receta)
        .options(joinedload(Receta.medicamento), joinedload(Receta.medico))
        .filter(Receta.id_receta == id_receta)
        .first()
    )
    if not receta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada.")

    _verificar_acceso_receta(receta, current_user, db)

    if not receta.es_activo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La receta ya se encuentra anulada.",
        )

    receta.es_activo = False
    receta.id_usuario_registro = current_user.id_usuario
    db.commit()
    db.refresh(receta)
    return RecetaResponse.model_validate(receta)


# ===========================================================================
# REPORTES
# ===========================================================================

@app.get(
    "/reportes/resumen-detallado",
    tags=["Reportes"],
    summary="Datos crudos con filtros de fecha. Para generación de Excel/PDF.",
)
def reporte_resumen_detallado(
    fecha_inicio: date | None = Query(None),
    fecha_fin: date | None = Query(None),
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    filtro = apply_rbac_filter(current_user)

    query = (
        db.query(Receta)
        .join(Paciente, Receta.curp_paciente == Paciente.curp_paciente)
        .join(CatMedicamento, Receta.clave_cnis == CatMedicamento.clave_cnis)
        .options(
            joinedload(Receta.paciente),
            joinedload(Receta.medicamento),
            joinedload(Receta.medico),
        )
    )

    if solo_activos:
        query = query.filter(Receta.es_activo == True, Paciente.es_activo == True)

    if filtro.filtrar_por_clues:
        query = query.filter(Receta.clues == filtro.valor_clues)
    elif filtro.filtrar_por_entidad:
        query = query.join(
            UnidadMedica, Receta.clues == UnidadMedica.clues
        ).filter(UnidadMedica.id_entidad == filtro.valor_entidad)

    if fecha_inicio:
        query = query.filter(Receta.fecha_primera_admin >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Receta.fecha_primera_admin <= fecha_fin)

    recetas = query.all()

    return {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "total_registros": len(recetas),
        "filtros_aplicados": {
            "fecha_inicio": str(fecha_inicio) if fecha_inicio else None,
            "fecha_fin": str(fecha_fin) if fecha_fin else None,
            "solo_activos": solo_activos,
            "rbac_clues": filtro.valor_clues,
            "rbac_entidad": filtro.valor_entidad,
        },
        "datos": [
            {
                "id_receta": r.id_receta,
                "curp_paciente": r.curp_paciente,
                "nombre_paciente": r.paciente.nombre_completo,
                "diagnostico": r.paciente.diagnostico_actual,
                "clues_unidad": r.clues,
                "medico": r.medico.nombre_medico if r.medico else None,
                "cedula_medico": r.medico.cedula if r.medico else None,
                "dias_adherencia": (
                    (date.today() - r.fecha_inicio_tratamiento).days
                    if r.fecha_inicio_tratamiento else None
                ),
                "clave_cnis": r.clave_cnis,
                "descripcion_medicamento": r.medicamento.descripcion if r.medicamento else None,
                "dosis_administrada": r.dosis_administrada,
                "fecha_inicio_tratamiento": (
                    r.fecha_inicio_tratamiento.isoformat()
                    if r.fecha_inicio_tratamiento else None
                ),
                "fecha_primera_admin": (
                    r.fecha_primera_admin.isoformat()
                    if r.fecha_primera_admin else None
                ),
                "fecha_registro_sistema": r.fecha_registro_sistema.isoformat(),
                "es_activo": r.es_activo,
            }
            for r in recetas
        ],
    }


@app.get(
    "/reportes/estatal",
    tags=["Reportes"],
    summary="Datos agregados por unidad médica. Exclusivo para Admin Estatal y Superior.",
)
def reporte_estatal(
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_admin_estatal_o_superior),
):
    filtro = apply_rbac_filter(current_user)

    query = (
        db.query(
            UnidadMedica.clues,
            UnidadMedica.nombre_de_la_unidad,
            UnidadMedica.id_entidad,
            func.count(Paciente.curp_paciente.distinct()).label("total_pacientes"),
            func.count(Receta.id_receta.distinct()).label("total_recetas"),
        )
        .outerjoin(Paciente, Paciente.clues_unidad_adscripcion == UnidadMedica.clues)
        .outerjoin(Receta, Receta.clues == UnidadMedica.clues)
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
                "total_recetas_activas": r.total_recetas,
            }
            for r in resultados
        ],
    }


# ===========================================================================
# CATÁLOGOS — Medicamentos
# ===========================================================================

@app.get(
    "/catalogos/medicamentos",
    response_model=list[MedicamentoResponse],
    tags=["Catálogos"],
    summary="Lista del catálogo oficial de medicamentos.",
)
def listar_medicamentos(
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_cualquier_rol),
):
    query = db.query(CatMedicamento)
    if solo_activos:
        query = query.filter(CatMedicamento.es_activo == True)
    return query.order_by(CatMedicamento.clave_cnis).all()


@app.post(
    "/catalogos/medicamentos",
    response_model=MedicamentoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Catálogos"],
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


@app.patch(
    "/catalogos/medicamentos/{clave_cnis}",
    response_model=MedicamentoResponse,
    tags=["Catálogos"],
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


# ===========================================================================
# CATÁLOGOS — Unidades Médicas
# ===========================================================================

@app.get(
    "/catalogos/unidades",
    response_model=list[UnidadMedicaResponse],
    tags=["Catálogos"],
    summary="Lista de unidades médicas.",
)
def listar_unidades(
    id_entidad: str | None = Query(None),
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
    tags=["Catálogos"],
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
    tags=["Catálogos"],
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
# USUARIOS
# ===========================================================================

@app.get(
    "/usuarios",
    response_model=list[UsuarioResponse],
    tags=["Usuarios"],
    summary="Lista de usuarios. Solo SUPER_ADMIN.",
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
    tags=["Usuarios"],
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
    tags=["Usuarios"],
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
    tags=["Usuarios"],
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


# ===========================================================================
# Helpers internos
# ===========================================================================

def _calcular_adherencia(curp: str, db: Session) -> int | None:
    """
    Retorna los días transcurridos desde fecha_inicio_tratamiento de la receta
    activa más reciente del paciente. Retorna None si no hay receta activa con fecha.
    """
    receta = (
        db.query(Receta)
        .filter(
            Receta.curp_paciente == curp,
            Receta.es_activo == True,
            Receta.fecha_inicio_tratamiento.isnot(None),
        )
        .order_by(Receta.fecha_registro_sistema.desc())
        .first()
    )
    if receta and receta.fecha_inicio_tratamiento:
        return (date.today() - receta.fecha_inicio_tratamiento).days
    return None


def _verificar_acceso_paciente(
    paciente: Paciente,
    usuario: UsuarioActivo,
    db: Session,
) -> None:
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


def _verificar_acceso_receta(
    receta: Receta,
    usuario: UsuarioActivo,
    db: Session,
) -> None:
    if usuario.es_super_admin:
        return
    if usuario.es_responsable_unidad:
        if receta.clues != usuario.clues_unidad_asignada:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a recetas de otra unidad médica.",
            )
        return
    if usuario.es_admin_estatal:
        unidad = db.query(UnidadMedica).filter(
            UnidadMedica.clues == receta.clues
        ).first()
        if not unidad or unidad.id_entidad != usuario.id_entidad:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a recetas de otro estado.",
            )
