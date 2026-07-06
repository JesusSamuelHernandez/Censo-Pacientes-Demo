"""Schemas de catalogos: diagnosticos, medicamentos, unidades y puestos."""
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ClaveCnisStr, CluesStr


class DiagnosticoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=500)
    codigo_cie10: str | None = Field(None, max_length=20)


class DiagnosticoCreate(DiagnosticoBase):
    pass


class DiagnosticoUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=500)
    codigo_cie10: str | None = Field(None, max_length=20)
    es_activo: bool | None = None


class DiagnosticoResponse(DiagnosticoBase):
    id_diagnostico: int
    es_activo: bool

    model_config = ConfigDict(from_attributes=True)


class PuestoResponse(BaseModel):
    codigo: str
    denominacion_puesto: str
    es_activo: bool

    model_config = ConfigDict(from_attributes=True)


class MedicamentoBase(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=3000)
    grupo: str | None = Field(None, max_length=150)
    tipo_clave: str | None = Field(None, max_length=100)
    unidad: str | None = Field(None, max_length=100, description="Unidad singular del medicamento (ej. 'tableta', 'inyeccion', 'ml').")
    unidad_de_medida: str | None = Field(None, max_length=50, description="Unidad de medida de la cantidad (ej. 'mg', 'ml', 'UI').")


class MedicamentoCreate(MedicamentoBase):
    clave_cnis: ClaveCnisStr


class MedicamentoUpdate(BaseModel):
    descripcion: str | None = Field(None, min_length=1, max_length=3000)
    grupo: str | None = Field(None, max_length=150)
    tipo_clave: str | None = Field(None, max_length=100)
    unidad: str | None = Field(None, max_length=100)
    unidad_de_medida: str | None = Field(None, max_length=50)
    es_activo: bool | None = None


class MedicamentoResponse(MedicamentoBase):
    clave_cnis: str
    es_activo: bool

    model_config = ConfigDict(from_attributes=True)


class UnidadMedicaBase(BaseModel):
    nombre_de_la_unidad: str = Field(..., min_length=1, max_length=255)
    id_entidad: str = Field(..., min_length=1, max_length=100)
    categoria_gerencial: str | None = Field(None, max_length=150)


class UnidadMedicaCreate(UnidadMedicaBase):
    clues: CluesStr


class UnidadMedicaUpdate(BaseModel):
    nombre_de_la_unidad: str | None = Field(None, min_length=1, max_length=255)
    id_entidad: str | None = Field(None, min_length=1, max_length=100)
    categoria_gerencial: str | None = Field(None, max_length=150)


class UnidadMedicaResponse(UnidadMedicaBase):
    clues: str

    model_config = ConfigDict(from_attributes=True)