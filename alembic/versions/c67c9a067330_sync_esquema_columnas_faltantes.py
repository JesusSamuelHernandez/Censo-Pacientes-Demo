"""Sync columnas de modelos que nunca se migraron a la base.

Corrige el desfase entre app/models y el esquema real: medicos.curp/curp_hash/
id_puesto, pacientes.motivo_baja y registros.confirmado_mediante/
tratamiento_amparo/queja_derechos_humanos existen en los modelos SQLAlchemy
desde hace tiempo pero nunca se agregaron a la base con una migracion. Tambien
relaja usuarios.nombre_usuario a nullable, como ya lo define el modelo.

No se generó con --autogenerate tal cual: ese diff también proponía
eliminar cat_medicamentos.insumo (columna ya migrada en 20260708_0002, con
datos potenciales) y cuatro índices de rendimiento (idx_pacientes_clues_activo,
idx_registros_activo_fin_tratamiento, idx_registros_clues_activo_fecha,
idx_registros_paciente_activo) que sí existen en la base pero no están
declarados como Index() en los modelos — son falsos positivos del comparador
de Alembic, no cambios reales, y se excluyeron a propósito.

Revision ID: c67c9a067330
Revises: 20260708_0002
Create Date: 2026-07-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.crypto import EncryptedString

revision: str = "c67c9a067330"
down_revision: Union[str, None] = "20260708_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("medicos", sa.Column("curp_hash", sa.String(length=64), nullable=True))
    op.add_column("medicos", sa.Column("curp", EncryptedString(), nullable=True))
    op.add_column("medicos", sa.Column("id_puesto", sa.String(length=20), nullable=True))
    op.create_index(op.f("ix_medicos_curp_hash"), "medicos", ["curp_hash"], unique=True)
    op.create_foreign_key(
        "fk_medicos_id_puesto_cat_puestos",
        "medicos",
        "cat_puestos",
        ["id_puesto"],
        ["codigo"],
        ondelete="RESTRICT",
    )

    op.add_column("pacientes", sa.Column("motivo_baja", sa.String(length=300), nullable=True))

    op.add_column("registros", sa.Column("confirmado_mediante", sa.String(length=200), nullable=True))
    op.add_column(
        "registros",
        sa.Column("tratamiento_amparo", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "registros",
        sa.Column("queja_derechos_humanos", sa.Boolean(), server_default="false", nullable=False),
    )

    op.alter_column("usuarios", "nombre_usuario", existing_type=sa.String(length=150), nullable=True)


def downgrade() -> None:
    op.alter_column("usuarios", "nombre_usuario", existing_type=sa.String(length=150), nullable=False)

    op.drop_column("registros", "queja_derechos_humanos")
    op.drop_column("registros", "tratamiento_amparo")
    op.drop_column("registros", "confirmado_mediante")

    op.drop_column("pacientes", "motivo_baja")

    op.drop_constraint("fk_medicos_id_puesto_cat_puestos", "medicos", type_="foreignkey")
    op.drop_index(op.f("ix_medicos_curp_hash"), table_name="medicos")
    op.drop_column("medicos", "id_puesto")
    op.drop_column("medicos", "curp")
    op.drop_column("medicos", "curp_hash")
