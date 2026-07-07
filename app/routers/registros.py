"""Router de registros (prescripciones): CRUD completo con posología y reemplazos."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth import UsuarioActivo, apply_rbac_filter, require_password_cambiado
from app.crypto import hash_sha256
from app.database import get_db
from app.models import (
    CatMedicamento,
    ExpedientePaciente,
    Medico,
    Paciente,
    Registro,
    UnidadMedica,
)
from app.schemas import (
    RegistroCompletoCreate,
    RegistroCompletoResponse,
    RegistroCreate,
    RegistroListResponse,
    RegistroResponse,
    RegistroUpdate,
    ValidarContinuidadRequest,
)
from app.services.pacientes import _verificar_acceso_paciente, _verificar_acceso_registro
from app.services.registros import _aplicar_posologia, _registro_to_response, marcar_registros_vencidos

router = APIRouter(prefix="/registros", tags=["Registros"])


@router.get(
    "",
    response_model=RegistroListResponse,
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


@router.post(
    "",
    response_model=RegistroResponse,
    status_code=status.HTTP_201_CREATED,
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

    paciente = db.query(Paciente).filter(Paciente.id_paciente == payload.id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")
    _verificar_acceso_paciente(paciente, current_user, db)
    if not paciente.es_activo:
        paciente.es_activo = True
        paciente.motivo_baja = None

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

    prescripcion_activa = db.query(Registro).filter(
        Registro.id_paciente == payload.id_paciente,
        Registro.clave_cnis == payload.clave_cnis,
        Registro.es_activo == True,
    ).first()
    if prescripcion_activa:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El paciente ya tiene una prescripción activa de este medicamento. Edita la existente o anúlala antes de crear una nueva.",
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
        confirmado_mediante=payload.confirmado_mediante,
        tratamiento_amparo=payload.tratamiento_amparo,
        queja_derechos_humanos=payload.queja_derechos_humanos,
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


@router.post(
    "/completo",
    response_model=RegistroCompletoResponse,
    status_code=status.HTTP_201_CREATED,
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

    # 1. Identificar al paciente: por id_paciente, por CURP, o crear uno nuevo sin CURP
    def _crear_paciente_nuevo(curp_hash: str | None, curp_cifrada: bytes | None) -> Paciente:
        if not payload.nombre_completo:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="nombre_completo es requerido para registrar un paciente nuevo.",
            )
        clues_paciente = (payload.clues_unidad_adscripcion or payload.clues).strip().upper()
        if current_user.es_responsable_unidad:
            if clues_paciente != current_user.clues_unidad_asignada:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo puede registrar pacientes en su propia unidad médica.",
                )
        nuevo_paciente = Paciente(
            curp_hash=curp_hash,
            curp_paciente=curp_cifrada,
            nombre_completo=payload.nombre_completo,
            fecha_nacimiento=payload.fecha_nacimiento,
            clues_unidad_adscripcion=clues_paciente,
            es_activo=True,
            id_usuario_registro=current_user.id_usuario,
        )
        db.add(nuevo_paciente)
        db.flush()  # Obtiene id_paciente sin hacer commit aún
        return nuevo_paciente

    if payload.id_paciente is not None and payload.curp_paciente:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se puede proporcionar id_paciente y curp_paciente al mismo tiempo.",
        )

    paciente_creado = False

    if payload.id_paciente is not None:
        paciente = db.query(Paciente).filter(Paciente.id_paciente == payload.id_paciente).first()
        if not paciente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")
        _verificar_acceso_paciente(paciente, current_user, db)
        if not paciente.es_activo:
            paciente.es_activo = True
            paciente.motivo_baja = None

    elif payload.curp_paciente:
        curp_hash = hash_sha256(payload.curp_paciente)
        paciente = db.query(Paciente).filter(Paciente.curp_hash == curp_hash).first()
        if not paciente:
            paciente = _crear_paciente_nuevo(curp_hash, payload.curp_paciente)
            paciente_creado = True
        else:
            _verificar_acceso_paciente(paciente, current_user, db)
            if not paciente.es_activo:
                paciente.es_activo = True
                paciente.motivo_baja = None

    else:
        paciente = _crear_paciente_nuevo(None, None)
        paciente_creado = True

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
    if not paciente_creado:
        prescripcion_activa = db.query(Registro).filter(
            Registro.id_paciente == paciente.id_paciente,
            Registro.clave_cnis == payload.clave_cnis,
            Registro.es_activo == True,
        ).first()
        if prescripcion_activa:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El paciente ya tiene una prescripción activa de este medicamento. Edita la existente o anúlala antes de crear una nueva.",
            )

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
        confirmado_mediante=payload.confirmado_mediante,
        tratamiento_amparo=payload.tratamiento_amparo,
        queja_derechos_humanos=payload.queja_derechos_humanos,
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
    base_dict = _registro_to_response(registro).model_dump()
    base_dict["paciente_creado"] = paciente_creado
    return RegistroCompletoResponse(**base_dict)


@router.get(
    "/{id_registro}",
    response_model=RegistroResponse,
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


@router.patch(
    "/{id_registro}",
    response_model=RegistroResponse,
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

    if CAMPOS_POSOLOGIA & set(campos_actualizados):
        unidad_med = registro.medicamento.unidad if registro.medicamento else None
        unidad_dm = registro.medicamento.unidad_de_medida if registro.medicamento else None
        _aplicar_posologia(registro, unidad_med, unidad_dm)

    registro.id_usuario_registro = current_user.id_usuario
    db.commit()
    db.refresh(registro)
    return _registro_to_response(registro)


@router.delete(
    "/{id_registro}",
    response_model=RegistroResponse,
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


@router.patch(
    "/{id_registro}/validar-continuidad",
    response_model=RegistroResponse,
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


@router.post(
    "/{id_registro}/reemplazar",
    response_model=RegistroResponse,
    status_code=status.HTTP_201_CREATED,
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
        "confirmado_mediante": original.confirmado_mediante,
        "tratamiento_amparo": original.tratamiento_amparo,
        "queja_derechos_humanos": original.queja_derechos_humanos,
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

    for campo, valor in payload.model_dump(exclude_none=True).items():
        if campo != "es_activo":  # no permitir cambiar el estado directamente
            campos_nuevo[campo] = valor

    nuevo = Registro(**campos_nuevo)

    unidad_med = original.medicamento.unidad if original.medicamento else None
    unidad_dm = original.medicamento.unidad_de_medida if original.medicamento else None
    _aplicar_posologia(nuevo, unidad_med, unidad_dm)

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
