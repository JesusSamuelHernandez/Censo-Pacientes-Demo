"""Lógica de negocio para pacientes: presentación, helpers de consulta y verificación RBAC."""
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import exists
from sqlalchemy.orm import Session

from app.audit import Accion, Resultado, registrar_evento
from app.auth import UsuarioActivo
from app.config import REACCIONES_ADVERSAS_HABILITADO
from app.crypto import hash_identificador
from app.models import (
    CatDiagnostico,
    CatMedicamento,
    Paciente,
    ReaccionAdversa,
    Registro,
    UnidadMedica,
)
from app.schemas import PacienteResponse
from app.services.utils import _deserializar_motivo_baja


def _paciente_to_response(
    p: Paciente,
    tiene_prescripcion_activa: bool = False,
    medicamentos_activos: list[str] | None = None,
    diagnosticos_activos: list[str] | None = None,
    db: Session | None = None,
) -> PacienteResponse:
    """Construye el schema de respuesta (campos cifrados se descifran vía TypeDecorator)."""
    tiene_reaccion = (
        db.query(ReaccionAdversa).filter(
            ReaccionAdversa.id_paciente == p.id_paciente
        ).count() > 0
        if REACCIONES_ADVERSAS_HABILITADO and db is not None
        else False
    )
    return PacienteResponse(
        id_paciente=p.id_paciente,
        curp_paciente=p.curp_paciente,
        nombre_completo=p.nombre_completo,
        diagnostico_actual=p.diagnostico_actual,
        clues_unidad_adscripcion=p.clues_unidad_adscripcion,
        fecha_nacimiento=p.fecha_nacimiento,
        es_activo=p.es_activo,
        motivo_baja=_deserializar_motivo_baja(p.motivo_baja),
        estatus_evolucion=p.estatus_evolucion,
        fecha_registro=p.fecha_registro,
        id_usuario_registro=p.id_usuario_registro,
        dias_adherencia=None,
        tiene_prescripcion_activa=tiene_prescripcion_activa,
        medicamentos_activos=medicamentos_activos or [],
        diagnosticos_activos=diagnosticos_activos or [],
        tiene_reaccion_adversa=tiene_reaccion,
    )


def _get_medicamentos_activos(id_paciente: int, db: Session) -> list[str]:
    """Retorna las descripciones de medicamentos de prescripciones activas del paciente."""
    return _get_medicamentos_y_adherencia(id_paciente, db)[0]


def _get_medicamentos_y_adherencia(id_paciente: int, db: Session) -> tuple[list[str], list[int | None]]:
    """
    Retorna (descripciones, dias_adherencia) de medicamentos de prescripciones activas
    del paciente, alineados posicionalmente. Si hay varios registros activos para el
    mismo medicamento, se usa el más reciente (fecha_registro_sistema).
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
    """Lanza 403 si el usuario no tiene acceso RBAC al paciente indicado."""
    if usuario.es_super_admin:
        return
    if usuario.es_responsable_unidad:
        if paciente.clues_unidad_adscripcion != usuario.clues_unidad_asignada:
            detalle = "No tiene acceso a pacientes de otra unidad médica."
            registrar_evento(
                db, accion=Accion.ACCESO_DENEGADO, resultado=Resultado.DENEGADO,
                id_usuario=usuario.id_usuario, objeto_tipo="paciente",
                objeto_id=paciente.id_paciente, detalle=detalle,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detalle)
        return
    if usuario.es_admin_estatal:
        unidad = db.query(UnidadMedica).filter(
            UnidadMedica.clues == paciente.clues_unidad_adscripcion
        ).first()
        if not unidad or unidad.id_entidad != usuario.id_entidad:
            detalle = "No tiene acceso a pacientes de otro estado."
            registrar_evento(
                db, accion=Accion.ACCESO_DENEGADO, resultado=Resultado.DENEGADO,
                id_usuario=usuario.id_usuario, objeto_tipo="paciente",
                objeto_id=paciente.id_paciente, detalle=detalle,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detalle)


def _verificar_acceso_registro(
    registro: Registro,
    usuario: UsuarioActivo,
    db: Session,
) -> None:
    """Lanza 403 si el usuario no tiene acceso RBAC al registro indicado."""
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
            detalle = "No tiene acceso a registros de pacientes de otra unidad médica."
            registrar_evento(
                db, accion=Accion.ACCESO_DENEGADO, resultado=Resultado.DENEGADO,
                id_usuario=usuario.id_usuario, objeto_tipo="registro",
                objeto_id=registro.id_registro, detalle=detalle,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detalle)
        return
    if usuario.es_admin_estatal:
        unidad = db.query(UnidadMedica).filter(
            UnidadMedica.clues == registro.clues
        ).first()
        if not unidad or unidad.id_entidad != usuario.id_entidad:
            detalle = "No tiene acceso a registros de otro estado."
            registrar_evento(
                db, accion=Accion.ACCESO_DENEGADO, resultado=Resultado.DENEGADO,
                id_usuario=usuario.id_usuario, objeto_tipo="registro",
                objeto_id=registro.id_registro, detalle=detalle,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detalle)


def _obtener_paciente_por_identificador(identificador: str, db: Session) -> Paciente:
    """Resuelve un paciente a partir del segmento {identificador} de la URL.

    El identificador puede ser el id_paciente numérico (preferido, no expone CURP
    en logs ni historial) o una CURP (compatibilidad; siempre empieza con 4 letras).
    """
    if identificador.isdigit():
        paciente = db.query(Paciente).filter(Paciente.id_paciente == int(identificador)).first()
    else:
        paciente = db.query(Paciente).filter(Paciente.curp_hash == hash_identificador(identificador)).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")
    return paciente
