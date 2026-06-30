"""Initial schema and production indexes.

Revision ID: 20260619_0001
Revises: None
Create Date: 2026-06-19
"""
from typing import Sequence, Union

from alembic import op
from app.models import Base

revision: str = "20260619_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    op.create_index(
        "idx_registros_paciente_activo",
        "registros",
        ["id_paciente", "es_activo"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_registros_clues_activo_fecha",
        "registros",
        ["clues", "es_activo", "fecha_primera_administracion"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_registros_activo_fin_tratamiento",
        "registros",
        ["es_activo", "fecha_fin_tratamiento"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_pacientes_clues_activo",
        "pacientes",
        ["clues_unidad_adscripcion", "es_activo"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("idx_pacientes_clues_activo", table_name="pacientes", if_exists=True)
    op.drop_index("idx_registros_activo_fin_tratamiento", table_name="registros", if_exists=True)
    op.drop_index("idx_registros_clues_activo_fecha", table_name="registros", if_exists=True)
    op.drop_index("idx_registros_paciente_activo", table_name="registros", if_exists=True)
    Base.metadata.drop_all(bind=op.get_bind())
