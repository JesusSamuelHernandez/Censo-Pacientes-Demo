"""Modelos ORM de medicos."""
from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Medico(Base):
    """Profesionales medicos adscritos a unidades medicas."""
    __tablename__ = "medicos"

    id_medico: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cedula_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    nombre_medico: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    cedula: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    curp_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    curp: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    id_puesto: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("cat_puestos.codigo", ondelete="RESTRICT"), nullable=True
    )

    clues_adscripcion: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    es_activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    unidad_adscripcion: Mapped["UnidadMedica"] = relationship(back_populates="medicos")
    puesto: Mapped["CatPuesto | None"] = relationship(back_populates="medicos")
    registros: Mapped[list["Registro"]] = relationship(back_populates="medico")

    def __repr__(self) -> str:
        return f"<Medico id={self.id_medico}>"