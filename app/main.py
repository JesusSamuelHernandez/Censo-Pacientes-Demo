"""
main.py — Punto de entrada de la API. Define todos los endpoints del Blueprint v6.

Módulos cubiertos:
    /auth/login                      → Autenticación JWT
    /pacientes                       → Gestión clínica de pacientes
    /medicos                         → Gestión de personal médico
    /registros                       → Censo de prescripción de medicamentos (antes /recetas)
    /reportes/resumen-detallado      → Datos crudos para Excel/PDF
    /reportes/estatal                → Agregados por unidad (Admin Estatal)
    /catalogos/medicamentos          → Catálogo CNIS (Solo Super Admin)
    /catalogos/unidades              → Unidades médicas (Solo Super Admin)
    /usuarios                        → Cuentas de plataforma (Solo Super Admin)

Soft Delete:
    DELETE /pacientes/{curp}         → es_activo = False
    DELETE /registros/{id_registro}  → es_activo = False

RBAC (Blueprint §4):
    apply_rbac_filter() se llama en cada query para garantizar:
        RESPONSABLE_UNIDAD → solo ve su unidad
        ADMIN_ESTATAL      → solo ve su estado
        SUPER_ADMIN        → sin restricciones

Adherencia:
    Calculada en endpoint desde el registro activo más reciente del paciente:
    (date.today() - registro.fecha_inicio_tratamiento).days
"""
import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import exists, func, update
from sqlalchemy.orm import Session, joinedload

from app.auth import (
    UsuarioActivo,
    apply_rbac_filter,
    autenticar_usuario,
    create_access_token,
    hash_password,
    require_admin_estatal_o_superior,
    require_cualquier_rol,
    require_password_cambiado,
    require_super_admin,
    verify_password,
)
from app.crypto import cifrar, descifrar, descifrar_o_none, hash_sha256
from app.database import engine, get_db
from app.models import Base, CatDiagnostico, CatMedicamento, ExpedientePaciente, Medico, NotificacionTransferencia, Paciente, Registro, UnidadMedica, UnidadMedicamento, Usuario
from app.schemas import (
    BusquedaCurpResponse,
    CambiarPasswordRequest,
    DiagnosticoCreate,
    DiagnosticoResponse,
    DiagnosticoUpdate,
    ExpedienteCreate,
    ExpedienteResponse,
    ExpedienteUpdate,
    NotificacionListResponse,
    NotificacionResponse,
    NotificacionTransferenciaListResponse,
    NotificacionTransferenciaResponse,
    RtmFilaResponse,
    RtmMesItem,
    RtmResponse,
    RegistroCompletoCreate,
    RegistroCompletoResponse,
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
    RegistroCreate,
    RegistroListResponse,
    RegistroResponse,
    RegistroUpdate,
    TokenResponse,
    UnidadMedicaCreate,
    UnidadMedicaResponse,
    UnidadMedicaUpdate,
    UsuarioCreate,
    UsuarioCreateResponse,
    UsuarioResponse,
    UsuarioUpdate,
    ValidarContinuidadRequest,
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
    version="3.0.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
import os

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173,https://censo-frontend-production-dab7.up.railway.app"
)

allowed_origins = [url.strip() for url in FRONTEND_URL.split(",") if url.strip()]

if "http://localhost:5173" not in allowed_origins:
    allowed_origins.append("http://localhost:5173")

print(f"✓ CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TEMPORAL: permitir todos para debugging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    por_pagina: int = Query(20, ge=1, le=500),
    clave_cnis: str | None = Query(None, description="Filtrar pacientes que tienen prescripción activa con este medicamento."),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    marcar_registros_vencidos(db)
    filtro = apply_rbac_filter(current_user)
    query = db.query(Paciente)

    if solo_activos:
        query = query.filter(Paciente.es_activo == True)
        query = query.filter(
            exists().where(
                Registro.id_paciente == Paciente.id_paciente,
                Registro.es_activo == True,
            )
        )

    # Filtro por medicamento específico
    if clave_cnis:
        query = query.filter(
            exists().where(
                Registro.id_paciente == Paciente.id_paciente,
                Registro.es_activo == True,
                Registro.clave_cnis == clave_cnis,
            )
        )

    if filtro.filtrar_por_clues:
        query = query.filter(Paciente.clues_unidad_adscripcion == filtro.valor_clues)
    elif filtro.filtrar_por_entidad:
        query = query.join(UnidadMedica).filter(
            UnidadMedica.id_entidad == filtro.valor_entidad
        )

    total = query.count()
    pacientes_pag = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    # Una sola query para obtener medicamentos activos de la página actual.
    # De paso sirve para calcular `tiene_prescripcion_activa` e `ids_con_activo`.
    ids_con_activo: set[int] = set()
    medicamentos_por_paciente: dict[int, list[str]] = {}
    adherencia_por_paciente: dict[int, list[int | None]] = {}

    if pacientes_pag:
        ids_pag = [p.id_paciente for p in pacientes_pag]
        meds_rows = (
            db.query(Registro.id_paciente, CatMedicamento.descripcion, CatMedicamento.clave_cnis, Registro.fecha_inicio_tratamiento)
            .join(CatMedicamento, Registro.clave_cnis == CatMedicamento.clave_cnis)
            .filter(Registro.id_paciente.in_(ids_pag), Registro.es_activo == True)
            .order_by(Registro.fecha_registro_sistema.desc())
            .all()
        )
        for id_p, desc, clave, fecha_inicio in meds_rows:
            ids_con_activo.add(id_p)
            label = (desc[:60] + "..." if desc and len(desc) > 60 else desc or clave)
            if id_p not in medicamentos_por_paciente:
                medicamentos_por_paciente[id_p] = []
                adherencia_por_paciente[id_p] = []
            if label not in medicamentos_por_paciente[id_p]:
                medicamentos_por_paciente[id_p].append(label)
                adherencia_por_paciente[id_p].append(
                    (date.today() - fecha_inicio).days if fecha_inicio else None
                )

    resultados = []
    for p in pacientes_pag:
        tiene = p.id_paciente in ids_con_activo
        meds = medicamentos_por_paciente.get(p.id_paciente, [])
        adherencias = adherencia_por_paciente.get(p.id_paciente, [])
        diags = _get_diagnosticos_activos(p.id_paciente, db)
        datos = _paciente_to_response(p, tiene_prescripcion_activa=tiene, medicamentos_activos=meds, diagnosticos_activos=diags)
        datos.adherencia_medicamentos = adherencias
        datos.dias_adherencia = _calcular_adherencia(p.id_paciente, db)
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
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    if current_user.es_responsable_unidad:
        if payload.clues_unidad_adscripcion != current_user.clues_unidad_asignada:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede registrar pacientes en su propia unidad médica.",
            )

    curp_hash = hash_sha256(payload.curp_paciente)
    if db.query(Paciente).filter(Paciente.curp_hash == curp_hash).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un paciente con CURP '{payload.curp_paciente}'.",
        )

    nuevo = Paciente(
        curp_hash=curp_hash,
        curp_paciente=cifrar(payload.curp_paciente),
        nombre_completo=cifrar(payload.nombre_completo),
        diagnostico_actual=cifrar(payload.diagnostico_actual) if payload.diagnostico_actual else None,
        clues_unidad_adscripcion=payload.clues_unidad_adscripcion,
        fecha_nacimiento=payload.fecha_nacimiento,
        es_activo=True,
        id_usuario_registro=current_user.id_usuario,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    respuesta = _paciente_to_response(nuevo, tiene_prescripcion_activa=False)
    respuesta.dias_adherencia = None
    return respuesta


@app.get(
    "/pacientes/buscar",
    response_model=BusquedaCurpResponse,
    tags=["Pacientes"],
    summary="Búsqueda nacional de paciente por CURP. Sin filtro RBAC — todos los roles.",
)
def buscar_paciente_por_curp(
    curp: str = Query(..., min_length=18, max_length=18, description="CURP completa del paciente."),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    curp_normalizada = curp.strip().upper()
    paciente = db.query(Paciente).filter(
        Paciente.curp_hash == hash_sha256(curp_normalizada)
    ).first()

    if not paciente:
        return BusquedaCurpResponse(existe=False)

    unidad = db.query(UnidadMedica).filter(
        UnidadMedica.clues == paciente.clues_unidad_adscripcion
    ).first()

    total_registros = db.query(Registro).filter(
        Registro.id_paciente == paciente.id_paciente
    ).count()

    return BusquedaCurpResponse(
        existe=True,
        id_paciente=paciente.id_paciente,
        nombre_completo=descifrar(paciente.nombre_completo),
        fecha_nacimiento=paciente.fecha_nacimiento,
        clues_unidad_adscripcion=paciente.clues_unidad_adscripcion,
        nombre_unidad=unidad.nombre_de_la_unidad if unidad else None,
        total_registros=total_registros,
    )


@app.get(
    "/pacientes/{curp_paciente}",
    response_model=PacienteResponse,
    tags=["Pacientes"],
    summary="Detalle completo de un paciente.",
)
def obtener_paciente(
    curp_paciente: str,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    marcar_registros_vencidos(db)
    paciente = db.query(Paciente).filter(
        Paciente.curp_hash == hash_sha256(curp_paciente)
    ).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")

    # Lectura nacional sin restricción: cualquier rol puede consultar el detalle de
    # un paciente para hacer búsquedas al registrar una nueva prescripción.
    # La restricción RBAC aplica solo en escritura (PATCH / DELETE).

    tiene = _tiene_prescripcion_activa(paciente.id_paciente, db)
    meds, adherencias = _get_medicamentos_y_adherencia(paciente.id_paciente, db)
    diags = _get_diagnosticos_activos(paciente.id_paciente, db)
    respuesta = _paciente_to_response(paciente, tiene_prescripcion_activa=tiene, medicamentos_activos=meds, diagnosticos_activos=diags)
    respuesta.adherencia_medicamentos = adherencias
    respuesta.dias_adherencia = _calcular_adherencia(paciente.id_paciente, db)
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
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    paciente = db.query(Paciente).filter(
        Paciente.curp_hash == hash_sha256(curp_paciente)
    ).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")

    # RBAC para escritura — permite traslado entrante para RESPONSABLE_UNIDAD
    if current_user.es_responsable_unidad:
        nueva_clues = payload.clues_unidad_adscripcion
        if nueva_clues:
            # Si cambia la CLUES, el destino debe ser su propia unidad
            if nueva_clues.strip().upper() != current_user.clues_unidad_asignada:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo puede transferir pacientes a su propia unidad médica.",
                )
        else:
            # Si no cambia la CLUES, el paciente debe ser ya de su unidad
            if paciente.clues_unidad_adscripcion != current_user.clues_unidad_asignada:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Para editar un paciente de otra unidad, selecciona tu unidad en el campo de adscripción para transferirlo.",
                )
    elif current_user.es_admin_estatal:
        unidad = db.query(UnidadMedica).filter(
            UnidadMedica.clues == paciente.clues_unidad_adscripcion
        ).first()
        if not unidad or unidad.id_entidad != current_user.id_entidad:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a pacientes de otro estado.",
            )

    clues_anterior = paciente.clues_unidad_adscripcion

    datos = payload.model_dump(exclude_none=True)
    if "nombre_completo" in datos:
        paciente.nombre_completo = cifrar(datos.pop("nombre_completo"))
    if "diagnostico_actual" in datos:
        val = datos.pop("diagnostico_actual")
        paciente.diagnostico_actual = cifrar(val) if val else None
    if "estatus_evolucion" in datos:
        paciente.id_usuario_ultimo_cambio_estatus = current_user.id_usuario
        paciente.fecha_ultimo_cambio_estatus = datetime.now(timezone.utc)
    for campo, valor in datos.items():
        setattr(paciente, campo, valor)

    paciente.id_usuario_registro = current_user.id_usuario
    db.commit()
    db.refresh(paciente)

    # Si la unidad cambió, registrar notificación de traslado para la unidad de origen
    if clues_anterior != paciente.clues_unidad_adscripcion:
        notif = NotificacionTransferencia(
            id_paciente=paciente.id_paciente,
            clues_unidad_origen=clues_anterior,
            clues_unidad_destino=paciente.clues_unidad_adscripcion,
            id_usuario_traslado=current_user.id_usuario,
        )
        db.add(notif)
        db.commit()

    tiene = _tiene_prescripcion_activa(paciente.id_paciente, db)
    meds, adherencias = _get_medicamentos_y_adherencia(paciente.id_paciente, db)
    diags = _get_diagnosticos_activos(paciente.id_paciente, db)
    respuesta = _paciente_to_response(paciente, tiene_prescripcion_activa=tiene, medicamentos_activos=meds, diagnosticos_activos=diags)
    respuesta.adherencia_medicamentos = adherencias
    respuesta.dias_adherencia = _calcular_adherencia(paciente.id_paciente, db)
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
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    paciente = db.query(Paciente).filter(
        Paciente.curp_hash == hash_sha256(curp_paciente)
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

    db.query(Registro).filter(
        Registro.id_paciente == paciente.id_paciente,
        Registro.es_activo == True,
    ).update({"es_activo": False})

    db.commit()
    db.refresh(paciente)

    respuesta = _paciente_to_response(paciente, tiene_prescripcion_activa=False)
    respuesta.dias_adherencia = None
    return respuesta


@app.get(
    "/pacientes/{curp_paciente}/expedientes",
    response_model=list[ExpedienteResponse],
    tags=["Pacientes"],
    summary="Lista los expedientes del paciente en cada unidad donde ha sido atendido.",
)
def listar_expedientes_paciente(
    curp_paciente: str,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    paciente = db.query(Paciente).filter(
        Paciente.curp_hash == hash_sha256(curp_paciente)
    ).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")
    expedientes = db.query(ExpedientePaciente).filter(
        ExpedientePaciente.id_paciente == paciente.id_paciente
    ).all()
    return [ExpedienteResponse.model_validate(e) for e in expedientes]


@app.post(
    "/pacientes/{curp_paciente}/expedientes",
    response_model=ExpedienteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Pacientes"],
    summary="Crea o actualiza el expediente del paciente en una unidad específica (upsert).",
)
def upsert_expediente_paciente(
    curp_paciente: str,
    payload: ExpedienteCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    paciente = db.query(Paciente).filter(
        Paciente.curp_hash == hash_sha256(curp_paciente)
    ).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")

    if current_user.es_responsable_unidad and payload.clues != current_user.clues_unidad_asignada:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puede gestionar expedientes de su propia unidad.",
        )

    expediente = db.query(ExpedientePaciente).filter(
        ExpedientePaciente.id_paciente == paciente.id_paciente,
        ExpedientePaciente.clues == payload.clues,
    ).first()

    if expediente:
        expediente.numero_expediente = payload.numero_expediente
    else:
        if not db.query(UnidadMedica).filter(UnidadMedica.clues == payload.clues).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unidad '{payload.clues}' no encontrada.")
        expediente = ExpedientePaciente(
            id_paciente=paciente.id_paciente,
            clues=payload.clues,
            numero_expediente=payload.numero_expediente,
        )
        db.add(expediente)

    db.commit()
    db.refresh(expediente)
    return ExpedienteResponse.model_validate(expediente)


@app.get(
    "/pacientes/{curp_paciente}/registros",
    response_model=RegistroListResponse,
    tags=["Pacientes"],
    summary="Todas las prescripciones de un paciente, sin filtro de unidad.",
)
def listar_registros_de_paciente(
    curp_paciente: str,
    solo_activos: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    marcar_registros_vencidos(db)
    paciente = db.query(Paciente).filter(
        Paciente.curp_hash == hash_sha256(curp_paciente)
    ).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")

    query = (
        db.query(Registro)
        .options(
            joinedload(Registro.paciente),
            joinedload(Registro.medicamento),
            joinedload(Registro.medico),
            joinedload(Registro.diagnostico),
        )
        .filter(Registro.id_paciente == paciente.id_paciente)
    )

    if solo_activos:
        query = query.filter(Registro.es_activo == True)

    registros = query.order_by(Registro.id_registro.desc()).all()
    total = len(registros)

    return RegistroListResponse(
        total=total,
        pagina=1,
        por_pagina=total if total > 0 else 1,
        resultados=[_registro_to_response(r) for r in registros],
    )


# ===========================================================================
# MÉDICOS
# ===========================================================================

@app.get(
    "/medicos",
    response_model=list[MedicoResponse],
    tags=["Médicos"],
    summary="Catálogo de médicos filtrado por rol (RBAC).",
)
def listar_medicos(
    clues_adscripcion: str | None = Query(None, description="Filtrar por unidad médica (solo SUPER_ADMIN puede usarlo libremente)."),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    filtro = apply_rbac_filter(current_user)
    query = db.query(Medico)

    query = query.filter(Medico.es_activo == True)

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


@app.post(
    "/medicos",
    response_model=MedicoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Médicos"],
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

    nuevo = Medico(
        cedula_hash=cedula_hash,
        nombre_medico=cifrar(payload.nombre_medico),
        cedula=cifrar(payload.cedula),
        email=payload.email,
        clues_adscripcion=payload.clues_adscripcion,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return _medico_to_response(nuevo)


@app.get(
    "/medicos/{id_medico}",
    response_model=MedicoResponse,
    tags=["Médicos"],
    summary="Perfil del médico.",
)
def obtener_medico(
    id_medico: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médico no encontrado.")
    return _medico_to_response(medico)


@app.patch(
    "/medicos/{id_medico}",
    response_model=MedicoResponse,
    tags=["Médicos"],
    summary="Actualizar datos o dar de baja un médico. Todos los roles con RBAC geográfico.",
)
def actualizar_medico(
    id_medico: int,
    payload: MedicoUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médico no encontrado.")

    # Validar acceso por rol
    if current_user.es_responsable_unidad:
        if medico.clues_adscripcion != current_user.clues_unidad_asignada:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede modificar médicos de su propia unidad médica.",
            )
    elif current_user.es_admin_estatal:
        unidad = db.query(UnidadMedica).filter(UnidadMedica.clues == medico.clues_adscripcion).first()
        if not unidad or unidad.id_entidad != current_user.id_entidad:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede modificar médicos de unidades de su estado.",
            )

    datos = payload.model_dump(exclude_none=True)
    if "nombre_medico" in datos:
        medico.nombre_medico = cifrar(datos.pop("nombre_medico"))
    if "cedula" in datos:
        nueva_cedula = datos.pop("cedula")
        medico.cedula = cifrar(nueva_cedula)
        medico.cedula_hash = hash_sha256(nueva_cedula)
    for campo, valor in datos.items():
        setattr(medico, campo, valor)
    db.commit()
    db.refresh(medico)
    return _medico_to_response(medico)


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
# REGISTROS (antes: RECETAS)
# ===========================================================================

@app.get(
    "/registros",
    response_model=RegistroListResponse,
    tags=["Registros"],
    summary="Historial de registros (prescripciones) filtrado por rol.",
)
def listar_registros(
    solo_activos: bool = Query(True),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    marcar_registros_vencidos(db)
    filtro = apply_rbac_filter(current_user)

    query = (
        db.query(Registro)
        .options(
            joinedload(Registro.paciente),
            joinedload(Registro.medicamento),
            joinedload(Registro.medico),
            joinedload(Registro.diagnostico),
        )
    )

    if solo_activos:
        query = query.filter(Registro.es_activo == True)

    if filtro.filtrar_por_clues:
        # La prescripción "sigue al paciente": filtramos por unidad actual del paciente,
        # no por la unidad donde fue generada la prescripción.
        query = (
            query.join(Paciente, Registro.id_paciente == Paciente.id_paciente)
                 .filter(Paciente.clues_unidad_adscripcion == filtro.valor_clues)
        )
    elif filtro.filtrar_por_entidad:
        query = query.join(
            UnidadMedica, Registro.clues == UnidadMedica.clues
        ).filter(UnidadMedica.id_entidad == filtro.valor_entidad)

    total = query.count()
    registros = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    return RegistroListResponse(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        resultados=[_registro_to_response(r) for r in registros],
    )


@app.post(
    "/registros",
    response_model=RegistroResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Registros"],
    summary="Registrar una nueva prescripción.",
)
def crear_registro(
    payload: RegistroCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no puede registrar prescripciones.",
        )

    if current_user.es_responsable_unidad:
        if payload.clues != current_user.clues_unidad_asignada:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede registrar prescripciones en su propia unidad médica.",
            )

    paciente = db.query(Paciente).filter(
        Paciente.id_paciente == payload.id_paciente,
    ).first()
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado.",
        )
    _verificar_acceso_paciente(paciente, current_user, db)
    if not paciente.es_activo:
        paciente.es_activo = True

    if not db.query(Medico).filter(Medico.id_medico == payload.id_medico).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Médico con id '{payload.id_medico}' no encontrado.",
        )

    medicamento = db.query(CatMedicamento).filter(
        CatMedicamento.clave_cnis == payload.clave_cnis,
        CatMedicamento.es_activo == True,
    ).first()
    if not medicamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicamento '{payload.clave_cnis}' no encontrado en catálogo activo.",
        )

    if any([payload.dosis, payload.frecuencia, payload.duracion, payload.unidad_tiempo]):
        if not payload.fecha_primera_administracion:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La fecha de primera administración es obligatoria cuando se indica posología.",
            )

    nuevo = Registro(
        id_medico=payload.id_medico,
        id_paciente=payload.id_paciente,
        clave_cnis=payload.clave_cnis,
        clues=payload.clues,
        fecha_inicio_tratamiento=payload.fecha_inicio_tratamiento,
        fecha_primera_administracion=payload.fecha_primera_administracion,
        fecha_fin_tratamiento=payload.fecha_fin_tratamiento,
        dosis_administrada=payload.dosis_administrada,
        peso=payload.peso,
        talla=payload.talla,
        estatus_diagnostico=payload.estatus_diagnostico,
        confirmado_por=payload.confirmado_por,
        prescripcion=payload.prescripcion,
        dosis=payload.dosis,
        cantidad=payload.cantidad,
        frecuencia=payload.frecuencia,
        unidad_tiempo=payload.unidad_tiempo,
        duracion=payload.duracion,
        id_diagnostico=payload.id_diagnostico,
        id_usuario_registro=current_user.id_usuario,
        es_activo=True,
    )
    _aplicar_posologia(nuevo, medicamento.unidad, medicamento.unidad_de_medida)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    registro = (
        db.query(Registro)
        .options(joinedload(Registro.medicamento), joinedload(Registro.medico), joinedload(Registro.diagnostico))
        .filter(Registro.id_registro == nuevo.id_registro)
        .first()
    )
    return _registro_to_response(registro)


@app.post(
    "/registros/completo",
    response_model=RegistroCompletoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Registros"],
    summary="Registrar paciente + prescripción en una sola llamada. Crea el paciente si no existe.",
)
def crear_registro_completo(
    payload: RegistroCompletoCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no puede registrar prescripciones.",
        )

    # 1. Buscar paciente por CURP hash
    curp_hash = hash_sha256(payload.curp_paciente)
    paciente = db.query(Paciente).filter(Paciente.curp_hash == curp_hash).first()
    paciente_creado = False

    if not paciente:
        if not payload.nombre_completo:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="nombre_completo es requerido para registrar un paciente nuevo.",
            )

        # La CLUES del paciente: usa la explícita o toma la de la prescripción
        clues_paciente = (payload.clues_unidad_adscripcion or payload.clues).strip().upper()

        if current_user.es_responsable_unidad:
            if clues_paciente != current_user.clues_unidad_asignada:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo puede registrar pacientes en su propia unidad médica.",
                )

        paciente = Paciente(
            curp_hash=curp_hash,
            curp_paciente=cifrar(payload.curp_paciente),
            nombre_completo=cifrar(payload.nombre_completo),
            fecha_nacimiento=payload.fecha_nacimiento,
            clues_unidad_adscripcion=clues_paciente,
            es_activo=True,
            id_usuario_registro=current_user.id_usuario,
        )
        db.add(paciente)
        db.flush()  # Obtiene id_paciente sin hacer commit aún
        paciente_creado = True
    else:
        _verificar_acceso_paciente(paciente, current_user, db)
        if not paciente.es_activo:
            paciente.es_activo = True

    # 2. Validar CLUES de la prescripción
    if current_user.es_responsable_unidad:
        if payload.clues != current_user.clues_unidad_asignada:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede registrar prescripciones en su propia unidad médica.",
            )

    # 3. Validar médico
    if not db.query(Medico).filter(Medico.id_medico == payload.id_medico).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Médico con id '{payload.id_medico}' no encontrado.",
        )

    # 4. Validar medicamento activo
    medicamento = db.query(CatMedicamento).filter(
        CatMedicamento.clave_cnis == payload.clave_cnis,
        CatMedicamento.es_activo == True,
    ).first()
    if not medicamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicamento '{payload.clave_cnis}' no encontrado en catálogo activo.",
        )

    # 5. Crear registro (prescripción)
    nuevo = Registro(
        id_paciente=paciente.id_paciente,
        id_medico=payload.id_medico,
        clave_cnis=payload.clave_cnis,
        clues=payload.clues,
        fecha_inicio_tratamiento=payload.fecha_inicio_tratamiento,
        fecha_primera_administracion=payload.fecha_primera_administracion,
        fecha_fin_tratamiento=payload.fecha_fin_tratamiento,
        dosis_administrada=payload.dosis_administrada,
        peso=payload.peso,
        talla=payload.talla,
        estatus_diagnostico=payload.estatus_diagnostico,
        confirmado_por=payload.confirmado_por,
        prescripcion=payload.prescripcion,
        dosis=payload.dosis,
        cantidad=payload.cantidad,
        frecuencia=payload.frecuencia,
        unidad_tiempo=payload.unidad_tiempo,
        duracion=payload.duracion,
        id_diagnostico=payload.id_diagnostico,
        id_usuario_registro=current_user.id_usuario,
        es_activo=True,
    )
    if any([payload.dosis, payload.frecuencia, payload.duracion, payload.unidad_tiempo]):
        if not payload.fecha_primera_administracion:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La fecha de primera administración es obligatoria cuando se indica posología.",
            )
    _aplicar_posologia(nuevo, medicamento.unidad, medicamento.unidad_de_medida)
    db.add(nuevo)
    db.flush()  # obtiene id_registro sin commit

    # 6. Expediente: upsert en expedientes_paciente
    if payload.numero_expediente:
        expediente = db.query(ExpedientePaciente).filter(
            ExpedientePaciente.id_paciente == paciente.id_paciente,
            ExpedientePaciente.clues == payload.clues,
        ).first()
        if expediente:
            expediente.numero_expediente = payload.numero_expediente
        else:
            db.add(ExpedientePaciente(
                id_paciente=paciente.id_paciente,
                clues=payload.clues,
                numero_expediente=payload.numero_expediente,
            ))

    db.commit()
    db.refresh(nuevo)

    registro = (
        db.query(Registro)
        .options(
            joinedload(Registro.paciente),
            joinedload(Registro.medicamento),
            joinedload(Registro.medico),
            joinedload(Registro.diagnostico),
        )
        .filter(Registro.id_registro == nuevo.id_registro)
        .first()
    )
    # _registro_to_response ya puebla curp_paciente y nombre_paciente via joinedload.
    # Usamos dict.update para agregar paciente_creado sin conflicto de clave duplicada.
    base_dict = _registro_to_response(registro).model_dump()
    base_dict["paciente_creado"] = paciente_creado
    return RegistroCompletoResponse(**base_dict)


@app.get(
    "/registros/{id_registro}",
    response_model=RegistroResponse,
    tags=["Registros"],
    summary="Detalle completo de un registro (prescripción).",
)
def obtener_registro(
    id_registro: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    registro = (
        db.query(Registro)
        .options(
            joinedload(Registro.paciente),
            joinedload(Registro.medicamento),
            joinedload(Registro.medico),
            joinedload(Registro.diagnostico),
        )
        .filter(Registro.id_registro == id_registro)
        .first()
    )
    if not registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado.")

    _verificar_acceso_registro(registro, current_user, db)
    return _registro_to_response(registro)


@app.patch(
    "/registros/{id_registro}",
    response_model=RegistroResponse,
    tags=["Registros"],
    summary="Actualización parcial de un registro.",
)
def actualizar_registro(
    id_registro: int,
    payload: RegistroUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no puede modificar registros.",
        )

    registro = (
        db.query(Registro)
        .options(joinedload(Registro.medicamento), joinedload(Registro.medico), joinedload(Registro.diagnostico))
        .filter(Registro.id_registro == id_registro)
        .first()
    )
    if not registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado.")

    _verificar_acceso_registro(registro, current_user, db)

    CAMPOS_POSOLOGIA = {"dosis", "cantidad", "frecuencia", "unidad_tiempo", "duracion",
                        "fecha_primera_administracion"}
    campos_actualizados = payload.model_dump(exclude_none=True)
    for campo, valor in campos_actualizados.items():
        setattr(registro, campo, valor)

    # Recalcular prescripcion, total y fecha_fin si se modificó algún campo de posología
    if CAMPOS_POSOLOGIA & set(campos_actualizados):
        unidad_med = registro.medicamento.unidad if registro.medicamento else None
        unidad_dm = registro.medicamento.unidad_de_medida if registro.medicamento else None
        _aplicar_posologia(registro, unidad_med, unidad_dm)

    registro.id_usuario_registro = current_user.id_usuario
    db.commit()
    db.refresh(registro)
    return _registro_to_response(registro)


@app.delete(
    "/registros/{id_registro}",
    response_model=RegistroResponse,
    tags=["Registros"],
    summary="Soft Delete: anula un registro por error de captura.",
)
def anular_registro(
    id_registro: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no puede anular registros.",
        )

    registro = (
        db.query(Registro)
        .options(joinedload(Registro.medicamento), joinedload(Registro.medico), joinedload(Registro.diagnostico))
        .filter(Registro.id_registro == id_registro)
        .first()
    )
    if not registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado.")

    _verificar_acceso_registro(registro, current_user, db)

    if not registro.es_activo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El registro ya se encuentra anulado.",
        )

    registro.es_activo = False
    registro.id_usuario_registro = current_user.id_usuario
    db.commit()
    db.refresh(registro)
    return _registro_to_response(registro)


@app.patch(
    "/registros/{id_registro}/validar-continuidad",
    response_model=RegistroResponse,
    tags=["Registros"],
    summary="Valida la continuidad de un tratamiento: actualiza la fecha de fin y reactiva el registro si estaba vencido.",
)
def validar_continuidad(
    id_registro: int,
    payload: ValidarContinuidadRequest,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no puede validar continuidad de registros.",
        )

    registro = (
        db.query(Registro)
        .options(joinedload(Registro.medicamento), joinedload(Registro.medico), joinedload(Registro.diagnostico))
        .filter(Registro.id_registro == id_registro)
        .first()
    )
    if not registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado.")

    # RBAC: RESPONSABLE_UNIDAD solo puede validar registros de su unidad
    if current_user.es_responsable_unidad:
        if registro.clues != current_user.clues_unidad_asignada:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede validar registros de otra unidad médica.",
            )

    # Si tiene posología guardada → calcular nueva fecha desde hoy
    if registro.duracion and registro.unidad_tiempo:
        factor = {"días": 1, "semanas": 7, "meses": 30}.get(registro.unidad_tiempo, 1)
        registro.fecha_fin_tratamiento = date.today() + timedelta(days=registro.duracion * factor)
    else:
        # Fallback legacy: requiere fecha manual
        if not payload.nueva_fecha_fin_tratamiento:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Este registro no tiene posología guardada. Indica la nueva fecha de fin manualmente.",
            )
        registro.fecha_fin_tratamiento = payload.nueva_fecha_fin_tratamiento

    registro.es_activo = True
    registro.id_usuario_registro = current_user.id_usuario
    db.commit()
    db.refresh(registro)
    return _registro_to_response(registro)


@app.post(
    "/registros/{id_registro}/reemplazar",
    response_model=RegistroResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Registros"],
    summary="Reemplaza una prescripción con cambios: crea una nueva activa y anula la original.",
)
def reemplazar_registro(
    id_registro: int,
    payload: RegistroUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no puede reemplazar registros.",
        )

    original = (
        db.query(Registro)
        .options(
            joinedload(Registro.medicamento),
            joinedload(Registro.medico),
            joinedload(Registro.paciente),
            joinedload(Registro.diagnostico),
        )
        .filter(Registro.id_registro == id_registro)
        .first()
    )
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado.")

    _verificar_acceso_registro(original, current_user, db)

    # Copiar todos los campos del original al nuevo registro
    campos_nuevo = {
        "id_medico": original.id_medico,
        "id_paciente": original.id_paciente,
        "clave_cnis": original.clave_cnis,
        "clues": original.clues,
        "fecha_inicio_tratamiento": original.fecha_inicio_tratamiento,
        "fecha_primera_administracion": original.fecha_primera_administracion,
        "fecha_fin_tratamiento": original.fecha_fin_tratamiento,
        "dosis_administrada": original.dosis_administrada,
        "peso": original.peso,
        "talla": original.talla,
        "estatus_diagnostico": original.estatus_diagnostico,
        "confirmado_por": original.confirmado_por,
        "prescripcion": original.prescripcion,
        "dosis": original.dosis,
        "cantidad": original.cantidad,
        "frecuencia": original.frecuencia,
        "unidad_tiempo": original.unidad_tiempo,
        "duracion": original.duracion,
        "total_medicamento": original.total_medicamento,
        "id_diagnostico": original.id_diagnostico,
        "id_usuario_registro": current_user.id_usuario,
        "id_registro_origen": original.id_registro,
        "es_activo": True,
    }

    # Aplicar los cambios del payload sobre la copia
    for campo, valor in payload.model_dump(exclude_none=True).items():
        if campo != "es_activo":  # no permitir cambiar el estado directamente
            campos_nuevo[campo] = valor

    nuevo = Registro(**campos_nuevo)

    # Recalcular posología si aplica
    unidad_med = original.medicamento.unidad if original.medicamento else None
    unidad_dm = original.medicamento.unidad_de_medida if original.medicamento else None
    _aplicar_posologia(nuevo, unidad_med, unidad_dm)

    # Anular el registro original
    original.es_activo = False
    original.id_usuario_registro = current_user.id_usuario

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    nuevo_cargado = (
        db.query(Registro)
        .options(
            joinedload(Registro.paciente),
            joinedload(Registro.medicamento),
            joinedload(Registro.medico),
            joinedload(Registro.diagnostico),
        )
        .filter(Registro.id_registro == nuevo.id_registro)
        .first()
    )
    return _registro_to_response(nuevo_cargado)


# ===========================================================================
# NOTIFICACIONES
# ===========================================================================

@app.get(
    "/notificaciones",
    response_model=NotificacionListResponse,
    tags=["Notificaciones"],
    summary="Registros que requieren validación de continuidad (vencidos o por vencer en 7 días).",
)
def listar_notificaciones(
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    from datetime import timedelta

    # Primero marca los vencidos en BD
    marcar_registros_vencidos(db)

    # Ventana de alerta: registros cuyo plazo de continuidad vence en los próximos 7 días
    # fecha_fin + 30 días <= hoy + 7  →  fecha_fin <= hoy - 23
    fecha_alerta = date.today() - timedelta(days=23)

    filtro = apply_rbac_filter(current_user)

    query = (
        db.query(Registro)
        .options(
            joinedload(Registro.paciente),
            joinedload(Registro.medicamento),
        )
        .filter(
            Registro.fecha_fin_tratamiento.isnot(None),
            Registro.fecha_fin_tratamiento <= fecha_alerta,
        )
    )

    if filtro.filtrar_por_clues:
        query = query.filter(Registro.clues == filtro.valor_clues)
    elif filtro.filtrar_por_entidad:
        query = query.join(
            UnidadMedica, Registro.clues == UnidadMedica.clues
        ).filter(UnidadMedica.id_entidad == filtro.valor_entidad)

    registros = query.order_by(Registro.fecha_fin_tratamiento.asc()).all()

    resultados = []
    for r in registros:
        fecha_limite = r.fecha_fin_tratamiento + timedelta(days=30)
        dias_restantes = (fecha_limite - date.today()).days
        resultados.append(NotificacionResponse(
            id_registro=r.id_registro,
            id_paciente=r.id_paciente,
            nombre_paciente=descifrar(r.paciente.nombre_completo) if r.paciente else "—",
            clave_cnis=r.clave_cnis,
            descripcion_medicamento=r.medicamento.descripcion if r.medicamento else None,
            clues=r.clues,
            fecha_fin_tratamiento=r.fecha_fin_tratamiento,
            fecha_limite=fecha_limite,
            dias_restantes=dias_restantes,
            es_activo=r.es_activo,
            fecha_inicio_tratamiento=r.fecha_inicio_tratamiento,
            dosis_administrada=r.dosis_administrada,
            peso=r.peso,
            talla=r.talla,
            prescripcion=r.prescripcion,
            duracion=r.duracion,
            unidad_tiempo=r.unidad_tiempo,
        ))

    return NotificacionListResponse(total=len(resultados), resultados=resultados)


@app.get(
    "/notificaciones/transferencias",
    response_model=NotificacionTransferenciaListResponse,
    tags=["Notificaciones"],
    summary="Traslados de pacientes pendientes de aceptar (RESPONSABLE_UNIDAD y SUPER_ADMIN).",
)
def listar_notificaciones_transferencia(
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    if current_user.es_admin_estatal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El Administrador Estatal no tiene notificaciones de traslado.",
        )

    query = (
        db.query(NotificacionTransferencia)
        .options(
            joinedload(NotificacionTransferencia.paciente),
            joinedload(NotificacionTransferencia.unidad_origen),
            joinedload(NotificacionTransferencia.unidad_destino),
            joinedload(NotificacionTransferencia.usuario_traslado),
        )
        .filter(NotificacionTransferencia.leida == False)
    )

    if current_user.es_responsable_unidad:
        query = query.filter(
            NotificacionTransferencia.clues_unidad_origen == current_user.clues_unidad_asignada
        )

    notifs = query.order_by(NotificacionTransferencia.fecha_traslado.desc()).all()

    resultados = [
        NotificacionTransferenciaResponse(
            id=n.id,
            id_paciente=n.id_paciente,
            nombre_paciente=descifrar(n.paciente.nombre_completo) if n.paciente else "—",
            curp_paciente=descifrar(n.paciente.curp_paciente) if n.paciente else "—",
            clues_unidad_origen=n.clues_unidad_origen,
            nombre_unidad_origen=n.unidad_origen.nombre_de_la_unidad if n.unidad_origen else None,
            clues_unidad_destino=n.clues_unidad_destino,
            nombre_unidad_destino=n.unidad_destino.nombre_de_la_unidad if n.unidad_destino else None,
            nombre_usuario_traslado=n.usuario_traslado.nombre_usuario if n.usuario_traslado else None,
            fecha_traslado=n.fecha_traslado,
        )
        for n in notifs
    ]

    return NotificacionTransferenciaListResponse(total=len(resultados), resultados=resultados)


@app.patch(
    "/notificaciones/transferencias/{id_notificacion}/leer",
    tags=["Notificaciones"],
    summary="Marcar traslado como leído por la unidad de origen.",
)
def marcar_traslado_leido(
    id_notificacion: int,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    if current_user.es_admin_estatal:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso.")

    notif = db.query(NotificacionTransferencia).filter(
        NotificacionTransferencia.id == id_notificacion
    ).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada.")

    if current_user.es_responsable_unidad and notif.clues_unidad_origen != current_user.clues_unidad_asignada:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo la unidad de origen puede aceptar este traslado.",
        )

    notif.leida = True
    notif.id_usuario_leida = current_user.id_usuario
    notif.fecha_leida = datetime.now(timezone.utc)
    db.commit()

    return {"ok": True}


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
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    filtro = apply_rbac_filter(current_user)

    query = (
        db.query(Registro)
        .join(Paciente, Registro.id_paciente == Paciente.id_paciente)
        .join(CatMedicamento, Registro.clave_cnis == CatMedicamento.clave_cnis)
        .options(
            joinedload(Registro.paciente),
            joinedload(Registro.medicamento),
            joinedload(Registro.medico),
            joinedload(Registro.diagnostico),
        )
    )

    if solo_activos:
        query = query.filter(Registro.es_activo == True, Paciente.es_activo == True)

    if filtro.filtrar_por_clues:
        query = query.filter(Paciente.clues_unidad_adscripcion == filtro.valor_clues)
    elif filtro.filtrar_por_entidad:
        query = query.join(
            UnidadMedica, Registro.clues == UnidadMedica.clues
        ).filter(UnidadMedica.id_entidad == filtro.valor_entidad)

    if fecha_inicio:
        query = query.filter(Registro.fecha_primera_administracion >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Registro.fecha_primera_administracion <= fecha_fin)

    registros = query.all()

    return {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "total_registros": len(registros),
        "filtros_aplicados": {
            "fecha_inicio": str(fecha_inicio) if fecha_inicio else None,
            "fecha_fin": str(fecha_fin) if fecha_fin else None,
            "solo_activos": solo_activos,
            "rbac_clues": filtro.valor_clues,
            "rbac_entidad": filtro.valor_entidad,
        },
        "datos": [
            {
                "id_registro": r.id_registro,
                "id_paciente": r.id_paciente,
                "curp_paciente": descifrar(r.paciente.curp_paciente) if r.paciente else None,
                "nombre_paciente": descifrar(r.paciente.nombre_completo) if r.paciente else None,
                "diagnostico": descifrar_o_none(r.paciente.diagnostico_actual) if r.paciente else None,
                "clues_unidad": r.clues,
                "medico": descifrar(r.medico.nombre_medico) if r.medico else None,
                "cedula_medico": descifrar(r.medico.cedula) if r.medico else None,
                "dias_adherencia": (
                    (date.today() - r.fecha_inicio_tratamiento).days
                    if r.fecha_inicio_tratamiento else None
                ),
                "clave_cnis": r.clave_cnis,
                "descripcion_medicamento": r.medicamento.descripcion if r.medicamento else None,
                "prescripcion": r.prescripcion,
                "fecha_inicio_tratamiento": (
                    r.fecha_inicio_tratamiento.isoformat()
                    if r.fecha_inicio_tratamiento else None
                ),
                "fecha_primera_administracion": (
                    r.fecha_primera_administracion.isoformat()
                    if r.fecha_primera_administracion else None
                ),
                "fecha_registro_sistema": r.fecha_registro_sistema.isoformat(),
                "es_activo": r.es_activo,
            }
            for r in registros
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
            func.count(Paciente.id_paciente.distinct()).label("total_pacientes"),
            func.count(Registro.id_registro.distinct()).label("total_registros"),
        )
        .outerjoin(Paciente, Paciente.clues_unidad_adscripcion == UnidadMedica.clues)
        .outerjoin(Registro, (Registro.clues == UnidadMedica.clues) & (Registro.es_activo == True))
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
                "total_registros_activos": r.total_registros,
            }
            for r in resultados
        ],
    }


_MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


@app.get(
    "/reportes/rtm",
    response_model=RtmResponse,
    tags=["Reportes"],
    summary="Requerimiento Teórico Mensual por unidad. Solo SUPER_ADMIN.",
)
def reporte_rtm(
    clues: str = Query(..., description="CLUES de la unidad a consultar."),
    meses: int = Query(7, ge=1, le=24, description="Número de meses a proyectar (actual + siguientes)."),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_super_admin),
):
    clues_norm = clues.strip().upper()

    # 1. Construir la lista de meses (año, mes) a proyectar
    hoy = date.today()
    meses_list: list[tuple[int, int]] = []
    y, m = hoy.year, hoy.month
    for _ in range(meses):
        meses_list.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    # 2. Prescripciones activas con posología completa en la unidad solicitada
    registros = (
        db.query(Registro)
        .options(joinedload(Registro.medicamento))
        .filter(
            Registro.clues == clues_norm,
            Registro.es_activo == True,
            Registro.dosis.isnot(None),
            Registro.cantidad.isnot(None),
            Registro.frecuencia.isnot(None),
            Registro.fecha_primera_administracion.isnot(None),
            Registro.fecha_fin_tratamiento.isnot(None),
        )
        .all()
    )

    # 3. Calcular aportes proporcionales por mes
    # totales[clave_cnis][(year, month)] = cantidad total en unidad_de_medida
    totales: dict[str, dict[tuple[int, int], float]] = defaultdict(lambda: defaultdict(float))

    for r in registros:
        consumo_diario = r.dosis * r.cantidad * (24 / r.frecuencia)
        for (ay, am) in meses_list:
            inicio_mes = date(ay, am, 1)
            # Usamos el primer día del mes siguiente como límite exclusivo,
            # consistente con fecha_fin_tratamiento (también exclusiva).
            fin_mes_exclusivo = date(ay + 1, 1, 1) if am == 12 else date(ay, am + 1, 1)
            overlap_inicio = max(inicio_mes, r.fecha_primera_administracion)
            overlap_fin    = min(fin_mes_exclusivo, r.fecha_fin_tratamiento)
            if overlap_inicio < overlap_fin:
                dias = (overlap_fin - overlap_inicio).days
                totales[r.clave_cnis][(ay, am)] += consumo_diario * dias

    # 4. Información de medicamentos
    claves_con_datos = set(totales.keys())
    meds_info: dict[str, CatMedicamento] = {}
    if claves_con_datos:
        meds_info = {
            med.clave_cnis: med
            for med in db.query(CatMedicamento).filter(
                CatMedicamento.clave_cnis.in_(claves_con_datos)
            ).all()
        }

    # 5. Construir filas ordenadas por clave_cnis
    cabeceras = [f"{_MESES_ES[am]} {ay}" for (ay, am) in meses_list]
    filas = []
    for clave in sorted(claves_con_datos):
        med = meds_info.get(clave)
        items = [
            RtmMesItem(
                anio=ay,
                mes=am,
                etiqueta=f"{_MESES_ES[am]} {ay}",
                cantidad=round(totales[clave].get((ay, am), 0.0), 2),
            )
            for (ay, am) in meses_list
        ]
        filas.append(RtmFilaResponse(
            clave_cnis=clave,
            descripcion=med.descripcion if med else clave,
            grupo=med.grupo if med else None,
            unidad_de_medida=med.unidad_de_medida if med else None,
            meses=items,
        ))

    # 6. Nombre de la unidad
    unidad = db.query(UnidadMedica).filter(UnidadMedica.clues == clues_norm).first()

    return RtmResponse(
        clues=clues_norm,
        nombre_unidad=unidad.nombre_de_la_unidad if unidad else None,
        generado_en=datetime.now(timezone.utc).isoformat(),
        cabeceras=cabeceras,
        filas=filas,
    )


# ===========================================================================
# CATÁLOGOS — Diagnósticos
# ===========================================================================

@app.get(
    "/catalogos/diagnosticos",
    response_model=list[DiagnosticoResponse],
    tags=["Catálogos"],
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


@app.post(
    "/catalogos/diagnosticos",
    response_model=DiagnosticoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Catálogos"],
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


@app.patch(
    "/catalogos/diagnosticos/{id_diagnostico}",
    response_model=DiagnosticoResponse,
    tags=["Catálogos"],
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
    clues: str | None = Query(None, description="Si se indica, devuelve solo medicamentos asignados a esa unidad."),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    query = db.query(CatMedicamento)
    if solo_activos:
        query = query.filter(CatMedicamento.es_activo == True)
    if clues:
        query = query.join(
            UnidadMedicamento,
            UnidadMedicamento.clave_cnis == CatMedicamento.clave_cnis,
        ).filter(UnidadMedicamento.clues == clues)
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
    current_user: UsuarioActivo = Depends(require_password_cambiado),
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
    response_model=UsuarioCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Usuarios"],
    summary="Crear una cuenta de usuario. Solo SUPER_ADMIN. Devuelve contraseña temporal.",
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
    password_temporal = _generar_password_temporal()
    nuevo = Usuario(
        nombre_usuario=payload.nombre_usuario,
        email=str(payload.email),
        hashed_password=hash_password(password_temporal),
        rol_nombre=payload.rol_nombre,
        clues_unidad_asignada=payload.clues_unidad_asignada,
        id_entidad=payload.id_entidad,
        debe_cambiar_password=True,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
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


@app.post(
    "/usuarios/me/cambiar-password",
    response_model=UsuarioResponse,
    tags=["Usuarios"],
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
    usuario.hashed_password = hash_password(payload.password_nueva)
    usuario.debe_cambiar_password = False
    db.commit()
    db.refresh(usuario)
    return usuario


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

import secrets
import string

def _generar_password_temporal(longitud: int = 12) -> str:
    """Genera una contraseña aleatoria alfanumérica para el primer acceso."""
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(longitud))


def _paciente_to_response(
    p: Paciente,
    tiene_prescripcion_activa: bool = False,
    medicamentos_activos: list[str] | None = None,
    diagnosticos_activos: list[str] | None = None,
) -> PacienteResponse:
    """Descifra los campos LargeBinary y construye el schema de respuesta."""
    return PacienteResponse(
        id_paciente=p.id_paciente,
        curp_paciente=descifrar(p.curp_paciente),
        nombre_completo=descifrar(p.nombre_completo),
        diagnostico_actual=descifrar_o_none(p.diagnostico_actual),
        clues_unidad_adscripcion=p.clues_unidad_adscripcion,
        fecha_nacimiento=p.fecha_nacimiento,
        es_activo=p.es_activo,
        estatus_evolucion=p.estatus_evolucion,
        fecha_registro=p.fecha_registro,
        id_usuario_registro=p.id_usuario_registro,
        dias_adherencia=None,
        tiene_prescripcion_activa=tiene_prescripcion_activa,
        medicamentos_activos=medicamentos_activos or [],
        diagnosticos_activos=diagnosticos_activos or [],
    )


def _get_medicamentos_activos(id_paciente: int, db: Session) -> list[str]:
    """Retorna las descripciones de medicamentos de prescripciones activas del paciente."""
    return _get_medicamentos_y_adherencia(id_paciente, db)[0]


def _get_medicamentos_y_adherencia(id_paciente: int, db: Session) -> tuple[list[str], list[int | None]]:
    """
    Retorna (descripciones, dias_adherencia) de medicamentos de prescripciones activas
    del paciente, alineados posicionalmente. Si hay varios registros activos para el
    mismo medicamento, se usa el más reciente (`fecha_registro_sistema`).
    """
    rows = (
        db.query(CatMedicamento.descripcion, CatMedicamento.clave_cnis, Registro.fecha_inicio_tratamiento)
        .join(Registro, Registro.clave_cnis == CatMedicamento.clave_cnis)
        .filter(Registro.id_paciente == id_paciente, Registro.es_activo == True)
        .order_by(Registro.fecha_registro_sistema.desc())
        .all()
    )
    medicamentos: list[str] = []
    adherencias: list[int | None] = []
    vistos: set[str] = set()
    for desc, clave, fecha_inicio in rows:
        label = desc[:60] + "..." if desc and len(desc) > 60 else desc or clave
        if label in vistos:
            continue
        vistos.add(label)
        medicamentos.append(label)
        adherencias.append((date.today() - fecha_inicio).days if fecha_inicio else None)
    return medicamentos, adherencias


def _get_diagnosticos_activos(id_paciente: int, db: Session) -> list[str]:
    """Retorna los nombres de diagnósticos de prescripciones activas del paciente."""
    rows = (
        db.query(CatDiagnostico.nombre)
        .join(Registro, Registro.id_diagnostico == CatDiagnostico.id_diagnostico)
        .filter(Registro.id_paciente == id_paciente, Registro.es_activo == True)
        .distinct()
        .all()
    )
    return [nombre for (nombre,) in rows]


def _tiene_prescripcion_activa(id_paciente: int, db: Session) -> bool:
    """Retorna True si el paciente tiene al menos un registro con es_activo=True."""
    return db.query(
        exists().where(
            Registro.id_paciente == id_paciente,
            Registro.es_activo == True,
        )
    ).scalar()


def _medico_to_response(m: Medico) -> MedicoResponse:
    """Descifra los campos LargeBinary y construye el schema de respuesta."""
    return MedicoResponse(
        id_medico=m.id_medico,
        nombre_medico=descifrar(m.nombre_medico),
        cedula=descifrar(m.cedula),
        email=m.email,
        clues_adscripcion=m.clues_adscripcion,
        es_activo=m.es_activo,
    )


def _pluralizar_unidad(unidad: str, cantidad: float) -> str:
    """Pluraliza la unidad del medicamento según cantidad. Ej: "tableta" → "tabletas"."""
    if cantidad == 1:
        return unidad
    u = unidad.lower()
    if u in {"ml", "mg", "mcg", "g", "ui", "dosis"}:
        return unidad
    if u.endswith("ón"):
        return unidad[:-2] + "ones"
    if u[-1] in "aeiouáéíóú":
        return unidad + "s"
    return unidad + "es"


def _calcular_prescripcion_y_total(
    dosis: float,
    frecuencia: int,
    duracion: int,
    unidad_tiempo: str,
    unidad: str,
    cantidad: float | None = None,
    unidad_de_medida: str | None = None,
) -> tuple[str, float]:
    """Retorna (texto_prescripcion, total_medicamento) a partir de los campos de posología."""
    factor = {"días": 1, "semanas": 7, "meses": 30}.get(unidad_tiempo, 1)
    duracion_dias = duracion * factor
    total = dosis * (24 / frecuencia) * duracion_dias
    unidad_txt = _pluralizar_unidad(unidad, dosis)
    if cantidad and unidad_de_medida:
        texto = (
            f"{dosis:g} {unidad_txt} de {cantidad:g} {unidad_de_medida}, "
            f"cada {frecuencia} horas, por {duracion} {unidad_tiempo}"
        )
    else:
        texto = f"{dosis:g} {unidad_txt}, cada {frecuencia} horas, por {duracion} {unidad_tiempo}"
    return texto, round(total, 2)


def _aplicar_posologia(
    registro: Registro,
    unidad_medicamento: str | None,
    unidad_de_medida: str | None = None,
) -> None:
    """Calcula prescripcion, total_medicamento y fecha_fin_tratamiento si la posología está completa."""
    if not (registro.dosis and registro.frecuencia and registro.duracion and registro.unidad_tiempo):
        return
    unidad = unidad_medicamento or "unidad"
    texto, total = _calcular_prescripcion_y_total(
        registro.dosis, registro.frecuencia, registro.duracion,
        registro.unidad_tiempo, unidad,
        cantidad=registro.cantidad,
        unidad_de_medida=unidad_de_medida,
    )
    registro.prescripcion = texto
    registro.total_medicamento = total
    # Auto-calcular fecha_fin_tratamiento a partir de la primera administración
    if registro.fecha_primera_administracion:
        factor = {"días": 1, "semanas": 7, "meses": 30}.get(registro.unidad_tiempo, 1)
        registro.fecha_fin_tratamiento = (
            registro.fecha_primera_administracion + timedelta(days=registro.duracion * factor)
        )


def _registro_to_response(r: Registro) -> RegistroResponse:
    """Construye RegistroResponse descifrando los campos del médico y paciente embebidos."""
    return RegistroResponse(
        id_registro=r.id_registro,
        id_medico=r.id_medico,
        id_paciente=r.id_paciente,
        clave_cnis=r.clave_cnis,
        clues=r.clues,
        fecha_inicio_tratamiento=r.fecha_inicio_tratamiento,
        fecha_primera_administracion=r.fecha_primera_administracion,
        fecha_fin_tratamiento=r.fecha_fin_tratamiento,
        dosis_administrada=r.dosis_administrada,
        peso=r.peso,
        talla=r.talla,
        estatus_diagnostico=r.estatus_diagnostico,
        confirmado_por=r.confirmado_por,
        prescripcion=r.prescripcion,
        dosis=r.dosis,
        cantidad=r.cantidad,
        frecuencia=r.frecuencia,
        unidad_tiempo=r.unidad_tiempo,
        duracion=r.duracion,
        total_medicamento=r.total_medicamento,
        id_registro_origen=r.id_registro_origen,
        es_activo=r.es_activo,
        fecha_registro_sistema=r.fecha_registro_sistema,
        id_usuario_registro=r.id_usuario_registro,
        nombre_paciente=descifrar(r.paciente.nombre_completo) if r.paciente else None,
        curp_paciente=descifrar(r.paciente.curp_paciente) if r.paciente else None,
        id_diagnostico=r.id_diagnostico,
        medicamento=MedicamentoResponse.model_validate(r.medicamento) if r.medicamento else None,
        medico=_medico_to_response(r.medico) if r.medico else None,
        diagnostico=DiagnosticoResponse.model_validate(r.diagnostico) if r.diagnostico else None,
    )


def _calcular_adherencia(id_paciente: int, db: Session) -> int | None:
    """
    Retorna los días transcurridos desde fecha_inicio_tratamiento del registro
    activo más reciente del paciente. Retorna None si no hay registro activo con fecha.
    """
    registro = (
        db.query(Registro)
        .filter(
            Registro.id_paciente == id_paciente,
            Registro.es_activo == True,
            Registro.fecha_inicio_tratamiento.isnot(None),
        )
        .order_by(Registro.fecha_registro_sistema.desc())
        .first()
    )
    if registro and registro.fecha_inicio_tratamiento:
        return (date.today() - registro.fecha_inicio_tratamiento).days
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


def marcar_registros_vencidos(db: Session) -> int:
    """
    Marca es_activo=False en todos los registros activos cuyo plazo de continuidad
    ya venció: fecha_fin_tratamiento + 30 días <= hoy.
    Retorna el número de registros marcados. Se llama al inicio de los endpoints
    de lectura relevantes (lazy marking — sin scheduler externo).
    """
    from datetime import timedelta
    fecha_limite = date.today() - timedelta(days=30)
    resultado = db.execute(
        update(Registro)
        .where(
            Registro.es_activo == True,
            Registro.fecha_fin_tratamiento.isnot(None),
            Registro.fecha_fin_tratamiento <= fecha_limite,
        )
        .values(es_activo=False)
    )
    db.commit()
    return resultado.rowcount


def _verificar_acceso_registro(
    registro: Registro,
    usuario: UsuarioActivo,
    db: Session,
) -> None:
    if usuario.es_super_admin:
        return
    if usuario.es_responsable_unidad:
        # La prescripción "sigue al paciente": el acceso se determina por la unidad
        # actual del paciente, no por la unidad donde fue generada la prescripción.
        paciente = db.query(Paciente).filter(
            Paciente.id_paciente == registro.id_paciente
        ).first()
        clues_paciente = paciente.clues_unidad_adscripcion if paciente else registro.clues
        if clues_paciente != usuario.clues_unidad_asignada:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a registros de pacientes de otra unidad médica.",
            )
        return
    if usuario.es_admin_estatal:
        unidad = db.query(UnidadMedica).filter(
            UnidadMedica.clues == registro.clues
        ).first()
        if not unidad or unidad.id_entidad != usuario.id_entidad:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a registros de otro estado.",
            )
