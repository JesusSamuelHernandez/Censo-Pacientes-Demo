"""
models.py — Definición de tablas ORM (SQLAlchemy) para la App Medicamentos de Alto Costo.

Tablas:
    - CatMedicamentos   : Catálogo maestro de medicamentos (clave CNIS).
    - UnidadMedica      : Establecimientos de salud (CLUES como PK).
    - Usuario           : Cuentas de la plataforma con roles RBAC.
    - Paciente          : Padrón de pacientes en tratamiento.
    - Medico            : Profesionales médicos adscritos a unidades.
    - Receta            : Censo de prescripción de medicamentos por paciente.

Convenciones:
    - Soft Delete        : columna es_activo (Boolean) en Paciente y Receta.
    - Auditoría          : id_usuario_registro (FK → usuarios) en Paciente y Receta.
    - Adherencia         : calculada en capa de endpoint desde la receta activa más reciente
                           como (fecha_actual - receta.fecha_inicio_tratamiento).days.
    - Timestamps auto    : fecha_registro (Paciente) y fecha_registro_sistema (Receta) usan
                           server_default=func.now() para que sea la BD quien estampe la hora.
"""
from datetime import date, datetime
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
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

    # Relación inversa
    recetas: Mapped[list["Receta"]] = relationship(back_populates="medicamento")

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

    # Relaciones inversas
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="unidad_asignada")
    pacientes: Mapped[list["Paciente"]] = relationship(back_populates="unidad_adscripcion")
    medicos: Mapped[list["Medico"]] = relationship(back_populates="unidad_adscripcion")
    recetas: Mapped[list["Receta"]] = relationship(back_populates="unidad")

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

    # FK opcional → cat_unidades (solo para RESPONSABLE_UNIDAD)
    clues_unidad_asignada: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("cat_unidades.clues", ondelete="RESTRICT"), nullable=True
    )
    # Contexto geográfico para ADMIN_ESTATAL
    id_entidad: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Flujo de contraseña temporal: True obliga al usuario a cambiar su contraseña
    # antes de poder usar cualquier otro endpoint.
    debe_cambiar_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Relaciones ORM
    unidad_asignada: Mapped["UnidadMedica | None"] = relationship(back_populates="usuarios")

    # Auditoría
    pacientes_registrados: Mapped[list["Paciente"]] = relationship(
        back_populates="usuario_registro",
        foreign_keys="Paciente.id_usuario_registro",
    )
    recetas_registradas: Mapped[list["Receta"]] = relationship(
        back_populates="usuario_registro",
        foreign_keys="Receta.id_usuario_registro",
    )

    def __repr__(self) -> str:
        return f"<Usuario id={self.id_usuario} email={self.email!r} rol={self.rol_nombre!r}>"


# ---------------------------------------------------------------------------
# 4. Pacientes
# ---------------------------------------------------------------------------
class Paciente(Base):
    """
    Padrón de pacientes en tratamiento con medicamentos de alto costo.

    - PK interna  : id_paciente (int autoincremental) — permite cifrar curp_paciente en el futuro.
    - Soft Delete : es_activo = False (nunca se elimina físicamente).
    - Auditoría   : id_usuario_registro guarda quién capturó o modificó el registro.
    - Adherencia  : calculada en la capa de endpoint desde la receta activa más reciente
                    como (date.today() - receta.fecha_inicio_tratamiento).days.
    """
    __tablename__ = "pacientes"

    id_paciente: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # curp_hash: SHA-256 de la CURP en texto plano. Permite búsquedas y unicidad sin descifrar.
    curp_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # Columnas cifradas con Fernet (LargeBinary almacena los bytes del token cifrado)
    curp_paciente: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nombre_completo: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    diagnostico_actual: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # FK → cat_unidades
    clues_unidad_adscripcion: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="RESTRICT"),
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

    # Timestamp automático de creación
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
    recetas: Mapped[list["Receta"]] = relationship(
        back_populates="paciente",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Paciente curp={self.curp_paciente!r} nombre={self.nombre_completo!r}>"


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
    # cedula_hash: SHA-256 de la cédula. Permite validar duplicados sin descifrar.
    cedula_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # Columnas cifradas con Fernet
    nombre_medico: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    cedula: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # FK → cat_unidades
    clues_adscripcion: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Relaciones ORM
    unidad_adscripcion: Mapped["UnidadMedica"] = relationship(back_populates="medicos")
    recetas: Mapped[list["Receta"]] = relationship(back_populates="medico")

    def __repr__(self) -> str:
        return f"<Medico id={self.id_medico} cedula={self.cedula!r} nombre={self.nombre_medico!r}>"


# ---------------------------------------------------------------------------
# 6. Recetas (Sustituye a Suministros)
# ---------------------------------------------------------------------------
class Receta(Base):
    """
    Registro de prescripción de medicamento a un paciente por un médico.

    - id_receta             : folio de la receta, provisto por el usuario (texto libre).
    - Soft Delete           : es_activo = False cuando se anula por error de captura.
    - Auditoría             : id_usuario_registro identifica quién capturó el dato.
    - Adherencia            : calculada en endpoint como
                              (date.today() - fecha_inicio_tratamiento).days
                              usando la receta activa más reciente del paciente.
    """
    __tablename__ = "recetas"

    id_receta: Mapped[str] = mapped_column(String(50), primary_key=True)

    # FK → medicos
    id_medico: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("medicos.id_medico", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # FK → pacientes
    id_paciente: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pacientes.id_paciente", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # FK → cat_medicamentos
    clave_cnis: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("cat_medicamentos.clave_cnis", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # FK → cat_unidades (unidad donde se genera la receta)
    clues: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    fecha_inicio_tratamiento: Mapped[date | None] = mapped_column(Date)
    fecha_primera_admin: Mapped[date | None] = mapped_column(Date)
    dosis_administrada: Mapped[str | None] = mapped_column(String(100))

    # Timestamp automático
    fecha_registro_sistema: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
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
    medico: Mapped["Medico"] = relationship(back_populates="recetas")
    paciente: Mapped["Paciente"] = relationship(back_populates="recetas")
    medicamento: Mapped["CatMedicamento"] = relationship(back_populates="recetas")
    unidad: Mapped["UnidadMedica"] = relationship(back_populates="recetas")
    usuario_registro: Mapped["Usuario | None"] = relationship(
        back_populates="recetas_registradas",
        foreign_keys=[id_usuario_registro],
    )

    def __repr__(self) -> str:
        return (
            f"<Receta id={self.id_receta!r} "
            f"id_paciente={self.id_paciente!r} "
            f"med={self.clave_cnis!r}>"
        )
