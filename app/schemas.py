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

# Estatus de evolución del paciente — banderín de color en Pacientes Activos.
# "Inicia tx" es el valor por defecto para pacientes nuevos y existentes.
ESTATUS_EVOLUCION_OPTIONS = ["Inicia tx", "Tx fase intermedia", "Recaída", "Curación"]

# Motivo de baja del paciente — obligatorio al dar de baja desde Pacientes Activos.
MOTIVO_BAJA_OPTIONS = [
    "Efecto adverso",
    "Defunción",
    "Cambio de tratamiento",
    "Atención en seguridad social o medios privados",
]

# Método mediante el cual se confirmó el diagnóstico — Registro.confirmado_mediante.
CONFIRMADO_MEDIANTE_OPTIONS = [
    "Médico tratante (Clínico)",
    "Estudios de laboratorio especializados",
    "Confirmación por centro de referencia o especialista",
]


# ---------------------------------------------------------------------------
# ── 0. CatDiagnostico ───────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# ── 1. CatMedicamento ───────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class MedicamentoBase(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=3000)
    grupo: str | None = Field(None, max_length=150)
    tipo_clave: str | None = Field(None, max_length=100)
    unidad: str | None = Field(None, max_length=100, description="Unidad singular del medicamento (ej. 'tableta', 'inyección', 'ml').")
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
                "CURP inválida. Debe tener 18 caracteres con el formato oficial "
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
        description=f"Estatus de evolución del paciente. Valores válidos: {ESTATUS_EVOLUCION_OPTIONS}",
    )

    @field_validator("estatus_evolucion")
    @classmethod
    def validar_estatus_evolucion(cls, v: str) -> str:
        if v not in ESTATUS_EVOLUCION_OPTIONS:
            raise ValueError(f"estatus_evolucion debe ser uno de: {ESTATUS_EVOLUCION_OPTIONS}")
        return v


class BajaPacienteRequest(BaseModel):
    motivo_baja: list[str] = Field(
        ..., min_length=1, description=f"Uno o más motivos de la baja. Valores válidos: {MOTIVO_BAJA_OPTIONS}"
    )

    @field_validator("motivo_baja")
    @classmethod
    def validar_motivo_baja(cls, v: list[str]) -> list[str]:
        invalidos = [m for m in v if m not in MOTIVO_BAJA_OPTIONS]
        if invalidos:
            raise ValueError(f"motivo_baja contiene valores inválidos: {invalidos}. Válidos: {MOTIVO_BAJA_OPTIONS}")
        return v


class PacienteResponse(BaseModel):
    """
    Los campos cifrados (curp_paciente, nombre_completo, diagnostico_actual)
    se populan manualmente en el endpoint después de descifrar — no vienen
    directamente del ORM, por eso este schema no hereda de PacienteBase.
    """
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
    adherencia_medicamentos: list[int | None] = Field(
        default_factory=list,
        description="Días de adherencia por medicamento activo, alineado posicionalmente con medicamentos_activos.",
    )
    diagnosticos_activos: list[str] = Field(
        default_factory=list,
        description="Nombres de diagnósticos de prescripciones activas.",
    )
    tiene_reaccion_adversa: bool = Field(
        False,
        description="True si el paciente tiene al menos una reacción adversa registrada.",
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
    es_activo: bool | None = None


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
    es_activo: bool = True

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# ── 5b. Expediente del Paciente por Unidad ──────────────────────────────────
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# ── 6. Registro (anteriormente Receta — Blueprint v6) ───────────────────────
# ---------------------------------------------------------------------------

class RegistroBase(BaseModel):
    id_medico: int = Field(..., description="ID del médico que prescribe.")
    id_paciente: int = Field(..., description="ID interno del paciente (PK de la tabla pacientes).")
    clave_cnis: ClaveCnisStr
    clues: CluesStr
    id_diagnostico: int | None = Field(None, description="ID del diagnóstico del catálogo.")
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
    confirmado_mediante: str | None = Field(
        None, max_length=200, description="Método mediante el cual se confirmó el diagnóstico (texto libre)."
    )
    tratamiento_amparo: bool = Field(False, description="True si el caso está relacionado con un tratamiento por amparo.")
    queja_derechos_humanos: bool = Field(False, description="True si el caso está relacionado con una queja de derechos humanos.")
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
    diagnostico: DiagnosticoResponse | None = None

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
    # Identificador del paciente — exactamente una de estas dos vías, o ninguna
    # si se está registrando un paciente nuevo sin CURP:
    #   - id_paciente: paciente ya identificado (con o sin CURP) por búsqueda de nombre
    #   - curp_paciente: identifica/crea por CURP (flujo histórico)
    id_paciente: int | None = Field(None, description="ID de un paciente ya identificado por búsqueda (con o sin CURP).")
    curp_paciente: CurpStr | None = None

    # Datos del paciente — requeridos solo si no se identifica un paciente existente
    nombre_completo: str | None = Field(None, max_length=255)
    fecha_nacimiento: date | None = Field(None, description="Fecha de nacimiento del paciente nuevo.")
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
    # Expediente: si se provee, crea/actualiza el expediente del paciente en la unidad de la prescripción
    numero_expediente: str | None = Field(None, max_length=100, description="Número de expediente en la unidad de la prescripción.")

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


# ---------------------------------------------------------------------------
# ── 8. Búsqueda nacional de paciente por CURP ───────────────────────────────
# ---------------------------------------------------------------------------

class BusquedaCurpResponse(BaseModel):
    existe: bool
    id_paciente: int | None = None
    nombre_completo: str | None = None
    fecha_nacimiento: date | None = None
    clues_unidad_adscripcion: str | None = None
    nombre_unidad: str | None = None
    total_registros: int | None = None


# ---------------------------------------------------------------------------
# ── 8b. Búsqueda nacional de paciente por nombre ────────────────────────────
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# ── 8c. Reacciones Adversas a Medicamentos ───────────────────────────────────
# ---------------------------------------------------------------------------

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
    email: str
    nombre_usuario: str
    clues_unidad_asignada: str | None = None
    nombre_unidad: str | None = None
    id_entidad: str | None = None


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
