"""Modelo ORM del audit trail de seguridad (SAST-13)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EventoSeguridad(Base):
    """Evento de seguridad. Solo INSERT desde la app (sin UPDATE/DELETE expuestos).

    No debe contener CURP, contraseñas, JWT ni diagnosticos: solo
    identificadores internos y metadatos de la operacion (ver app/audit.py).
    """
    __tablename__ = "eventos_seguridad"

    id_evento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    accion: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    objeto_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    objeto_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ip_origen: Mapped[str | None] = mapped_column(String(45), nullable=True)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    usuario: Mapped["Usuario | None"] = relationship()

    def __repr__(self) -> str:
        return f"<EventoSeguridad id={self.id_evento} accion={self.accion!r} usuario={self.id_usuario!r}>"
