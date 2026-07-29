"""Add token_version to usuarios.

Soporta la invalidación de sesión de SAST-05: logout, cambio de contraseña
propio (POST /usuarios/me/cambiar-password), reseteo de contraseña por
SUPER_ADMIN (PATCH /usuarios/{id}) y la rotación de contraseña temporal en
/auth/solicitar-acceso incrementan esta columna, lo que invalida de inmediato
cualquier JWT ya emitido con un token_version anterior.

No se aplicó el --autogenerate tal cual: repite el DROP de
cat_medicamentos.insumo y los 4 índices de rendimiento ya excluidos en
migraciones previas (c67c9a067330, 84d6375fd582) por ser falsos positivos
del comparador.

Revision ID: d793f764fc3b
Revises: 84d6375fd582
Create Date: 2026-07-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d793f764fc3b"
down_revision: Union[str, None] = "84d6375fd582"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("token_version", sa.Integer(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "token_version")
