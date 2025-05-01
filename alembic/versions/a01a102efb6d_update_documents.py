"""update documents

Revision ID: a01a102efb6d
Revises: 0f3f2d09c375
Create Date: 2024-10-03 21:23:56.758627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'a01a102efb6d'
down_revision: Union[str, None] = '0f3f2d09c375'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def column_exists(table_name, column_name):
    inspector = inspect(op.get_bind())
    columns = [column['name'] for column in inspector.get_columns(table_name)]
    return column_name in columns

def upgrade():
    with op.batch_alter_table('documents') as batch_op:

        if not column_exists('documents', 'file_size'):
            batch_op.add_column(sa.Column('file_size', sa.Integer))

        if not column_exists('documents', 'upload_date'):
            batch_op.add_column(sa.Column('upload_date', sa.DateTime))

        if not column_exists('documents', 'status'):
            status_enum = sa.Enum('In Progress', 'Completed', 'Reviewed', name='document_status_enum')
            status_enum.create(op.get_bind())
            batch_op.add_column(sa.Column('status', status_enum, server_default='In Progress'))

        if not column_exists('documents', 'version'):
            batch_op.add_column(sa.Column('version', sa.Integer, server_default='1'))

def downgrade():
    pass