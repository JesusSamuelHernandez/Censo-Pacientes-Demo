"""Modelos ORM de pacientes y entidades relacionadas."""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.crypto import EncryptedString

class Paciente(Base):
    """Padron de pacientes en tratamiento con medicamentos de alto costo."""
    __tablename__ = "pacientes"

    id_paciente: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    curp_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    curp_paciente: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    nombre_completo: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    diagnostico_actual: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)

    clues_unidad_adscripcion: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    es_activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    motivo_baja: Mapped[str | None] = mapped_column(String(300), nullable=True)

    estatus_evolucion: Mapped[str] = mapped_column(
        String(30), nullable=False, default="Inicia tx", server_default="Inicia tx"
    )
    id_usuario_ultimo_cambio_estatus: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )
    fecha_ultimo_cambio_estatus: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
    expedientes: Mapped[list["ExpedientePaciente"]] = relationship(
        back_populates="paciente",
        cascade="all, delete-orphan",
    )
    reacciones_adversas: Mapped[list["ReaccionAdversa"]] = relationship(
        back_populates="paciente",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Paciente id={self.id_paciente}>"


class ExpedientePaciente(Base):
    """Numero de expediente clinico del paciente en cada unidad medica."""
    __tablename__ = "expedientes_paciente"

    id_paciente: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pacientes.id_paciente", ondelete="CASCADE"),
        primary_key=True,
    )
    clues: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="RESTRICT"),
        primary_key=True,
    )
    numero_expediente: Mapped[str] = mapped_column(String(100), nullable=False)

    paciente: Mapped["Paciente"] = relationship(back_populates="expedientes")
    unidad: Mapped["UnidadMedica"] = relationship()

    def __repr__(self) -> str:
        return f"<ExpedientePaciente paciente={self.id_paciente} clues={self.clues!r}>"


class ReaccionAdversa(Base):
    """Registro de una reaccion adversa a un medicamento reportada para un paciente."""
    __tablename__ = "reacciones_adversas"

    id_reaccion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    )
    comentario: Mapped[str] = mapped_column(Text, nullable=False)
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

    paciente: Mapped["Paciente"] = relationship(back_populates="reacciones_adversas")
    medicamento: Mapped["CatMedicamento"] = relationship()
    usuario_registro: Mapped["Usuario | None"] = relationship()

    def __repr__(self) -> str:
        return f"<ReaccionAdversa id={self.id_reaccion} paciente={self.id_paciente}>"


class NotificacionTransferencia(Base):
    """Registro generado cuando un paciente es transferido entre unidades."""
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