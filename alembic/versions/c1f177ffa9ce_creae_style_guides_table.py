"""creae style guides table

Revision ID: c1f177ffa9ce
Revises: a01a102efb6d
Create Date: 2024-10-03 21:45:23.546373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1f177ffa9ce'
down_revision: Union[str, None] = 'a01a102efb6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.create_table(
        'style_guides',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer, sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False)
    )

def downgrade():
    op.drop_table('style_guides')
