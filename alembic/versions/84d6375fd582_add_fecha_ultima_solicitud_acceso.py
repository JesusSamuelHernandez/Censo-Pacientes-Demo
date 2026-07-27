"""Add fecha_ultima_solicitud_acceso to usuarios.

Soporta la ventana de enfriamiento de /auth/solicitar-acceso (SAST-04): sin
esta columna no hay forma de saber si a una cuenta pendiente ya se le emitió
una contraseña temporal recientemente.

No se aplicó el --autogenerate tal cual: también repite el DROP de
cat_medicamentos.insumo y de los 4 índices de rendimiento ya excluidos en
c67c9a067330 por ser falsos positivos del comparador (existen en la base
pero no están declarados como Index() en los modelos).

Revision ID: 84d6375fd582
Revises: c67c9a067330
Create Date: 2026-07-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "84d6375fd582"
down_revision: Union[str, None] = "c67c9a067330"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("fecha_ultima_solicitud_acceso", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "fecha_ultima_solicitud_acceso")
