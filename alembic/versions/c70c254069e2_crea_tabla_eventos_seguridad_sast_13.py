"""crea tabla eventos_seguridad (SAST-13)

Audit trail de seguridad: login/logout, cambios de password/rol, consultas
individuales de PHI, transferencias, exportaciones y accesos denegados. Ver
app/audit.py — la tabla es de solo escritura desde la app (sin endpoints de
UPDATE/DELETE) y nunca debe contener CURP, contraseñas, JWT ni diagnosticos.

Revision ID: c70c254069e2
Revises: 6db7af02f87f
Create Date: 2026-07-28 16:12:34.222251
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c70c254069e2'
down_revision: Union[str, None] = '6db7af02f87f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eventos_seguridad",
        sa.Column("id_evento", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "id_usuario",
            sa.Integer(),
            sa.ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("accion", sa.String(length=50), nullable=False),
        sa.Column("resultado", sa.String(length=20), nullable=False),
        sa.Column("objeto_tipo", sa.String(length=50), nullable=True),
        sa.Column("objeto_id", sa.String(length=50), nullable=True),
        sa.Column("ip_origen", sa.String(length=45), nullable=True),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_eventos_seguridad_id_usuario", "eventos_seguridad", ["id_usuario"])
    op.create_index("ix_eventos_seguridad_accion", "eventos_seguridad", ["accion"])
    op.create_index("ix_eventos_seguridad_fecha", "eventos_seguridad", ["fecha"])


def downgrade() -> None:
    op.drop_index("ix_eventos_seguridad_fecha", table_name="eventos_seguridad")
    op.drop_index("ix_eventos_seguridad_accion", table_name="eventos_seguridad")
    op.drop_index("ix_eventos_seguridad_id_usuario", table_name="eventos_seguridad")
    op.drop_table("eventos_seguridad")
