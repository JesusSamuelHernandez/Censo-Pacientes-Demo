"""Helpers de presentación para el dominio Médico."""
from app.models import Medico
from app.schemas import MedicoResponse


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
