"""Helpers de presentación y verificación RBAC para el dominio Médico."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.audit import Accion, Resultado, registrar_evento
from app.auth import UsuarioActivo
from app.models import Medico, UnidadMedica
from app.schemas import MedicoResponse


def _obtener_medico_o_404(id_medico: int, db: Session) -> Medico:
    """Busca un médico por id o lanza 404."""
    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médico no encontrado.")
    return medico


def _verificar_acceso_medico(
    medico: Medico,
    usuario: UsuarioActivo,
    db: Session,
) -> None:
    """Lanza 403 si el usuario no tiene acceso RBAC al médico indicado."""
    if usuario.es_super_admin:
        return
    if usuario.es_responsable_unidad:
        if medico.clues_adscripcion != usuario.clues_unidad_asignada:
            detalle = "No tiene acceso a médicos de otra unidad médica."
            registrar_evento(
                db, accion=Accion.ACCESO_DENEGADO, resultado=Resultado.DENEGADO,
                id_usuario=usuario.id_usuario, objeto_tipo="medico",
                objeto_id=medico.id_medico, detalle=detalle,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detalle)
        return
    if usuario.es_admin_estatal:
        unidad = db.query(UnidadMedica).filter(
            UnidadMedica.clues == medico.clues_adscripcion
        ).first()
        if not unidad or unidad.id_entidad != usuario.id_entidad:
            detalle = "No tiene acceso a médicos de otro estado."
            registrar_evento(
                db, accion=Accion.ACCESO_DENEGADO, resultado=Resultado.DENEGADO,
                id_usuario=usuario.id_usuario, objeto_tipo="medico",
                objeto_id=medico.id_medico, detalle=detalle,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detalle)


def _medico_to_response(m: Medico) -> MedicoResponse:
    """Construye el schema de respuesta (campos cifrados se descifran vía TypeDecorator)."""
    return MedicoResponse(
        id_medico=m.id_medico,
        nombre_medico=m.nombre_medico,
        cedula=m.cedula,
        curp=m.curp,
        id_puesto=m.id_puesto,
        denominacion_puesto=m.puesto.denominacion_puesto if m.puesto else None,
        email=m.email,
        clues_adscripcion=m.clues_adscripcion,
        es_activo=m.es_activo,
    )
