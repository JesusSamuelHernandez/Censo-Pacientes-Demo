"""Router de reportes: resumen detallado, estatal y RTM."""
from collections import defaultdict
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.audit import Accion, registrar_evento
from app.auth import (
    UsuarioActivo,
    apply_rbac_filter,
    require_admin_estatal_o_superior,
    require_password_cambiado,
    require_super_admin,
)

from app.database import get_db
from app.models import CatMedicamento, Paciente, Registro, UnidadMedica
from app.schemas import RtmFilaResponse, RtmMesItem, RtmResponse

router = APIRouter(prefix="/reportes", tags=["Reportes"])

_MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


@router.get(
    "/resumen-detallado",
    summary="Datos crudos con filtros de fecha. Para generación de Excel/PDF.",
)
def reporte_resumen_detallado(
    fecha_inicio: date | None = Query(None),
    fecha_fin: date | None = Query(None),
    solo_activos: bool = Query(True),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(500, ge=1, le=2000),
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
        query = query.filter(Registro.fecha_inicio_tratamiento >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Registro.fecha_inicio_tratamiento <= fecha_fin)

    total_registros = query.count()
    registros = (
        query.order_by(Registro.id_registro.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    registrar_evento(
        db, accion=Accion.EXPORTACION, id_usuario=current_user.id_usuario,
        objeto_tipo="resumen_detallado", objeto_id=None,
        detalle=f"{len(registros)} de {total_registros} registros, pagina {pagina}",
    )

    return {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "total_registros": total_registros,
        "registros_devueltos": len(registros),
        "pagina": pagina,
        "por_pagina": por_pagina,
        "hay_mas": pagina * por_pagina < total_registros,
        "filtros_aplicados": {
            "fecha_inicio": str(fecha_inicio) if fecha_inicio else None,
            "fecha_fin": str(fecha_fin) if fecha_fin else None,
            "solo_activos": solo_activos,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "rbac_clues": filtro.valor_clues,
            "rbac_entidad": filtro.valor_entidad,
        },
        "datos": [
            {
                "id_registro": r.id_registro,
                "id_paciente": r.id_paciente,
                "curp_paciente": r.paciente.curp_paciente if r.paciente else None,
                "nombre_paciente": r.paciente.nombre_completo if r.paciente else None,
                "diagnostico": r.diagnostico.nombre if r.diagnostico else None,
                "estatus_diagnostico": r.estatus_diagnostico,
                "confirmado_por": r.confirmado_por,
                "confirmado_mediante": r.confirmado_mediante,
                "caso_relacionado_con": (
                    "Tratamiento por amparo" if r.tratamiento_amparo
                    else "Caso relacionado con queja de derechos humanos" if r.queja_derechos_humanos
                    else "No aplica"
                ),
                "clues_unidad": r.clues,
                "medico": r.medico.nombre_medico if r.medico else None,
                "cedula_medico": r.medico.cedula if r.medico else None,
                "dias_adherencia": (
                    (date.today() - r.fecha_inicio_tratamiento).days
                    if r.fecha_inicio_tratamiento else None
                ),
                "clave_cnis": r.clave_cnis,
                "descripcion_medicamento": r.medicamento.descripcion if r.medicamento else None,
                "prescripcion": r.prescripcion,
                "peso": float(r.peso) if r.peso is not None else None,
                "talla": float(r.talla) if r.talla is not None else None,
                "fecha_inicio_tratamiento": (
                    r.fecha_inicio_tratamiento.isoformat()
                    if r.fecha_inicio_tratamiento else None
                ),
                "fecha_fin_tratamiento": (
                    r.fecha_fin_tratamiento.isoformat()
                    if r.fecha_fin_tratamiento else None
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


@router.get(
    "/estatal",
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


@router.get(
    "/rtm",
    response_model=RtmResponse,
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
