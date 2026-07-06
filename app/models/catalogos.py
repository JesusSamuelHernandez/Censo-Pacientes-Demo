"""Modelos ORM de catalogos."""
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CatDiagnostico(Base):
    """
    Catalogo de diagnosticos clinicos. El diagnostico se asocia a cada
    prescripcion (Registro), no al paciente directamente.
    """
    __tablename__ = "cat_diagnosticos"

    id_diagnostico: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    codigo_cie10: Mapped[str | None] = mapped_column(String(20), nullable=True)
    es_activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    registros: Mapped[list["Registro"]] = relationship(back_populates="diagnostico")

    def __repr__(self) -> str:
        return f"<CatDiagnostico id={self.id_diagnostico!r} nombre={self.nombre!r}>"


class CatPuesto(Base):
    """Catalogo de puestos/especialidades del personal medico."""
    __tablename__ = "cat_puestos"

    codigo: Mapped[str] = mapped_column(String(20), primary_key=True)
    denominacion_puesto: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    es_activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    medicos: Mapped[list["Medico"]] = relationship(back_populates="puesto")

    def __repr__(self) -> str:
        return f"<CatPuesto codigo={self.codigo!r} denominacion={self.denominacion_puesto!r}>"


class CatMedicamento(Base):
    """Catalogo oficial de medicamentos de alto costo identificados por Clave CNIS."""
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


class UnidadMedica(Base):
    """Establecimientos de salud. CLUES es la llave primaria."""
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


class UnidadMedicamento(Base):
    """Relacion entre unidades medicas y medicamentos disponibles."""
    __tablename__ = "unidad_medicamentos"

    clues: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cat_unidades.clues", ondelete="CASCADE"),
        primary_key=True,
    )
    clave_cnis: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("cat_medicamentos.clave_cnis", ondelete="CASCADE"),
        primary_key=True,
    )

    def __repr__(self) -> str:
        return f"<UnidadMedicamento clues={self.clues!r} cnis={self.clave_cnis!r}>"