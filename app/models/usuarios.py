"""Modelos ORM de usuarios."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Usuario(Base):
    """Cuentas de acceso a la plataforma."""
    __tablename__ = "usuarios"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_usuario: Mapped[str | None] = mapped_column(String(150), nullable=True)
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


class UsuarioPreautorizado(Base):
    """Correos institucionales preautorizados para autoservicio."""
    __tablename__ = "usuarios_preautorizados"

    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    rol_nombre: Mapped[str] = mapped_column(String(30), nullable=False)
    clues_unidad_asignada: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("cat_unidades.clues", ondelete="RESTRICT"), nullable=True
    )
    id_entidad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<UsuarioPreautorizado email={self.email!r} rol={self.rol_nombre!r}>"