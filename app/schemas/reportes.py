"""Schemas de reportes."""
from pydantic import BaseModel


class RtmMesItem(BaseModel):
    anio: int
    mes: int
    etiqueta: str
    cantidad: float


class RtmFilaResponse(BaseModel):
    clave_cnis: str
    descripcion: str
    grupo: str | None
    unidad_de_medida: str | None
    meses: list[RtmMesItem]


class RtmResponse(BaseModel):
    clues: str
    nombre_unidad: str | None
    generado_en: str
    cabeceras: list[str]
    filas: list[RtmFilaResponse]