"""create segments table

Revision ID: 2b471e9ea6f9
Revises: 710263fc8ef9
Create Date: 2024-09-12 00:25:46.239126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2b471e9ea6f9'
down_revision: Union[str, None] = '710263fc8ef9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if not op.get_bind().engine.dialect.has_table(conn, 'status'):
        op.create_table('status',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('name', postgresql.ENUM('NOT_TRANSLATED', 'DRAFT', 'TRANSLATED', 'TRANSLATION_APPROVED', 'SIGN_OFF', 'REJECTED', 'LOCKED', 'PRE_TRANSLATED', name='segmentstatus'), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name='status_pkey'),
        sa.UniqueConstraint('name', name='status_name_key')
        )

    # creating documents for segmentation
    if not op.get_bind().engine.dialect.has_table(conn, 'documents'):
        op.create_table('documents',
        sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('id_project', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('id_source_language', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('filename', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('mime_type', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('encrypted_content', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('chars_per_word', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(['id_project'], ['projects.id'], name='documents_id_project_fkey'),
        sa.ForeignKeyConstraint(['id_source_language'], ['languages.id'], name='documents_id_source_language_fkey'),
        sa.PrimaryKeyConstraint('id', name='documents_pkey')
        )
        op.create_index('ix_documents_id', 'documents', ['id'], unique=False)

    if not op.get_bind().engine.dialect.has_table(conn, 'segments'):
    # creating the segments with documents
        op.create_table('segments',
        sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column('id_project', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('id_document', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('source_text', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('id_source_language', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('id_status', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('comments', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('segment_metadata', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column('qa_flags', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column('segment_history', postgresql.ARRAY(postgresql.JSONB(astext_type=sa.Text())), autoincrement=False, nullable=True),
        sa.Column('reference_materials', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column('locked_status', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('usage_frequency', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('last_used_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['id_document'], ['documents.id'], name='segments_id_document_fkey'),
        sa.ForeignKeyConstraint(['id_project'], ['projects.id'], name='segments_id_project_fkey'),
        sa.ForeignKeyConstraint(['id_source_language'], ['languages.id'], name='segments_id_source_language_fkey'),
        sa.ForeignKeyConstraint(['id_status'], ['status.id'], name='segments_id_status_fkey'),
        sa.PrimaryKeyConstraint('id', name='segments_pkey')
        )
        op.create_index('ix_segments_id', 'segments', ['id'], unique=False)

def downgrade() -> None:
   op.drop_table('segments')
   op.drop_table('documents')
   op.drop_table('status')
