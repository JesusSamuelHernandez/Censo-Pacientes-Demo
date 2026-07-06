"""Schemas de medicos."""
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import _CURP_REGEX, CluesStr


class MedicoBase(BaseModel):
    nombre_medico: str = Field(..., min_length=2, max_length=255)
    cedula: str = Field(..., min_length=1, max_length=30, description="Cedula profesional unica.")
    email: str | None = Field(None, max_length=255)
    clues_adscripcion: CluesStr

    @field_validator("clues_adscripcion", mode="before")
    @classmethod
    def normalizar_clues(cls, v: str) -> str:
        return v.strip().upper()


class MedicoCreate(MedicoBase):
    curp: str = Field(
        ...,
        min_length=18,
        max_length=18,
        description="CURP del medico (18 caracteres, formato oficial SEP/RENAPO).",
        examples=["LOOA890101HDFPRS09"],
    )
    id_puesto: str = Field(..., max_length=20, description="Codigo del puesto (catalogo cat_puestos).")

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

    @field_validator("id_puesto", mode="before")
    @classmethod
    def normalizar_id_puesto(cls, v: str) -> str:
        return v.strip().upper()


class MedicoUpdate(BaseModel):
    nombre_medico: str | None = Field(None, min_length=2, max_length=255)
    cedula: str | None = Field(None, min_length=1, max_length=30)
    curp: str | None = Field(None, min_length=18, max_length=18)
    id_puesto: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=255)
    clues_adscripcion: str | None = Field(None, max_length=20)
    es_activo: bool | None = None

    @field_validator("curp", mode="before")
    @classmethod
    def normalizar_y_validar_curp(cls, v: str | None) -> str | None:
        if v is None:
            return None
        curp = v.strip().upper()
        if not _CURP_REGEX.match(curp):
            raise ValueError(
                "CURP invalida. Debe tener 18 caracteres con el formato oficial "
                "(ej. LOOA890101HDFPRS09)."
            )
        return curp

    @field_validator("id_puesto", mode="before")
    @classmethod
    def normalizar_id_puesto(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v


class MedicoResponse(BaseModel):
    id_medico: int
    nombre_medico: str
    cedula: str
    curp: str | None = None
    id_puesto: str | None = None
    denominacion_puesto: str | None = None
    email: str | None
    clues_adscripcion: str
    es_activo: bool = True

    model_config = ConfigDict(from_attributes=True)