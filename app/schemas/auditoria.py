"""Schemas de lectura del audit trail de seguridad (SAST-13)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventoSeguridadResponse(BaseModel):
    id_evento: int
    id_usuario: int | None
    accion: str
    resultado: str
    objeto_tipo: str | None
    objeto_id: str | None
    ip_origen: str | None
    detalle: str | None
    fecha: datetime

    model_config = ConfigDict(from_attributes=True)


class EventoSeguridadListResponse(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    resultados: list[EventoSeguridadResponse]
