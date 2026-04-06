"""
models.py — Definición de tablas ORM (SQLAlchemy) para la App Medicamentos de Alto Costo.

Tablas:
    - CatMedicamentos   : Catálogo maestro de medicamentos (clave CNIS).
    - UnidadMedica      : Establecimientos de salud (CLUES como PK).
    - Usuario           : Cuentas de la plataforma con roles RBAC.
    - Paciente          : Padrón de pacientes en tratamiento.
    - Suministro        : Censo de asignación de medicamentos (no es bitácora diaria).

Convenciones:
    - Soft Delete        : columna es_activo (Boolean) en Paciente y Suministro.
    - Auditoría          : id_usuario_registro (FK → usuarios) en Paciente y Suministro.
    - Adherencia         : calculada en capa de servicio como (fecha_actual - fecha_inicio_tratamiento).days.
    - Timestamps auto    : fecha_registro (Paciente) y fecha_registro_sistema (Suministro) usan
                           server_default=func.now() para que sea la BD quien estampe la hora.
"""
from datetime import date, datetime
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
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
    es_activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relación inversa: todos los suministros que usan este medicamento.
    suministros: Mapped[list["Suministro"]] = relationship(back_populates="medicamento")

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
    __tablename__ = "unidades_medicas"

    clues: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre_de_la_unidad: Mapped[str] = mapped_column(String(255), nullable=False)
    id_entidad: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    categoria_gerencial: Mapped[str | None] = mapped_column(String(150))

    # Relaciones inversas
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="unidad_asignada")
    pacientes: Mapped[list["Paciente"]] = relationship(back_populates="unidad_adscripcion")

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

    # FK opcional → unidades_medicas (solo para RESPONSABLE_UNIDAD)
    clues_unidad_asignada: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("unidades_medicas.clues", ondelete="RESTRICT"), nullable=True
    )
    # Contexto geográfico para ADMIN_ESTATAL
    id_entidad: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relaciones ORM
    unidad_asignada: Mapped["UnidadMedica | None"] = relationship(back_populates="usuarios")

    # Auditoría: registros capturados por este usuario
    pacientes_registrados: Mapped[list["Paciente"]] = relationship(
        back_populates="usuario_registro",
        foreign_keys="Paciente.id_usuario_registro",
    )
    suministros_registrados: Mapped[list["Suministro"]] = relationship(
        back_populates="usuario_registro",
        foreign_keys="Suministro.id_usuario_registro",
    )

    def __repr__(self) -> str:
        return f"<Usuario id={self.id_usuario} email={self.email!r} rol={self.rol_nombre!r}>"


# ---------------------------------------------------------------------------
# 4. Pacientes
# ---------------------------------------------------------------------------
class Paciente(Base):
    """
    Padrón de pacientes en tratamiento con medicamentos de alto costo.

    - Soft Delete : es_activo = False (nunca se elimina físicamente).
    - Auditoría   : id_usuario_registro guarda quién capturó o modificó el registro.
    - Adherencia  : calculada en la capa de servicio como
                    (date.today() - fecha_inicio_tratamiento).days
                    No se persiste en BD para mantener el valor siempre actualizado.
    """
    __tablename__ = "pacientes"

    curp_paciente: Mapped[str] = mapped_column(String(18), primary_key=True)
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    diagnostico_actual: Mapped[str | None] = mapped_column(Text)
    fecha_inicio_tratamiento: Mapped[date | None] = mapped_column(Date)

    # FK → unidades_medicas
    clues_unidad_adscripcion: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("unidades_medicas.clues", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Soft Delete
    es_activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Auditoría — quién creó/modificó este registro
    id_usuario_registro: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamp automático de creación (lo estampa el motor de BD)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relaciones ORM
    unidad_adscripcion: Mapped["UnidadMedica"] = relationship(back_populates="pacientes")
    usuario_registro: Mapped["Usuario | None"] = relationship(
        back_populates="pacientes_registrados",
        foreign_keys=[id_usuario_registro],
    )
    suministros: Mapped[list["Suministro"]] = relationship(
        back_populates="paciente",
        cascade="all, delete-orphan",
    )

    # ------------------------------------------------------------------
    # Propiedad calculada: Adherencia (días en tratamiento activo)
    # ------------------------------------------------------------------
    @property
    def dias_adherencia(self) -> int | None:
        """
        Días transcurridos desde el inicio del tratamiento hasta hoy.
        Retorna None si fecha_inicio_tratamiento no está registrada.
        """
        if self.fecha_inicio_tratamiento is None:
            return None
        return (date.today() - self.fecha_inicio_tratamiento).days

    def __repr__(self) -> str:
        return f"<Paciente curp={self.curp_paciente!r} nombre={self.nombre_completo!r}>"


# ---------------------------------------------------------------------------
# 5. Suministros (Censo de Asignación de Tratamiento)
# ---------------------------------------------------------------------------
class Suministro(Base):
    """
    Registro de asignación de medicamento a un paciente.

    IMPORTANTE — No es una bitácora diaria de dosis:
        Representa el INICIO de un tratamiento con un medicamento específico.
        fecha_primera_administracion : fecha real en que el paciente recibió la primera dosis.
        fecha_registro_sistema       : timestamp automático de creación/modificación del registro.

    - Soft Delete : es_activo = False cuando se anula por error de captura.
    - Auditoría   : id_usuario_registro identifica quién capturó el dato.
    """
    __tablename__ = "suministros"

    id_suministro: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # FK → pacientes
    curp_paciente: Mapped[str] = mapped_column(
        String(18),
        ForeignKey("pacientes.curp_paciente", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # FK → cat_medicamentos
    clave_cnis_med: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("cat_medicamentos.clave_cnis", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    dosis_administrada: Mapped[str | None] = mapped_column(String(100))

    # Fecha real de primera administración (capturada manualmente)
    fecha_primera_administracion: Mapped[date | None] = mapped_column(Date)

    # Timestamp automático — lo actualiza la BD en cada INSERT/UPDATE
    fecha_registro_sistema: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Auditoría
    id_usuario_registro: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )

    # Soft Delete
    es_activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relaciones ORM
    paciente: Mapped["Paciente"] = relationship(back_populates="suministros")
    medicamento: Mapped["CatMedicamento"] = relationship(back_populates="suministros")
    usuario_registro: Mapped["Usuario | None"] = relationship(
        back_populates="suministros_registrados",
        foreign_keys=[id_usuario_registro],
    )

    def __repr__(self) -> str:
        return (
            f"<Suministro id={self.id_suministro} "
            f"curp={self.curp_paciente!r} "
            f"med={self.clave_cnis_med!r}>"
        )
