"""update project columns

Revision ID: c0f2398088fd
Revises: 4a1b82818209
Create Date: 2024-10-03 12:46:55.271644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = 'c0f2398088fd'
down_revision: Union[str, None] = '4a1b82818209'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def table_exists(table_name):
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()

def column_exists(table_name, column_name):
    inspector = inspect(op.get_bind())
    columns = [column['name'] for column in inspector.get_columns(table_name)]
    return column_name in columns

def upgrade():

    if table_exists('projects'):
        with op.batch_alter_table('projects') as batch_op:
            if not column_exists('projects', 'client_name'):
                batch_op.add_column(sa.Column('client_name', sa.String(length=255)))

            if not column_exists('projects', 'deadline'):
                batch_op.add_column(sa.Column('deadline', sa.Date, nullable=True))
    else:
    
        status_enum = sa.Enum('Pending', 'In Progress', 'Completed', name='status_enum')
        status_enum.create(op.get_bind()) 
        op.create_table(
            'projects',
            sa.Column('client_name', sa.String(length=255)),
            sa.Column('status', status_enum, nullable=False, server_default='Pending'),
            sa.Column('deadline', sa.Date, nullable=True),
        )

def downgrade():

    if table_exists('projects'):
        with op.batch_alter_table('projects') as batch_op:
            if column_exists('projects', 'client_name'):
                batch_op.drop_column('client_name')
            if column_exists('projects', 'deadline'):
                batch_op.drop_column('deadline')