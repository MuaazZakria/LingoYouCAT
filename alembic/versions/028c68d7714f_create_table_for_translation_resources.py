"""create table for translation_resources

Revision ID: 028c68d7714f
Revises: c0f2398088fd
Create Date: 2024-10-02 21:59:25.326482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '028c68d7714f'
down_revision: Union[str, None] = 'c0f2398088fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.create_table(
        'translation_resources',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer, sa.ForeignKey('projects.id', ondelete="CASCADE")),
        sa.Column('tmx_file', sa.String(), nullable=False),
        sa.Column('penalty_rules', sa.String(), nullable=True),
        sa.Column('match_thresholds', sa.Float(), nullable=True)
    )
    
    op.create_table(
        'machine_translation',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('engine_name', sa.String(), nullable=False),
        sa.Column('source_language', sa.String(), nullable=False),
        sa.Column('target_language', sa.String(), nullable=False),
        sa.Column('project_id', sa.Integer, sa.ForeignKey('projects.id', ondelete="CASCADE"))
    )

    op.create_table(
        'segment_comments',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('segment_id', sa.Integer, sa.ForeignKey('segments.id', ondelete="CASCADE")),
        sa.Column('comment_text', sa.Text(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('project_id', sa.Integer, sa.ForeignKey('projects.id', ondelete="CASCADE")),
    )


def downgrade():
    op.drop_table('segment_comments')
    op.drop_table('machine_translation')
    op.drop_table('translation_resources')
