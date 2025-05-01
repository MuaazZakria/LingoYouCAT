"""insert and update status data

Revision ID: 17cf91ea65fe
Revises: a30e6a45097b
Create Date: 2024-09-12 02:14:18.827289

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '17cf91ea65fe'
down_revision: Union[str, None] = 'a30e6a45097b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO status (id, name)
        VALUES
        (1, 'NOT_TRANSLATED'),
        (2, 'DRAFT'),
        (3, 'TRANSLATED'),
        (4, 'TRANSLATION_APPROVED'),
        (5, 'SIGN_OFF'),
        (6, 'REJECTED'),
        (7, 'LOCKED'),
        (8, 'PRE_TRANSLATED')
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM status
        WHERE id IN (1, 2, 3, 4, 5, 6, 7, 8)
        """
    )
