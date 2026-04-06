"""
schemas.py — Esquemas Pydantic v2 para validación de entrada/salida de la API.

Patrón por entidad:
    XxxBase     : campos comunes compartidos entre Create y Response.
    XxxCreate   : payload que el cliente envía en POST.
    XxxUpdate   : payload parcial para PATCH (todos los campos son opcionales).
    XxxResponse : lo que la API devuelve al cliente (nunca expone contraseñas).

Validaciones destacadas:
    - CURP        : exactamente 18 caracteres, patrón oficial mexicano.
    - CLUES       : alfanumérico, 1-20 caracteres.
    - rol_nombre  : debe ser uno de los 3 roles definidos en el Blueprint.
    - email       : formato estándar vía EmailStr de Pydantic.
    - password    : mínimo 8 caracteres (solo en Create, nunca en Response).
    - es_activo   : presente en Paciente y Suministro (Soft Delete).
"""
import re
from datetime import date, datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models import Rol


# ---------------------------------------------------------------------------
# Tipos anotados reutilizables
# ---------------------------------------------------------------------------

# CURP oficial: 4 letras + 6 dígitos (AAMMDD) + H/M + 2 letras estado +
#               3 letras consonantes internas + 2 alfanuméricos homoclave.
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
        description="Clave Única de Establecimiento de Salud (CLUES).",
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
        description=f"Rol del usuario. Valores válidos: {sorted(Rol.TODOS)}",
        examples=[Rol.RESPONSABLE_UNIDAD],
    ),
]


# ---------------------------------------------------------------------------
# ── 1. CatMedicamento ───────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class MedicamentoBase(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=2000)
    grupo: str | None = Field(None, max_length=150)
    tipo_clave: str | None = Field(None, max_length=100)


class MedicamentoCreate(MedicamentoBase):
    clave_cnis: ClaveCnisStr


class MedicamentoUpdate(BaseModel):
    """Todos los campos son opcionales para soportar PATCH parcial."""
    descripcion: str | None = Field(None, min_length=1, max_length=2000)
    grupo: str | None = Field(None, max_length=150)
    tipo_clave: str | None = Field(None, max_length=100)
    es_activo: bool | None = None


class MedicamentoResponse(MedicamentoBase):
    clave_cnis: str
    es_activo: bool

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# ── 2. UnidadMedica ─────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# ── 3. Usuario ──────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class UsuarioBase(BaseModel):
    nombre_usuario: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    rol_nombre: RolStr
    clues_unidad_asignada: str | None = Field(
        None,
        max_length=20,
        description="Requerido solo para RESPONSABLE_UNIDAD.",
    )
    id_entidad: str | None = Field(
        None,
        max_length=100,
        description="Requerido solo para ADMIN_ESTATAL.",
    )

    @field_validator("rol_nombre")
    @classmethod
    def rol_debe_ser_valido(cls, v: str) -> str:
        if v not in Rol.TODOS:
            raise ValueError(
                f"rol_nombre '{v}' no es válido. Debe ser uno de: {sorted(Rol.TODOS)}"
            )
        return v

    @model_validator(mode="after")
    def validar_contexto_por_rol(self) -> "UsuarioBase":
        """
        Reglas de coherencia entre rol y campos geográficos:
          - RESPONSABLE_UNIDAD requiere clues_unidad_asignada.
          - ADMIN_ESTATAL requiere id_entidad.
          - SUPER_ADMIN no requiere ninguno de los dos.
        """
        rol = self.rol_nombre
        if rol == Rol.RESPONSABLE_UNIDAD and not self.clues_unidad_asignada:
            raise ValueError(
                "clues_unidad_asignada es requerido para el rol RESPONSABLE_UNIDAD."
            )
        if rol == Rol.ADMIN_ESTATAL and not self.id_entidad:
            raise ValueError(
                "id_entidad es requerido para el rol ADMIN_ESTATAL."
            )
        return self


class UsuarioCreate(UsuarioBase):
    """
    Payload de creación. Acepta contraseña en texto plano;
    el endpoint la hashea antes de persistir.
    """
    password: str = Field(
        ...,
        min_length=8,
        description="Contraseña en texto plano. Se almacenará hasheada.",
    )


class UsuarioUpdate(BaseModel):
    """Campos editables por el SUPER_ADMIN."""
    nombre_usuario: str | None = Field(None, min_length=2, max_length=150)
    rol_nombre: str | None = None
    clues_unidad_asignada: str | None = Field(None, max_length=20)
    id_entidad: str | None = Field(None, max_length=100)
    password: str | None = Field(None, min_length=8)

    @field_validator("rol_nombre")
    @classmethod
    def rol_valido_si_presente(cls, v: str | None) -> str | None:
        if v is not None and v not in Rol.TODOS:
            raise ValueError(
                f"rol_nombre '{v}' no es válido. Debe ser uno de: {sorted(Rol.TODOS)}"
            )
        return v


class UsuarioResponse(BaseModel):
    """Respuesta pública: NUNCA incluye hashed_password ni la contraseña original."""
    id_usuario: int
    nombre_usuario: str
    email: str
    rol_nombre: str
    clues_unidad_asignada: str | None
    id_entidad: str | None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# ── 4. Paciente ─────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class PacienteBase(BaseModel):
    nombre_completo: str = Field(..., min_length=2, max_length=255)
    diagnostico_actual: str | None = Field(None, max_length=5000)
    fecha_inicio_tratamiento: date | None = None
    clues_unidad_adscripcion: CluesStr

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
                "CURP inválida. Debe tener 18 caracteres con el formato oficial "
                "(ej. LOOA890101HDFPRS09)."
            )
        return curp


class PacienteUpdate(BaseModel):
    """PATCH parcial — solo se actualizan los campos enviados."""
    nombre_completo: str | None = Field(None, min_length=2, max_length=255)
    diagnostico_actual: str | None = Field(None, max_length=5000)
    fecha_inicio_tratamiento: date | None = None
    clues_unidad_adscripcion: str | None = Field(None, max_length=20)
    es_activo: bool | None = Field(
        None,
        description="False = dar de baja al paciente (Soft Delete).",
    )


class PacienteResponse(PacienteBase):
    curp_paciente: str
    es_activo: bool
    fecha_registro: datetime
    id_usuario_registro: int | None

    # Campo calculado: días desde el inicio del tratamiento hasta hoy.
    # Se puebla en el endpoint a partir de Paciente.dias_adherencia.
    dias_adherencia: int | None = Field(
        None,
        description="Días transcurridos desde fecha_inicio_tratamiento hasta hoy.",
    )

    model_config = ConfigDict(from_attributes=True)


class PacienteListResponse(BaseModel):
    """Respuesta paginada para GET /pacientes."""
    total: int
    pagina: int
    por_pagina: int
    resultados: list[PacienteResponse]


# ---------------------------------------------------------------------------
# ── 5. Suministro ───────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class SuministroBase(BaseModel):
    curp_paciente: CurpStr
    clave_cnis_med: ClaveCnisStr
    dosis_administrada: str | None = Field(
        None,
        max_length=100,
        description="Ej. '200 mg', '1 ampolleta'.",
        examples=["200 mg"],
    )
    fecha_primera_administracion: date | None = Field(
        None,
        description="Fecha real en que el paciente recibió la primera dosis.",
    )

    @field_validator("curp_paciente", mode="before")
    @classmethod
    def normalizar_curp(cls, v: str) -> str:
        return v.strip().upper()


class SuministroCreate(SuministroBase):
    """
    Payload para registrar una nueva asignación de tratamiento.
    id_usuario_registro se inyecta automáticamente desde el token JWT en el endpoint.
    """
    pass


class SuministroUpdate(BaseModel):
    """
    PATCH parcial. Incluye es_activo para el Soft Delete por error de captura.
    No se permite cambiar curp_paciente ni clave_cnis_med una vez creado el registro.
    """
    dosis_administrada: str | None = Field(None, max_length=100)
    fecha_primera_administracion: date | None = None
    es_activo: bool | None = Field(
        None,
        description="False = anular registro por error de captura (Soft Delete).",
    )


class SuministroResponse(SuministroBase):
    id_suministro: int
    es_activo: bool
    fecha_registro_sistema: datetime
    id_usuario_registro: int | None

    # Datos embebidos del medicamento (evita N+1 requests en el cliente).
    medicamento: MedicamentoResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class SuministroListResponse(BaseModel):
    """Respuesta paginada para GET /suministros."""
    total: int
    pagina: int
    por_pagina: int
    resultados: list[SuministroResponse]


# ---------------------------------------------------------------------------
# ── 6. Auth ─────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Respuesta del endpoint POST /auth/login."""
    access_token: str
    token_type: str = "bearer"
    rol_nombre: str
    id_usuario: int
