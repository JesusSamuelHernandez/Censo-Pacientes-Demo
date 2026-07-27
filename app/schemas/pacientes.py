"""Schemas de pacientes, busquedas, expedientes y reacciones adversas."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import (
    _CURP_REGEX,
    CluesStr,
    CurpStr,
    ESTATUS_EVOLUCION_OPTIONS,
    MOTIVO_BAJA_OPTIONS,
)


class PacienteBase(BaseModel):
    nombre_completo: str = Field(..., min_length=2, max_length=255)
    diagnostico_actual: str | None = Field(None, max_length=5000)
    clues_unidad_adscripcion: CluesStr
    fecha_nacimiento: date | None = Field(None, description="Fecha de nacimiento del paciente.")

    @field_validator("clues_unidad_adscripcion", mode="before")
    @classmethod
    def normalizar_clues(cls, v: str) -> str:
        return v.strip().upper()


class PacienteCreate(PacienteBase):
    curp_paciente: CurpStr

    @field_validator("curp_paciente", mode="before")
    @classmethod
    def normalizar_y_validar_curp(cls, v: str) -> str:
        curp = v.strip().upper()
        if not _CURP_REGEX.match(curp):
            raise ValueError(
                "CURP invalida. Debe tener 18 caracteres con el formato oficial "
                "(ej. LOOA890101HDFPRS09)."
            )
        return curp


class PacienteUpdate(BaseModel):
    nombre_completo: str | None = Field(None, min_length=2, max_length=255)
    diagnostico_actual: str | None = Field(None, max_length=5000)
    clues_unidad_adscripcion: str | None = Field(None, max_length=20)
    fecha_nacimiento: date | None = None
    es_activo: bool | None = Field(
        None,
        description="False = dar de baja al paciente (Soft Delete).",
    )
    estatus_evolucion: str | None = Field(
        None,
        description=f"Estatus de evolucion del paciente. Valores validos: {ESTATUS_EVOLUCION_OPTIONS}",
    )

    @field_validator("estatus_evolucion")
    @classmethod
    def validar_estatus_evolucion(cls, v: str) -> str:
        if v not in ESTATUS_EVOLUCION_OPTIONS:
            raise ValueError(f"estatus_evolucion debe ser uno de: {ESTATUS_EVOLUCION_OPTIONS}")
        return v


class BajaPacienteRequest(BaseModel):
    motivo_baja: list[str] = Field(
        ..., min_length=1, description=f"Uno o mas motivos de la baja. Valores validos: {MOTIVO_BAJA_OPTIONS}"
    )

    @field_validator("motivo_baja")
    @classmethod
    def validar_motivo_baja(cls, v: list[str]) -> list[str]:
        invalidos = [m for m in v if m not in MOTIVO_BAJA_OPTIONS]
        if invalidos:
            raise ValueError(f"motivo_baja contiene valores invalidos: {invalidos}. Validos: {MOTIVO_BAJA_OPTIONS}")
        return v


class PacienteResponse(BaseModel):
    id_paciente: int
    curp_paciente: str | None = None
    nombre_completo: str
    diagnostico_actual: str | None
    clues_unidad_adscripcion: str
    fecha_nacimiento: date | None = None
    es_activo: bool
    motivo_baja: list[str] | None = None
    estatus_evolucion: str
    fecha_registro: datetime
    id_usuario_registro: int | None
    dias_adherencia: int | None = Field(
        None,
        description="Dias desde fecha_inicio_tratamiento del registro activo mas reciente.",
    )
    tiene_prescripcion_activa: bool = Field(
        False,
        description="True si el paciente tiene al menos un registro con es_activo=True.",
    )
    medicamentos_activos: list[str] = Field(
        default_factory=list,
        description="Descripciones de los medicamentos de prescripciones activas.",
    )
    adherencia_medicamentos: list[int | None] = Field(
        default_factory=list,
        description="Dias de adherencia por medicamento activo, alineado posicionalmente con medicamentos_activos.",
    )
    diagnosticos_activos: list[str] = Field(
        default_factory=list,
        description="Nombres de diagnosticos de prescripciones activas.",
    )
    tiene_reaccion_adversa: bool = Field(
        False,
        description="True si el paciente tiene al menos una reaccion adversa registrada.",
    )

    model_config = ConfigDict(from_attributes=True)


class PacienteListResponse(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    resultados: list[PacienteResponse]


class ExpedienteCreate(BaseModel):
    clues: CluesStr
    numero_expediente: str = Field(..., min_length=1, max_length=100)

    @field_validator("clues", mode="before")
    @classmethod
    def normalizar_clues(cls, v: str) -> str:
        return v.strip().upper()


class ExpedienteUpdate(BaseModel):
    numero_expediente: str = Field(..., min_length=1, max_length=100)


class ExpedienteResponse(BaseModel):
    id_paciente: int
    clues: str
    numero_expediente: str

    model_config = ConfigDict(from_attributes=True)


class BusquedaCurpRequest(BaseModel):
    curp: CurpStr

    @field_validator("curp", mode="before")
    @classmethod
    def normalizar_y_validar_curp(cls, v: str) -> str:
        curp = v.strip().upper()
        if not _CURP_REGEX.match(curp):
            raise ValueError(
                "CURP invalida. Debe tener 18 caracteres con el formato oficial "
                "(ej. LOOA890101HDFPRS09)."
            )
        return curp


class BusquedaCurpResponse(BaseModel):
    existe: bool
    id_paciente: int | None = None
    nombre_completo: str | None = None
    fecha_nacimiento: date | None = None
    clues_unidad_adscripcion: str | None = None
    nombre_unidad: str | None = None
    total_registros: int | None = None


class BusquedaNombreItem(BaseModel):
    id_paciente: int
    nombre_completo: str
    fecha_nacimiento: date | None = None
    curp_paciente: str | None = None
    clues_unidad_adscripcion: str
    nombre_unidad: str | None = None
    total_registros: int


class BusquedaNombreResponse(BaseModel):
    resultados: list[BusquedaNombreItem]


class ReaccionAdversaCreate(BaseModel):
    clave_cnis: str
    comentario: str = Field(..., min_length=1, max_length=2000)


class ReaccionAdversaResponse(BaseModel):
    id_reaccion: int
    clave_cnis: str
    nombre_medicamento: str
    comentario: str
    nombre_usuario_registro: str | None = None
    email_usuario_registro: str | None = None
    fecha_registro: datetime

    model_config = ConfigDict(from_attributes=True)