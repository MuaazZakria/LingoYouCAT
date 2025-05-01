"""create table for termbase/glosseries

Revision ID: 0f3f2d09c375
Revises: 028c68d7714f
Create Date: 2024-10-04 09:09:03.105443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '0f3f2d09c375'
down_revision: Union[str, None] = '028c68d7714f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

term_status_enum = sa.Enum('approved', 'deprecated', name='term_status')

def table_exists(table_name):
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()

def column_exists(table_name, column_name):
    inspector = inspect(op.get_bind())
    columns = [column['name'] for column in inspector.get_columns(table_name)]
    return column_name in columns

def upgrade():
    table_name = 'termbase'
    term_status_enum.create(op.get_bind(), checkfirst=True)
    
    if not table_exists(table_name):
        op.create_table(
            'termbase',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('term', sa.String(length=255), nullable=False),
            sa.Column('definition', sa.Text),
            sa.Column('source_language', sa.String(length=10), nullable=False),
            sa.Column('target_language', sa.String(length=10), nullable=False),
            sa.Column('status', sa.Enum('approved', 'deprecated', name='term_status'), nullable=False),
            sa.Column('usage_example', sa.Text),
            sa.Column('context_sentence', sa.Text),
            sa.Column('project_id', sa.Integer, sa.ForeignKey('projects.id'), nullable=False),
        )
    else:
        if not column_exists(table_name, 'usage_example'):
            op.add_column(table_name, sa.Column('usage_example', sa.Text))
        if not column_exists(table_name, 'context_sentence'):
            op.add_column(table_name, sa.Column('context_sentence', sa.Text))
        if not column_exists(table_name, 'status'):
            op.add_column(table_name, sa.Column('status', sa.Enum('approved', 'deprecated', name='term_status')))
        if not column_exists(table_name, 'project_id'):
            op.add_column(table_name, sa.Column('project_id', sa.Integer, sa.ForeignKey('projects.id')))

def downgrade():
    table_name = 'termbase'
    
    if table_exists(table_name):
        if column_exists(table_name, 'usage_example'):
            op.drop_column(table_name, 'usage_example')
        if column_exists(table_name, 'context_sentence'):
            op.drop_column(table_name, 'context_sentence')
        if column_exists(table_name, 'status'):
            op.drop_column(table_name, 'status')
        if column_exists(table_name, 'project_id'):
            op.drop_column(table_name, 'project_id')