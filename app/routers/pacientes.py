"""Router de pacientes: padrón, búsquedas, expedientes y reacciones adversas."""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exists, func
from sqlalchemy.orm import Session, joinedload

from app.auth import (
    UsuarioActivo,
    _verificar_clues_en_ambito,
    apply_rbac_filter,
    require_password_cambiado,
)
from app.config import ESTATUS_EVOLUCION_HABILITADO, REACCIONES_ADVERSAS_HABILITADO
from app.crypto import hash_sha256
from app.database import get_db
from app.models import (
    CatMedicamento,
    ExpedientePaciente,
    NotificacionTransferencia,
    Paciente,
    ReaccionAdversa,
    Registro,
    UnidadMedica,
)
from app.schemas import (
    BajaPacienteRequest,
    BusquedaCurpRequest,
    BusquedaCurpResponse,
    BusquedaNombreItem,
    BusquedaNombreResponse,
    ExpedienteCreate,
    ExpedienteResponse,
    PacienteCreate,
    PacienteListResponse,
    PacienteResponse,
    PacienteUpdate,
    ReaccionAdversaCreate,
    ReaccionAdversaResponse,
    RegistroListResponse,
)
from app.services.pacientes import (
    _calcular_adherencia,
    _get_diagnosticos_activos,
    _get_medicamentos_y_adherencia,
    _obtener_paciente_por_identificador,
    _paciente_to_response,
    _tiene_prescripcion_activa,
    _verificar_acceso_paciente,
)
from app.services.registros import _registro_to_response, marcar_registros_vencidos
from app.services.utils import _normalizar_texto, _serializar_motivo_baja

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])


@router.get(
    "",
    response_model=PacienteListResponse,
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
        datos = _paciente_to_response(p, tiene_prescripcion_activa=tiene, medicamentos_activos=meds, diagnosticos_activos=diags, db=db)
        datos.adherencia_medicamentos = adherencias
        datos.dias_adherencia = _calcular_adherencia(p.id_paciente, db)
        resultados.append(datos)

    return PacienteListResponse(
        total=total, pagina=pagina, por_pagina=por_pagina, resultados=resultados
    )


@router.post(
    "",
    response_model=PacienteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registro de un nuevo paciente.",
)
def crear_paciente(
    payload: PacienteCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    _verificar_clues_en_ambito(payload.clues_unidad_adscripcion, current_user, db)

    curp_hash = hash_sha256(payload.curp_paciente)
    if db.query(Paciente).filter(Paciente.curp_hash == curp_hash).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un paciente con CURP '{payload.curp_paciente}'.",
        )

    nuevo = Paciente(
        curp_hash=curp_hash,
        curp_paciente=payload.curp_paciente,
        nombre_completo=payload.nombre_completo,
        diagnostico_actual=payload.diagnostico_actual if payload.diagnostico_actual else None,
        clues_unidad_adscripcion=payload.clues_unidad_adscripcion,
        fecha_nacimiento=payload.fecha_nacimiento,
        es_activo=True,
        id_usuario_registro=current_user.id_usuario,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    respuesta = _paciente_to_response(nuevo, tiene_prescripcion_activa=False, db=db)
    respuesta.dias_adherencia = None
    return respuesta


@router.post(
    "/buscar",
    response_model=BusquedaCurpResponse,
    summary="Búsqueda nacional de paciente por CURP. Sin filtro RBAC — todos los roles.",
)
def buscar_paciente_por_curp(
    payload: BusquedaCurpRequest,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    curp_normalizada = payload.curp
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
        nombre_completo=paciente.nombre_completo,
        fecha_nacimiento=paciente.fecha_nacimiento,
        clues_unidad_adscripcion=paciente.clues_unidad_adscripcion,
        nombre_unidad=unidad.nombre_de_la_unidad if unidad else None,
        total_registros=total_registros,
    )


@router.get(
    "/buscar-por-nombre",
    response_model=BusquedaNombreResponse,
    summary="Búsqueda de pacientes por nombre filtrada automáticamente por rol.",
)
def buscar_pacientes_por_nombre(
    q: str = Query(..., min_length=3, description="Texto a buscar en el nombre completo del paciente."),
    limite: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    tokens_busqueda = _normalizar_texto(q).split()
    filtro = apply_rbac_filter(current_user)

    query = db.query(Paciente)
    if filtro.filtrar_por_clues:
        query = query.filter(Paciente.clues_unidad_adscripcion == filtro.valor_clues)
    elif filtro.filtrar_por_entidad:
        query = query.join(UnidadMedica).filter(
            UnidadMedica.id_entidad == filtro.valor_entidad
        )

    candidatos: list[tuple[Paciente, str, str]] = []
    for paciente in query.order_by(Paciente.id_paciente).all():
        nombre = paciente.nombre_completo
        nombre_normalizado = _normalizar_texto(nombre)
        tokens_nombre = nombre_normalizado.split()
        if all(
            any(token_nombre.startswith(token_q) for token_nombre in tokens_nombre)
            for token_q in tokens_busqueda
        ):
            candidatos.append((paciente, nombre, nombre_normalizado))

    candidatos.sort(key=lambda c: c[2])
    candidatos = candidatos[:limite]

    unidades = {u.clues: u.nombre_de_la_unidad for u in db.query(UnidadMedica).all()}
    totales_por_paciente: dict[int, int] = {}
    if candidatos:
        ids_pacientes = [paciente.id_paciente for paciente, _, _ in candidatos]
        totales_por_paciente = dict(
            db.query(Registro.id_paciente, func.count(Registro.id_registro))
            .filter(Registro.id_paciente.in_(ids_pacientes))
            .group_by(Registro.id_paciente)
            .all()
        )

    resultados = [
        BusquedaNombreItem(
            id_paciente=paciente.id_paciente,
            nombre_completo=nombre,
            fecha_nacimiento=paciente.fecha_nacimiento,
            curp_paciente=paciente.curp_paciente,
            clues_unidad_adscripcion=paciente.clues_unidad_adscripcion,
            nombre_unidad=unidades.get(paciente.clues_unidad_adscripcion),
            total_registros=totales_por_paciente.get(paciente.id_paciente, 0),
        )
        for paciente, nombre, _ in candidatos
    ]

    return BusquedaNombreResponse(resultados=resultados)


@router.get(
    "/{identificador}",
    response_model=PacienteResponse,
    summary="Detalle completo de un paciente.",
)
def obtener_paciente(
    identificador: str,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    marcar_registros_vencidos(db)
    paciente = _obtener_paciente_por_identificador(identificador, db)
    _verificar_acceso_paciente(paciente, current_user, db)

    # Si se requiere ubicar pacientes de otras unidades (p. ej. para
    # continuidad de tratamiento), usar /pacientes/buscar o /pacientes?q=,
    # que exponen solo identidad y conteo de registros, sin diagnóstico,
    # expediente ni historial.

    tiene = _tiene_prescripcion_activa(paciente.id_paciente, db)
    meds, adherencias = _get_medicamentos_y_adherencia(paciente.id_paciente, db)
    diags = _get_diagnosticos_activos(paciente.id_paciente, db)
    respuesta = _paciente_to_response(paciente, tiene_prescripcion_activa=tiene, medicamentos_activos=meds, diagnosticos_activos=diags, db=db)
    respuesta.adherencia_medicamentos = adherencias
    respuesta.dias_adherencia = _calcular_adherencia(paciente.id_paciente, db)
    return respuesta


@router.patch(
    "/{identificador}",
    response_model=PacienteResponse,
    summary="Actualización parcial de datos del paciente.",
)
def actualizar_paciente(
    identificador: str,
    payload: PacienteUpdate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    paciente = _obtener_paciente_por_identificador(identificador, db)

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
        if payload.clues_unidad_adscripcion:
            # También el destino: no puede transferir el paciente a otro estado.
            _verificar_clues_en_ambito(payload.clues_unidad_adscripcion.strip().upper(), current_user, db)

    clues_anterior = paciente.clues_unidad_adscripcion

    datos = payload.model_dump(exclude_none=True)
    if "nombre_completo" in datos:
        paciente.nombre_completo = datos.pop("nombre_completo")
    if "diagnostico_actual" in datos:
        val = datos.pop("diagnostico_actual")
        paciente.diagnostico_actual = val or None
    if not ESTATUS_EVOLUCION_HABILITADO:
        # Módulo oculto temporalmente: se descarta sin error ni auditoría.
        datos.pop("estatus_evolucion", None)
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
    respuesta = _paciente_to_response(paciente, tiene_prescripcion_activa=tiene, medicamentos_activos=meds, diagnosticos_activos=diags, db=db)
    respuesta.adherencia_medicamentos = adherencias
    respuesta.dias_adherencia = _calcular_adherencia(paciente.id_paciente, db)
    return respuesta


@router.delete(
    "/{identificador}",
    response_model=PacienteResponse,
    summary="Soft Delete: da de baja al paciente.",
)
def dar_baja_paciente(
    identificador: str,
    payload: BajaPacienteRequest,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    paciente = _obtener_paciente_por_identificador(identificador, db)
    _verificar_acceso_paciente(paciente, current_user, db)

    if not paciente.es_activo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El paciente ya se encuentra dado de baja.",
        )

    paciente.es_activo = False
    paciente.motivo_baja = _serializar_motivo_baja(payload.motivo_baja)
    paciente.id_usuario_registro = current_user.id_usuario

    db.query(Registro).filter(
        Registro.id_paciente == paciente.id_paciente,
        Registro.es_activo == True,
    ).update({"es_activo": False})

    db.commit()
    db.refresh(paciente)

    respuesta = _paciente_to_response(paciente, tiene_prescripcion_activa=False, db=db)
    respuesta.dias_adherencia = None
    return respuesta


@router.get(
    "/{identificador}/expedientes",
    response_model=list[ExpedienteResponse],
    summary="Lista los expedientes del paciente en cada unidad donde ha sido atendido.",
)
def listar_expedientes_paciente(
    identificador: str,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    paciente = _obtener_paciente_por_identificador(identificador, db)
    _verificar_acceso_paciente(paciente, current_user, db)
    expedientes = db.query(ExpedientePaciente).filter(
        ExpedientePaciente.id_paciente == paciente.id_paciente
    ).all()
    return [ExpedienteResponse.model_validate(e) for e in expedientes]


@router.post(
    "/{identificador}/expedientes",
    response_model=ExpedienteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crea o actualiza el expediente del paciente en una unidad específica (upsert).",
)
def upsert_expediente_paciente(
    identificador: str,
    payload: ExpedienteCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    paciente = _obtener_paciente_por_identificador(identificador, db)
    _verificar_clues_en_ambito(payload.clues, current_user, db)

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


# ---------------------------------------------------------------------------
# Reacciones Adversas
#
# Módulo oculto temporalmente: REACCIONES_ADVERSAS_HABILITADO = False en
# app/config.py desactiva por completo estos endpoints. Para reactivar,
# cambiar el flag a True. El modelo, la tabla y los datos ya capturados no
# se ven afectados.
# ---------------------------------------------------------------------------

if REACCIONES_ADVERSAS_HABILITADO:

    def _reaccion_to_response(r: ReaccionAdversa) -> ReaccionAdversaResponse:
        return ReaccionAdversaResponse(
            id_reaccion=r.id_reaccion,
            clave_cnis=r.clave_cnis,
            nombre_medicamento=r.medicamento.descripcion if r.medicamento else r.clave_cnis,
            comentario=r.comentario,
            nombre_usuario_registro=r.usuario_registro.nombre_usuario if r.usuario_registro else None,
            email_usuario_registro=r.usuario_registro.email if r.usuario_registro else None,
            fecha_registro=r.fecha_registro,
        )

    @router.get(
        "/{identificador}/reacciones-adversas",
        response_model=list[ReaccionAdversaResponse],
        summary="Lista las reacciones adversas registradas para un paciente.",
    )
    def listar_reacciones_adversas(
        identificador: str,
        db: Session = Depends(get_db),
        current_user: UsuarioActivo = Depends(require_password_cambiado),
    ):
        paciente = _obtener_paciente_por_identificador(identificador, db)
        _verificar_acceso_paciente(paciente, current_user, db)
        reacciones = (
            db.query(ReaccionAdversa)
            .filter(ReaccionAdversa.id_paciente == paciente.id_paciente)
            .options(joinedload(ReaccionAdversa.medicamento), joinedload(ReaccionAdversa.usuario_registro))
            .order_by(ReaccionAdversa.fecha_registro.desc())
            .all()
        )
        return [_reaccion_to_response(r) for r in reacciones]

    @router.post(
        "/{identificador}/reacciones-adversas",
        response_model=ReaccionAdversaResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Registra una reacción adversa a un medicamento para un paciente.",
    )
    def agregar_reaccion_adversa(
        identificador: str,
        payload: ReaccionAdversaCreate,
        db: Session = Depends(get_db),
        current_user: UsuarioActivo = Depends(require_password_cambiado),
    ):
        paciente = _obtener_paciente_por_identificador(identificador, db)
        _verificar_acceso_paciente(paciente, current_user, db)

        if not db.query(CatMedicamento).filter(CatMedicamento.clave_cnis == payload.clave_cnis).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicamento no encontrado.")

        reaccion = ReaccionAdversa(
            id_paciente=paciente.id_paciente,
            clave_cnis=payload.clave_cnis,
            comentario=payload.comentario,
            id_usuario_registro=current_user.id_usuario,
        )
        db.add(reaccion)
        db.commit()
        db.refresh(reaccion)
        return _reaccion_to_response(reaccion)


@router.get(
    "/{identificador}/registros",
    response_model=RegistroListResponse,
    summary="Todas las prescripciones de un paciente, sin filtro de unidad.",
)
def listar_registros_de_paciente(
    identificador: str,
    solo_activos: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: UsuarioActivo = Depends(require_password_cambiado),
):
    marcar_registros_vencidos(db)
    paciente = _obtener_paciente_por_identificador(identificador, db)
    _verificar_acceso_paciente(paciente, current_user, db)

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
