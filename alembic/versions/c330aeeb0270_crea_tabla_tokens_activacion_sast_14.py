"""crea tabla tokens_activacion (SAST-14)

Sustituye la contraseña temporal reutilizable enviada por correo (alta
manual y autoservicio) por un enlace de activación de un solo uso con TTL
corto. Ver app/services/activacion.py — solo se guarda el hash del token
(app.crypto.hash_token), nunca el token en texto plano.

Revision ID: c330aeeb0270
Revises: c70c254069e2
Create Date: 2026-07-28 18:22:55.125260
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c330aeeb0270'
down_revision: Union[str, None] = 'c70c254069e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tokens_activacion",
        sa.Column("id_token", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "id_usuario",
            sa.Integer(),
            sa.ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_tokens_activacion_id_usuario", "tokens_activacion", ["id_usuario"])
    op.create_index(
        "ix_tokens_activacion_token_hash", "tokens_activacion", ["token_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_tokens_activacion_token_hash", table_name="tokens_activacion")
    op.drop_index("ix_tokens_activacion_id_usuario", table_name="tokens_activacion")
    op.drop_table("tokens_activacion")
