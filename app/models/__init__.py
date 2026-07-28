"""Modelos ORM exportados por dominio.

Este paquete mantiene compatible `from app.models import X` y carga todos los
modelos para que `Base.metadata` incluya la metadata completa de la aplicacion.
"""
from app.database import Base
from app.models.auditoria import EventoSeguridad
from app.models.roles import Rol
from app.models.catalogos import (
    CatDiagnostico,
    CatMedicamento,
    CatPuesto,
    UnidadMedica,
    UnidadMedicamento,
)
from app.models.usuarios import Usuario, UsuarioPreautorizado
from app.models.pacientes import (
    ExpedientePaciente,
    NotificacionTransferencia,
    Paciente,
    ReaccionAdversa,
)
from app.models.medicos import Medico
from app.models.registros import Registro

__all__ = [
    "Base",
    "CatDiagnostico",
    "CatMedicamento",
    "CatPuesto",
    "EventoSeguridad",
    "ExpedientePaciente",
    "Medico",
    "NotificacionTransferencia",
    "Paciente",
    "ReaccionAdversa",
    "Registro",
    "Rol",
    "UnidadMedica",
    "UnidadMedicamento",
    "Usuario",
    "UsuarioPreautorizado",
]