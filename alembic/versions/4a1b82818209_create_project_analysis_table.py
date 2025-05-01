"""Create project_analysis table

Revision ID: 4a1b82818209
Revises: 17cf91ea65fe
Create Date: 2024-09-19 09:18:48.394883

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4a1b82818209'
down_revision: Union[str, None] = '17cf91ea65fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create project_analysis table
    op.create_table(
        'project_analysis',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer, sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('total_segments', sa.Integer, nullable=False),
        sa.Column('total_words', sa.Integer, nullable=False),
        sa.Column('total_characters', sa.Integer, nullable=False),
        sa.Column('segments_similarity_scores', postgresql.JSON, nullable=False),
        sa.Column('words_similarity_scores', postgresql.JSON, nullable=False),
        sa.Column('characters_similarity_scores', postgresql.JSON, nullable=False)
    )

def downgrade() -> None:
    # Drop project_analysis table
    op.drop_table('project_analysis')
