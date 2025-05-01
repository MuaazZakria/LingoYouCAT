"""Create tasks table

Revision ID: 447f19cf61f3
Revises: c1f177ffa9ce
Create Date: 2024-10-08 07:29:07.453572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '447f19cf61f3'
down_revision: Union[str, None] = 'c1f177ffa9ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
# Enum types
tasktype_enum = postgresql.ENUM('translation', 'review', 'quality_assurance', name='tasktype')
prioritylevel_enum = postgresql.ENUM('high', 'medium', 'low', name='prioritylevel')
taskprogress_enum = postgresql.ENUM('not_started', 'in_progress', 'completed', name='taskprogress')

# Migration details
def upgrade():
    # Create tasktype enum
    # tasktype_enum.create(op.get_bind())
    # prioritylevel_enum.create(op.get_bind())
    # taskprogress_enum.create(op.get_bind())

    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('task_type', sa.Enum('translation', 'review', 'quality_assurance', name='tasktype'), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('start_date', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('deadline', sa.DateTime(), nullable=False),
        sa.Column('priority', sa.Enum('high', 'medium', 'low', name='prioritylevel'), default='medium'),
        sa.Column('progress_status', sa.Enum('not_started', 'in_progress', 'completed', name='taskprogress'), default='not_started'),
        sa.Column('assigned_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('depends_on_task_id', sa.Integer(), sa.ForeignKey('tasks.id'), nullable=True)
    )
    op.add_column('documents', sa.Column('task_id', sa.Integer(), sa.ForeignKey('tasks.id')))
    op.add_column('segment_translations', sa.Column('task_id', sa.Integer(), sa.ForeignKey('tasks.id')))



def downgrade():
    op.drop_table('tasks')
    # Drop enums
    tasktype_enum.drop(op.get_bind())
    prioritylevel_enum.drop(op.get_bind())
    taskprogress_enum.drop(op.get_bind())
    op.drop_column('documents', 'task_id')
    op.drop_column('segment_translations', 'task_id')