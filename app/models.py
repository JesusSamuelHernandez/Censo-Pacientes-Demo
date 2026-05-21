"""
models.py — Definición de tablas ORM (SQLAlchemy) para la App Medicamentos de Alto Costo.

Tablas:
    - CatMedicamentos   : Catálogo maestro de medicamentos (clave CNIS).
    - UnidadMedica      : Establecimientos de salud (CLUES como PK).
    - Usuario           : Cuentas de la plataforma con roles RBAC.
    - Paciente          : Padrón de pacientes en tratamiento.
    - Medico            : Profesionales médicos adscritos a unidades.
    - Registro          : Censo de prescripción de medicamentos por paciente (Blueprint v6).

Convenciones:
    - Soft Delete        : columna es_activo (Boolean) en Paciente y Registro.
    - Auditoría          : id_usuario_registro (FK → usuarios) en Paciente y Registro.
    - Adherencia         : calculada en capa de endpoint desde el registro activo más reciente
                           como (fecha_actual - registro.fecha_inicio_tratamiento).days.
    - Timestamps auto    : fecha_registro (Paciente) y fecha_registro_sistema (Registro) usan
                           server_default=func.now() para que sea la BD quien estampe la hora.
"""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Roles válidos — constantes centralizadas para evitar strings sueltos.
# ---------------------------------------------------------------------------
class Rol:
    SUPER_ADMIN         = "SUPER_ADMIN"
    ADMIN_ESTATAL       = "ADMIN_ESTATAL"
    RESPONSABLE_UNIDAD  = "RESPONSABLE_UNIDAD"

    TODOS = {SUPER_ADMIN, ADMIN_ESTATAL, RESPONSABLE_UNIDAD}


# ---------------------------------------------------------------------------
# 1. Catálogo Maestro de Medicamentos
# ---------------------------------------------------------------------------
class CatMedicamento(Base):
    """
    Catálogo oficial de medicamentos de alto costo identificados por Clave CNIS.
    Solo el SUPER_ADMIN puede crear/editar/desactivar entradas (Soft Delete via es_activo).
    """
    __tablename__ = "cat_medicamentos"

    clave_cnis: Mapped[str] = mapped_column(String(50), primary_key=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    grupo: Mapped[str | None] = mapped_column(String(150))
    tipo_clave: Mapped[str | None] = mapped_column(String(100))
    unidad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unidad_de_medida: Mapped[str | None] = mapped_column(String(50), nullable=True)
    es_activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    registros: Mapped[list["Registro"]] = relationship(back_populates="medicamento")

    def __repr__(self) -> str:
        return f"<CatMedicamento clave_cnis={self.clave_cnis!r}>"


# ---------------------------------------------------------------------------
# 2. Unidades Médicas
# ---------------------------------------------------------------------------
class UnidadMedica(Base):
    """
    Establecimientos de salud. La CLUES (Clave Única de Establecimientos de Salud)
    es la llave primaria y punto de anclaje para los filtros RBAC de unidad.
    """
    __tablename__ = "cat_unidades"

    clues: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre_de_la_unidad: Mapped[str] = mapped_column(String(255), nullable=False)
    id_entidad: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    categoria_gerencial: Mapped[str | None] = mapped_column(String(150))

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="unidad_asignada")
    pacientes: Mapped[list["Paciente"]] = relationship(back_populates="unidad_adscripcion")
    medicos: Mapped[list["Medico"]] = relationship(back_populates="unidad_adscripcion")
    registros: Mapped[list["Registro"]] = relationship(back_populates="unidad")

    def __repr__(self) -> str:
        return f"<UnidadMedica clues={self.clues!r} nombre={self.nombre_de_la_unidad!r}>"


# ---------------------------------------------------------------------------
# 3. Usuarios de la Plataforma
# ---------------------------------------------------------------------------
class Usuario(Base):
    """
    Cuentas de acceso a la plataforma.

    RBAC:
        - SUPER_ADMIN         : sin filtro geográfico.
        - ADMIN_ESTATAL       : filtro por id_entidad.
        - RESPONSABLE_UNIDAD  : filtro por clues_unidad_asignada.

    El campo clues_unidad_asignada es NULL para SUPER_ADMIN y ADMIN_ESTATAL.
    El campo id_entidad es NULL para SUPER_ADMIN y RESPONSABLE_UNIDAD.
    """
    __tablename__ = "usuarios"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_usuario: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    rol_nombre: Mapped[str] = mapped_column(String(30), nullable=False)

    clues_unidad_asignada: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("cat_unidades.clues", ondelete="RESTRICT"), nullable=True
    )
    id_entidad: Mapped[str | None] = mapped_column(String(100), nullable=True)

    debe_cambiar_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    unidad_asignada: Mapped["UnidadMedica | None"] = relationship(back_populates="usuarios")

    pacientes_registrados: Mapped[list["Paciente"]] = relationship(
        back_populates="usuario_registro",
        foreign_keys="Paciente.id_usuario_registro",
    )
    registros_registrados: Mapped[list["Registro"]] = relationship(
        back_populates="usuario_registro",
        foreign_keys="Registro.id_usuario_registro",
    )

    def __repr__(self) -> str:
        return f"<Usuario id={self.id_usuario} email={self.email!r} rol={self.rol_nombre!r}>"


# ---------------------------------------------------------------------------
# 4. Pacientes
# ---------------------------------------------------------------------------
class Paciente(Base):
    """
    Padrón de pacientes en tratamiento con medicamentos de alto costo.

    - PK interna  : id_paciente (int autoincremental).
    - Soft Delete : es_activo = False (nunca se elimina físicamente).
    - Auditoría   : id_usuario_registro guarda quién capturó o modificó el registro.
    - Adherencia  : calculada en la capa de endpoint desde el registro activo más reciente.
    """
    __tablename__ = "pacientes"

    id_paciente: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    curp_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    curp_paciente: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nombre_completo: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    diagnostico_actual: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    clues_unidad_adscripcion: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    es_activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    id_usuario_registro: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )

    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    unidad_adscripcion: Mapped["UnidadMedica"] = relationship(back_populates="pacientes")
    usuario_registro: Mapped["Usuario | None"] = relationship(
        back_populates="pacientes_registrados",
        foreign_keys=[id_usuario_registro],
    )
    registros: Mapped[list["Registro"]] = relationship(
        back_populates="paciente",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Paciente id={self.id_paciente}>"


# ---------------------------------------------------------------------------
# 5. Médicos
# ---------------------------------------------------------------------------
class Medico(Base):
    """
    Profesionales médicos adscritos a unidades médicas.
    Pueden ser registrados por RESPONSABLE_UNIDAD (su unidad) o SUPER_ADMIN.
    Solo SUPER_ADMIN puede editar o eliminar.
    """
    __tablename__ = "medicos"

    id_medico: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cedula_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    nombre_medico: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    cedula: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    clues_adscripcion: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    unidad_adscripcion: Mapped["UnidadMedica"] = relationship(back_populates="medicos")
    registros: Mapped[list["Registro"]] = relationship(back_populates="medico")

    def __repr__(self) -> str:
        return f"<Medico id={self.id_medico}>"


# ---------------------------------------------------------------------------
# 6. Registros (anteriormente Recetas — Blueprint v6)
# ---------------------------------------------------------------------------
class Registro(Base):
    """
    Registro de prescripción de medicamento a un paciente por un médico.

    - id_registro               : PK autoincremental (int). El folio ya no lo ingresa el usuario.
    - Soft Delete               : es_activo = False cuando se anula por error de captura.
    - Auditoría                 : id_usuario_registro identifica quién capturó el dato.
    - fecha_primera_administracion : fecha real de la primera dosis.
    - Adherencia                : calculada en endpoint como
                                  (date.today() - fecha_inicio_tratamiento).days
                                  usando el registro activo más reciente del paciente.
    """
    __tablename__ = "registros"

    id_registro: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    id_medico: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("medicos.id_medico", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    id_paciente: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pacientes.id_paciente", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    clave_cnis: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("cat_medicamentos.clave_cnis", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    clues: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    fecha_inicio_tratamiento: Mapped[date | None] = mapped_column(Date)
    fecha_primera_administracion: Mapped[date | None] = mapped_column(Date)
    fecha_fin_tratamiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    dosis_administrada: Mapped[str | None] = mapped_column(String(100))
    peso: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    talla: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    estatus_diagnostico: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confirmado_por: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prescripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Campos de posología — calculados automáticamente por el backend
    dosis: Mapped[float | None] = mapped_column(Float, nullable=True)
    cantidad: Mapped[float | None] = mapped_column(Float, nullable=True)
    frecuencia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unidad_tiempo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duracion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_medicamento: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Trazabilidad de reemplazos (cuando se edita desde Notificaciones)
    id_registro_origen: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("registros.id_registro", ondelete="SET NULL"),
        nullable=True,
    )

    fecha_registro_sistema: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    id_usuario_registro: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )

    es_activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    medico: Mapped["Medico"] = relationship(back_populates="registros")
    paciente: Mapped["Paciente"] = relationship(back_populates="registros")
    medicamento: Mapped["CatMedicamento"] = relationship(back_populates="registros")
    unidad: Mapped["UnidadMedica"] = relationship(back_populates="registros")
    usuario_registro: Mapped["Usuario | None"] = relationship(
        back_populates="registros_registrados",
        foreign_keys=[id_usuario_registro],
    )

    def __repr__(self) -> str:
        return (
            f"<Registro id={self.id_registro!r} "
            f"id_paciente={self.id_paciente!r} "
            f"med={self.clave_cnis!r}>"
        )


# ---------------------------------------------------------------------------
# 7. Notificaciones de Transferencia (Blueprint Transferencia Paciente Paso 3)
# ---------------------------------------------------------------------------
class NotificacionTransferencia(Base):
    """
    Registro generado automáticamente cuando un paciente es transferido entre unidades.
    Notifica a la unidad de origen para que quede enterada del traslado.
    Se marca como leída a nivel de unidad: el primer usuario de la unidad que la acepta
    la desaparece para todos.
    """
    __tablename__ = "notificaciones_transferencia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    id_paciente: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pacientes.id_paciente", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clues_unidad_origen: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    clues_unidad_destino: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="RESTRICT"),
        nullable=False,
    )
    id_usuario_traslado: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )
    fecha_traslado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    leida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    id_usuario_leida: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )
    fecha_leida: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    paciente: Mapped["Paciente"] = relationship(foreign_keys=[id_paciente])
    unidad_origen: Mapped["UnidadMedica"] = relationship(foreign_keys=[clues_unidad_origen])
    unidad_destino: Mapped["UnidadMedica"] = relationship(foreign_keys=[clues_unidad_destino])
    usuario_traslado: Mapped["Usuario | None"] = relationship(foreign_keys=[id_usuario_traslado])
    usuario_leida: Mapped["Usuario | None"] = relationship(foreign_keys=[id_usuario_leida])

    def __repr__(self) -> str:
        return f"<NotificacionTransferencia id={self.id} paciente={self.id_paciente}>"
