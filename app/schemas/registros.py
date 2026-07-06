"""Schemas de registros de prescripcion."""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.catalogos import DiagnosticoResponse, MedicamentoResponse
from app.schemas.common import CONFIRMADO_MEDIANTE_OPTIONS, ClaveCnisStr, CluesStr, CurpStr
from app.schemas.medicos import MedicoResponse


class RegistroBase(BaseModel):
    id_medico: int = Field(..., description="ID del medico que prescribe.")
    id_paciente: int = Field(..., description="ID interno del paciente (PK de la tabla pacientes).")
    clave_cnis: ClaveCnisStr
    clues: CluesStr
    id_diagnostico: int | None = Field(None, description="ID del diagnostico del catalogo.")
    fecha_inicio_tratamiento: date | None = Field(
        None, description="Inicio del esquema especifico de esta prescripcion."
    )
    fecha_primera_administracion: date | None = Field(
        None, description="Fecha real de la primera dosis."
    )
    fecha_fin_tratamiento: date | None = Field(
        None, description="Fecha en que termina la prescripcion. Se suma 1 mes para la ventana de continuidad."
    )
    dosis_administrada: str | None = Field(
        None,
        max_length=100,
        description="Ej. '200 mg', '1 ampolleta'.",
    )
    peso: Decimal | None = Field(None, description="Peso del paciente en kg (ej. 75.50).")
    talla: Decimal | None = Field(None, description="Talla del paciente en cm (ej. 165.00).")
    estatus_diagnostico: str | None = Field(
        None,
        max_length=50,
        description="Valores validos: 'confirmado', 'por confirmar'.",
    )
    confirmado_por: str | None = Field(None, max_length=100, description="Area que confirmo el diagnostico.")
    confirmado_mediante: str | None = Field(
        None, max_length=200, description="Metodo mediante el cual se confirmo el diagnostico (texto libre)."
    )
    tratamiento_amparo: bool = Field(False, description="True si el caso esta relacionado con un tratamiento por amparo.")
    queja_derechos_humanos: bool = Field(False, description="True si el caso esta relacionado con una queja de derechos humanos.")
    prescripcion: str | None = Field(
        None,
        description="Auto-generado por el backend si se envian dosis/frecuencia/duracion/unidad_tiempo.",
    )
    dosis: float | None = Field(None, gt=0, description="Cantidad de unidades por toma (ej. 2).")
    cantidad: float | None = Field(None, gt=0, description="Cantidad de medicamento por unidad (ej. 10 para '10 mg').")
    frecuencia: int | None = Field(None, gt=0, description="Horas entre tomas (ej. 8, 12, 24).")
    unidad_tiempo: str | None = Field(None, description="'dias', 'semanas' o 'meses'.")
    duracion: int | None = Field(None, gt=0, description="Numero de unidades de tiempo (ej. 7).")

    @field_validator("clues", mode="before")
    @classmethod
    def normalizar_clues(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("confirmado_mediante")
    @classmethod
    def validar_confirmado_mediante(cls, v: str | None) -> str | None:
        if v is not None and v not in CONFIRMADO_MEDIANTE_OPTIONS:
            raise ValueError(f"confirmado_mediante debe ser uno de: {CONFIRMADO_MEDIANTE_OPTIONS}")
        return v


class RegistroCreate(RegistroBase):
    pass


class RegistroUpdate(BaseModel):
    fecha_inicio_tratamiento: date | None = None
    fecha_primera_administracion: date | None = None
    fecha_fin_tratamiento: date | None = None
    dosis_administrada: str | None = Field(None, max_length=100)
    peso: Decimal | None = None
    talla: Decimal | None = None
    estatus_diagnostico: str | None = Field(None, max_length=50)
    confirmado_por: str | None = Field(None, max_length=100)
    confirmado_mediante: str | None = Field(None, max_length=200)
    tratamiento_amparo: bool | None = None
    queja_derechos_humanos: bool | None = None
    prescripcion: str | None = None
    dosis: float | None = Field(None, gt=0)
    cantidad: float | None = Field(None, gt=0)
    frecuencia: int | None = Field(None, gt=0)
    unidad_tiempo: str | None = None
    duracion: int | None = Field(None, gt=0)
    id_diagnostico: int | None = None
    es_activo: bool | None = Field(
        None,
        description="False = anular registro por error de captura (Soft Delete).",
    )

    @field_validator("confirmado_mediante")
    @classmethod
    def validar_confirmado_mediante(cls, v: str | None) -> str | None:
        if v is not None and v not in CONFIRMADO_MEDIANTE_OPTIONS:
            raise ValueError(f"confirmado_mediante debe ser uno de: {CONFIRMADO_MEDIANTE_OPTIONS}")
        return v


class RegistroResponse(RegistroBase):
    id_registro: int
    es_activo: bool
    fecha_registro_sistema: datetime
    id_usuario_registro: int | None
    nombre_paciente: str | None = None
    curp_paciente: str | None = None
    total_medicamento: float | None = None
    id_registro_origen: int | None = None
    medicamento: MedicamentoResponse | None = None
    medico: MedicoResponse | None = None
    diagnostico: DiagnosticoResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class RegistroListResponse(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    resultados: list[RegistroResponse]


class RegistroCompletoCreate(BaseModel):
    id_paciente: int | None = Field(None, description="ID de un paciente ya identificado por busqueda (con o sin CURP).")
    curp_paciente: CurpStr | None = None
    nombre_completo: str | None = Field(None, max_length=255)
    fecha_nacimiento: date | None = Field(None, description="Fecha de nacimiento del paciente nuevo.")
    clues_unidad_adscripcion: str | None = Field(None, max_length=20)
    id_medico: int = Field(..., description="ID del medico que prescribe.")
    clave_cnis: ClaveCnisStr
    clues: CluesStr
    fecha_inicio_tratamiento: date | None = None
    fecha_primera_administracion: date | None = None
    fecha_fin_tratamiento: date | None = None
    dosis_administrada: str | None = Field(None, max_length=100)
    peso: Decimal | None = None
    talla: Decimal | None = None
    estatus_diagnostico: str | None = Field(None, max_length=50)
    confirmado_por: str | None = Field(None, max_length=100)
    confirmado_mediante: str | None = Field(None, max_length=200)
    tratamiento_amparo: bool = False
    queja_derechos_humanos: bool = False
    prescripcion: str | None = None
    dosis: float | None = Field(None, gt=0)
    cantidad: float | None = Field(None, gt=0)
    frecuencia: int | None = Field(None, gt=0)
    unidad_tiempo: str | None = None
    duracion: int | None = Field(None, gt=0)
    id_diagnostico: int | None = None
    numero_expediente: str | None = Field(None, max_length=100, description="Numero de expediente en la unidad de la prescripcion.")

    @field_validator("curp_paciente", mode="before")
    @classmethod
    def normalizar_curp(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        return v.strip().upper()

    @field_validator("clues", mode="before")
    @classmethod
    def normalizar_clues(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("confirmado_mediante")
    @classmethod
    def validar_confirmado_mediante(cls, v: str | None) -> str | None:
        if v is not None and v not in CONFIRMADO_MEDIANTE_OPTIONS:
            raise ValueError(f"confirmado_mediante debe ser uno de: {CONFIRMADO_MEDIANTE_OPTIONS}")
        return v


class RegistroCompletoResponse(RegistroResponse):
    """Extiende RegistroResponse con info del paciente y si fue creado en esta llamada."""
    paciente_creado: bool = False
    curp_paciente: str | None = None
    nombre_paciente: str | None = None


class ValidarContinuidadRequest(BaseModel):
    nueva_fecha_fin_tratamiento: date | None = Field(
        None,
        description="Requerida solo si el registro no tiene posologia guardada (fallback legacy).",
    )