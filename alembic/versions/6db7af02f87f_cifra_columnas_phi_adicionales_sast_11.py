"""cifra columnas PHI adicionales (SAST-11)

Cifra con Fernet (via EncryptedString/EncryptedDecimal, ver app/crypto.py)
columnas de PHI que quedaban en texto/numero plano: expedientes_paciente.
numero_expediente, reacciones_adversas.comentario, registros.prescripcion,
registros.confirmado_mediante, registros.peso y registros.talla.

Quedan sin cifrar las llaves foraneas que revelan diagnostico/medicamento
(registros.clave_cnis, registros.id_diagnostico): cifrarlas rompería joins,
catalogos e indices. Ese riesgo residual se documenta en app/crypto.py y se
mitiga con privilegios SQL acotados y cifrado a nivel de volumen/backup.

Se implementa como DROP + ADD de columna (no ALTER ... USING) porque, al
momento de esta migracion, expedientes_paciente/reacciones_adversas/registros
estan vacias en todos los entornos conocidos (verificado con SELECT count(*)
antes de escribir esta migracion). Si en el futuro llegan a tener datos antes
de aplicar esta migracion, hay que rehacerla como una migracion de datos que
descifre/cifre fila por fila en vez de reusar este DROP + ADD.

Revision ID: 6db7af02f87f
Revises: d793f764fc3b
Create Date: 2026-07-28 12:57:22.918731
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.crypto import EncryptedDecimal, EncryptedString

revision: str = '6db7af02f87f'
down_revision: Union[str, None] = 'd793f764fc3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("expedientes_paciente", "numero_expediente")
    op.add_column(
        "expedientes_paciente", sa.Column("numero_expediente", EncryptedString(), nullable=False)
    )

    op.drop_column("reacciones_adversas", "comentario")
    op.add_column(
        "reacciones_adversas", sa.Column("comentario", EncryptedString(), nullable=False)
    )

    op.drop_column("registros", "prescripcion")
    op.add_column("registros", sa.Column("prescripcion", EncryptedString(), nullable=True))

    op.drop_column("registros", "confirmado_mediante")
    op.add_column(
        "registros", sa.Column("confirmado_mediante", EncryptedString(), nullable=True)
    )

    op.drop_column("registros", "peso")
    op.add_column("registros", sa.Column("peso", EncryptedDecimal(), nullable=True))

    op.drop_column("registros", "talla")
    op.add_column("registros", sa.Column("talla", EncryptedDecimal(), nullable=True))


def downgrade() -> None:
    op.drop_column("expedientes_paciente", "numero_expediente")
    op.add_column(
        "expedientes_paciente", sa.Column("numero_expediente", sa.String(length=100), nullable=False)
    )

    op.drop_column("reacciones_adversas", "comentario")
    op.add_column("reacciones_adversas", sa.Column("comentario", sa.Text(), nullable=False))

    op.drop_column("registros", "prescripcion")
    op.add_column("registros", sa.Column("prescripcion", sa.Text(), nullable=True))

    op.drop_column("registros", "confirmado_mediante")
    op.add_column(
        "registros", sa.Column("confirmado_mediante", sa.String(length=200), nullable=True)
    )

    op.drop_column("registros", "peso")
    op.add_column("registros", sa.Column("peso", sa.Numeric(5, 2), nullable=True))

    op.drop_column("registros", "talla")
    op.add_column("registros", sa.Column("talla", sa.Numeric(5, 2), nullable=True))
