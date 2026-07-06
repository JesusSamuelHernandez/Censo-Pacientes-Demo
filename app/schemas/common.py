"""Tipos anotados y constantes compartidas por los schemas."""
import re
from typing import Annotated

from pydantic import Field

from app.models import Rol

_CURP_REGEX = re.compile(
    r"^[A-Z]{4}\d{6}[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$"
)

CurpStr = Annotated[
    str,
    Field(
        min_length=18,
        max_length=18,
        description="CURP del paciente (18 caracteres, formato oficial SEP/RENAPO).",
        examples=["LOOA890101HDFPRS09"],
    ),
]

CluesStr = Annotated[
    str,
    Field(
        min_length=1,
        max_length=20,
        pattern=r"^[A-Z0-9]+$",
        description="Clave Unica de Establecimiento de Salud (CLUES).",
        examples=["DFSSA004266"],
    ),
]

ClaveCnisStr = Annotated[
    str,
    Field(
        min_length=1,
        max_length=50,
        description="Clave CNIS del medicamento (ej. '010.000.4155.00').",
        examples=["010.000.4155.00"],
    ),
]

RolStr = Annotated[
    str,
    Field(
        description=f"Rol del usuario. Valores validos: {sorted(Rol.TODOS)}",
        examples=[Rol.RESPONSABLE_UNIDAD],
    ),
]

ESTATUS_EVOLUCION_OPTIONS = ["Inicia tx", "Tx fase intermedia", "Recaída", "Curación"]

MOTIVO_BAJA_OPTIONS = [
    "Efecto adverso",
    "Defunción",
    "Cambio de tratamiento",
    "Atención en seguridad social o medios privados",
]

CONFIRMADO_MEDIANTE_OPTIONS = [
    "Médico tratante (Clínico)",
    "Estudios de laboratorio especializados",
    "Confirmación por centro de referencia o especialista",
]