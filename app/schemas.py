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
    - es_activo   : presente en Paciente y Registro (Soft Delete).
"""
import re
from datetime import date, datetime
from decimal import Decimal
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
    unidad: str | None = Field(None, max_length=100, description="Unidad singular del medicamento (ej. 'tableta', 'inyección', 'ml').")
    unidad_de_medida: str | None = Field(None, max_length=50, description="Unidad de medida de la cantidad (ej. 'mg', 'ml', 'UI').")


class MedicamentoCreate(MedicamentoBase):
    clave_cnis: ClaveCnisStr


class MedicamentoUpdate(BaseModel):
    descripcion: str | None = Field(None, min_length=1, max_length=2000)
    grupo: str | None = Field(None, max_length=150)
    tipo_clave: str | None = Field(None, max_length=100)
    unidad: str | None = Field(None, max_length=100)
    unidad_de_medida: str | None = Field(None, max_length=50)
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
    pass  # La contraseña la genera el backend automáticamente.


class UsuarioUpdate(BaseModel):
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
    id_usuario: int
    nombre_usuario: str
    email: str
    rol_nombre: str
    clues_unidad_asignada: str | None
    id_entidad: str | None
    debe_cambiar_password: bool

    model_config = ConfigDict(from_attributes=True)


class UsuarioCreateResponse(UsuarioResponse):
    """Respuesta exclusiva de POST /usuarios. Incluye la contraseña temporal en texto plano.
    Solo el SUPER_ADMIN que crea la cuenta puede verla — no se almacena en BD."""
    password_temporal: str


# ---------------------------------------------------------------------------
# ── 4. Paciente ─────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class PacienteBase(BaseModel):
    nombre_completo: str = Field(..., min_length=2, max_length=255)
    diagnostico_actual: str | None = Field(None, max_length=5000)
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
    nombre_completo: str | None = Field(None, min_length=2, max_length=255)
    diagnostico_actual: str | None = Field(None, max_length=5000)
    clues_unidad_adscripcion: str | None = Field(None, max_length=20)
    es_activo: bool | None = Field(
        None,
        description="False = dar de baja al paciente (Soft Delete).",
    )


class PacienteResponse(BaseModel):
    """
    Los campos cifrados (curp_paciente, nombre_completo, diagnostico_actual)
    se populan manualmente en el endpoint después de descifrar — no vienen
    directamente del ORM, por eso este schema no hereda de PacienteBase.
    """
    id_paciente: int
    curp_paciente: str
    nombre_completo: str
    diagnostico_actual: str | None
    clues_unidad_adscripcion: str
    es_activo: bool
    fecha_registro: datetime
    id_usuario_registro: int | None
    dias_adherencia: int | None = Field(
        None,
        description="Días desde fecha_inicio_tratamiento del registro activo más reciente.",
    )
    tiene_prescripcion_activa: bool = Field(
        False,
        description="True si el paciente tiene al menos un registro con es_activo=True.",
    )
    medicamentos_activos: list[str] = Field(
        default_factory=list,
        description="Descripciones de los medicamentos de prescripciones activas.",
    )

    model_config = ConfigDict(from_attributes=True)


class PacienteListResponse(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    resultados: list[PacienteResponse]


# ---------------------------------------------------------------------------
# ── 5. Medico ───────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class MedicoBase(BaseModel):
    nombre_medico: str = Field(..., min_length=2, max_length=255)
    cedula: str = Field(..., min_length=1, max_length=30, description="Cédula profesional única.")
    email: str | None = Field(None, max_length=255)
    clues_adscripcion: CluesStr

    @field_validator("clues_adscripcion", mode="before")
    @classmethod
    def normalizar_clues(cls, v: str) -> str:
        return v.strip().upper()


class MedicoCreate(MedicoBase):
    pass


class MedicoUpdate(BaseModel):
    nombre_medico: str | None = Field(None, min_length=2, max_length=255)
    cedula: str | None = Field(None, min_length=1, max_length=30)
    email: str | None = Field(None, max_length=255)
    clues_adscripcion: str | None = Field(None, max_length=20)


class MedicoResponse(BaseModel):
    """
    Los campos cifrados (nombre_medico, cedula) se populan manualmente
    en el endpoint después de descifrar.
    """
    id_medico: int
    nombre_medico: str
    cedula: str
    email: str | None
    clues_adscripcion: str

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# ── 6. Registro (anteriormente Receta — Blueprint v6) ───────────────────────
# ---------------------------------------------------------------------------

class RegistroBase(BaseModel):
    id_medico: int = Field(..., description="ID del médico que prescribe.")
    id_paciente: int = Field(..., description="ID interno del paciente (PK de la tabla pacientes).")
    clave_cnis: ClaveCnisStr
    clues: CluesStr
    fecha_inicio_tratamiento: date | None = Field(
        None, description="Inicio del esquema específico de esta prescripción."
    )
    fecha_primera_administracion: date | None = Field(
        None, description="Fecha real de la primera dosis."
    )
    fecha_fin_tratamiento: date | None = Field(
        None, description="Fecha en que termina la prescripción. Se suma 1 mes para la ventana de continuidad."
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
        description="Valores válidos: 'confirmado', 'por confirmar'.",
    )
    confirmado_por: str | None = Field(None, max_length=100, description="Área que confirmó el diagnóstico.")
    prescripcion: str | None = Field(
        None,
        description="Auto-generado por el backend si se envían dosis/frecuencia/duracion/unidad_tiempo.",
    )
    # Posología — el backend calcula prescripcion y total_medicamento a partir de estos campos
    dosis: float | None = Field(None, gt=0, description="Cantidad de unidades por toma (ej. 2).")
    cantidad: float | None = Field(None, gt=0, description="Cantidad de medicamento por unidad (ej. 10 para '10 mg').")
    frecuencia: int | None = Field(None, gt=0, description="Horas entre tomas (ej. 8, 12, 24).")
    unidad_tiempo: str | None = Field(None, description="'días', 'semanas' o 'meses'.")
    duracion: int | None = Field(None, gt=0, description="Número de unidades de tiempo (ej. 7).")

    @field_validator("clues", mode="before")
    @classmethod
    def normalizar_clues(cls, v: str) -> str:
        return v.strip().upper()


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
    prescripcion: str | None = None
    dosis: float | None = Field(None, gt=0)
    cantidad: float | None = Field(None, gt=0)
    frecuencia: int | None = Field(None, gt=0)
    unidad_tiempo: str | None = None
    duracion: int | None = Field(None, gt=0)
    es_activo: bool | None = Field(
        None,
        description="False = anular registro por error de captura (Soft Delete).",
    )


class RegistroResponse(RegistroBase):
    id_registro: int
    es_activo: bool
    fecha_registro_sistema: datetime
    id_usuario_registro: int | None

    # Datos del paciente embebidos (descifrados)
    nombre_paciente: str | None = None
    curp_paciente: str | None = None

    # Datos calculados por el backend
    total_medicamento: float | None = None

    # Trazabilidad de reemplazos
    id_registro_origen: int | None = None

    # Datos embebidos
    medicamento: MedicamentoResponse | None = None
    medico: MedicoResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class RegistroListResponse(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    resultados: list[RegistroResponse]


# ---------------------------------------------------------------------------
# ── 7. Registro combinado paciente + prescripción (Blueprint v6 Paso 4) ─────
# ---------------------------------------------------------------------------

class RegistroCompletoCreate(BaseModel):
    """
    Payload para POST /registros/completo.
    Crea (o reutiliza) un paciente y registra su prescripción en una sola llamada.
    Los campos de paciente solo son obligatorios cuando el CURP no existe en BD.
    """
    # Identificador del paciente — siempre requerido
    curp_paciente: CurpStr

    # Datos del paciente — requeridos solo si el CURP no existe en BD
    nombre_completo: str | None = Field(None, max_length=255)
    diagnostico_actual: str | None = Field(None, max_length=5000)
    # Si omitido, el backend usa la CLUES de la prescripción
    clues_unidad_adscripcion: str | None = Field(None, max_length=20)

    # Datos de la prescripción
    id_medico: int = Field(..., description="ID del médico que prescribe.")
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
    prescripcion: str | None = None
    dosis: float | None = Field(None, gt=0)
    cantidad: float | None = Field(None, gt=0)
    frecuencia: int | None = Field(None, gt=0)
    unidad_tiempo: str | None = None
    duracion: int | None = Field(None, gt=0)

    @field_validator("curp_paciente", mode="before")
    @classmethod
    def normalizar_curp(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("clues", mode="before")
    @classmethod
    def normalizar_clues(cls, v: str) -> str:
        return v.strip().upper()


class RegistroCompletoResponse(RegistroResponse):
    """Extiende RegistroResponse con info del paciente y si fue creado en esta llamada."""
    paciente_creado: bool = False
    curp_paciente: str | None = None
    nombre_paciente: str | None = None


# ---------------------------------------------------------------------------
# ── 8. Búsqueda nacional de paciente por CURP ───────────────────────────────
# ---------------------------------------------------------------------------

class BusquedaCurpResponse(BaseModel):
    existe: bool
    id_paciente: int | None = None
    nombre_completo: str | None = None
    clues_unidad_adscripcion: str | None = None
    nombre_unidad: str | None = None
    total_registros: int | None = None


# ---------------------------------------------------------------------------
# ── 8. Notificaciones ───────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class NotificacionResponse(BaseModel):
    id_registro: int
    id_paciente: int
    nombre_paciente: str
    clave_cnis: str
    descripcion_medicamento: str | None
    clues: str
    fecha_fin_tratamiento: date
    fecha_limite: date       # fecha_fin_tratamiento + 30 días
    dias_restantes: int      # negativo = ya venció; 0 = vence hoy
    es_activo: bool
    # Campos adicionales para la tarjeta de detalle
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


# ---------------------------------------------------------------------------
# ── 9. Validación de continuidad ────────────────────────────────────────────
# ---------------------------------------------------------------------------

class ValidarContinuidadRequest(BaseModel):
    nueva_fecha_fin_tratamiento: date | None = Field(
        None,
        description="Requerida solo si el registro no tiene posología guardada (fallback legacy).",
    )


# ---------------------------------------------------------------------------
# ── 10. Notificaciones de Transferencia ─────────────────────────────────────
# ---------------------------------------------------------------------------

class NotificacionTransferenciaResponse(BaseModel):
    id: int
    id_paciente: int
    nombre_paciente: str
    curp_paciente: str
    clues_unidad_origen: str
    nombre_unidad_origen: str | None
    clues_unidad_destino: str
    nombre_unidad_destino: str | None
    nombre_usuario_traslado: str | None
    fecha_traslado: datetime


class NotificacionTransferenciaListResponse(BaseModel):
    total: int
    resultados: list[NotificacionTransferenciaResponse]


# ---------------------------------------------------------------------------
# ── 11. Requerimiento Teórico Mensual (RTM) ──────────────────────────────────
# ---------------------------------------------------------------------------

class RtmMesItem(BaseModel):
    anio: int
    mes: int        # 1–12
    etiqueta: str   # "Mayo 2026"
    cantidad: float # total calculado en la unidad de medida del medicamento


class RtmFilaResponse(BaseModel):
    clave_cnis: str
    descripcion: str
    grupo: str | None
    unidad_de_medida: str | None  # ml, mg, UI…
    meses: list[RtmMesItem]       # n ítems en orden cronológico


class RtmResponse(BaseModel):
    clues: str
    nombre_unidad: str | None
    generado_en: str
    cabeceras: list[str]           # ["Mayo 2026", "Junio 2026", …]
    filas: list[RtmFilaResponse]   # una fila por medicamento con datos


# ---------------------------------------------------------------------------
# ── 9. Auth ─────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol_nombre: str
    id_usuario: int
    debe_cambiar_password: bool


# ---------------------------------------------------------------------------
# ── 8. Cambio de contraseña ─────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class CambiarPasswordRequest(BaseModel):
    password_actual: str = Field(..., min_length=1, description="Contraseña actual.")
    password_nueva: str = Field(
        ...,
        min_length=8,
        description="Nueva contraseña (mínimo 8 caracteres).",
    )
