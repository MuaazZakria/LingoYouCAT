"""insert language data

Revision ID: a30e6a45097b
Revises: 2b471e9ea6f9
Create Date: 2024-09-12 02:05:56.463709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a30e6a45097b'
down_revision: Union[str, None] = '2b471e9ea6f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO languages (id, code, name, locale)
        VALUES
        (1, 'en', 'English (USA)', 'en-US'),
        (2, 'en', 'English (UK)', 'en-GB'),
        (3, 'fr', 'French (France)', 'fr-FR'),
        (4, 'fr', 'French (Canada)', 'fr-CA'),
        (5, 'es', 'Spanish (Spain)', 'es-ES'),
        (6, 'es', 'Spanish (Mexico)', 'es-MX'),
        (7, 'de', 'German (Germany)', 'de-DE'),
        (8, 'it', 'Italian (Italy)', 'it-IT'),
        (9, 'pt', 'Portuguese (Portugal)', 'pt-PT'),
        (10, 'pt', 'Portuguese (Brazil)', 'pt-BR')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM languages
        WHERE id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        """
    )
