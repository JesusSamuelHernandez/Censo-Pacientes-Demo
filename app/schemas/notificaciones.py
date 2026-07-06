"""Schemas de notificaciones operativas y transferencias."""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class NotificacionResponse(BaseModel):
    id_registro: int
    id_paciente: int
    nombre_paciente: str
    clave_cnis: str
    descripcion_medicamento: str | None
    clues: str
    fecha_fin_tratamiento: date
    fecha_limite: date
    dias_restantes: int
    es_activo: bool
    fecha_inicio_tratamiento: date | None = None
    dosis_administrada: str | None = None
    peso: Decimal | None = None
    talla: Decimal | None = None
    prescripcion: str | None = None
    duracion: int | None = None
    unidad_tiempo: str | None = None


class NotificacionListResponse(BaseModel):
    total: int
    resultados: list[NotificacionResponse]


class NotificacionTransferenciaResponse(BaseModel):
    id: int
    id_paciente: int
    nombre_paciente: str
    curp_paciente: str | None = None
    clues_unidad_origen: str
    nombre_unidad_origen: str | None
    clues_unidad_destino: str
    nombre_unidad_destino: str | None
    nombre_usuario_traslado: str | None
    fecha_traslado: datetime


class NotificacionTransferenciaListResponse(BaseModel):
    total: int
    resultados: list[NotificacionTransferenciaResponse]