"""Modelo ORM de tokens de activación de cuenta (SAST-14)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TokenActivacion(Base):
    """
    Token de un solo uso para que una cuenta recién creada (alta manual o
    autoservicio) establezca su propia contraseña, en vez de recibir una
    contraseña temporal reutilizable por correo.

    Se guarda solo `token_hash` (ver app.crypto.hash_token) — el token en
    texto plano no se persiste, solo existe en memoria para el envío del
    correo. `expira_en` le da un TTL corto y `usado_en` lo invalida tras el
    primer uso.
    """
    __tablename__ = "tokens_activacion"

    id_token: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    usuario: Mapped["Usuario"] = relationship()

    def __repr__(self) -> str:
        return f"<TokenActivacion id={self.id_token} usuario={self.id_usuario}>"
