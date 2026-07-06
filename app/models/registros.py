"""Modelos ORM de registros de prescripcion."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Registro(Base):
    """Registro de prescripcion de medicamento a un paciente por un medico."""
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
    confirmado_mediante: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tratamiento_amparo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    queja_derechos_humanos: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    prescripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    dosis: Mapped[float | None] = mapped_column(Float, nullable=True)
    cantidad: Mapped[float | None] = mapped_column(Float, nullable=True)
    frecuencia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unidad_tiempo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duracion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_medicamento: Mapped[float | None] = mapped_column(Float, nullable=True)

    id_diagnostico: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("cat_diagnosticos.id_diagnostico", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

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
    diagnostico: Mapped["CatDiagnostico | None"] = relationship(back_populates="registros")
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