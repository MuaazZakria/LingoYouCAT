"""Restructure database

Revision ID: 710263fc8ef9
Revises: 9b0c450be50b
Create Date: 2024-09-03 22:58:54.171478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '710263fc8ef9'
down_revision: Union[str, None] = '9b0c450be50b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    if not op.get_bind().engine.dialect.has_table(conn, 'mt_services'):
        op.create_table('mt_services',
        sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('mt_services_id_seq'::regclass)"), autoincrement=True, nullable=False),
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('api_url', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('api_key', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name='mt_services_pkey'),
        postgresql_ignore_search_path=False
        )
    op.execute("""
    INSERT INTO mt_services (id, name, api_url, api_key) 
    VALUES 
    (1, 'Google Translate', 'https://translation.googleapis.com/v2', 'YOUR_GOOGLE_API_KEY_HERE'),
    (2, 'DeepL', 'https://api.deepl.com/v2/translate', 'YOUR_DEEPL_API_KEY_HERE');
    """)
    if not op.get_bind().engine.dialect.has_table(conn, 'languages'):
        op.create_table('languages',
        sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('languages_id_seq'::regclass)"), autoincrement=True, nullable=False),
        sa.Column('code', sa.VARCHAR(length=10), autoincrement=False, nullable=False),
        sa.Column('name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column('locale', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name='languages_pkey'),
        sa.UniqueConstraint('locale', name='languages_locale_key'),
        sa.UniqueConstraint('name', name='languages_name_key'),
        postgresql_ignore_search_path=False
        )
    if not op.get_bind().engine.dialect.has_table(conn, 'projects'):
        op.create_table('projects',
        sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('projects_id_seq'::regclass)"), autoincrement=True, nullable=False),
        sa.Column('id_short', sa.VARCHAR(length=10), autoincrement=False, nullable=True),
        sa.Column('name', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
        sa.Column('id_source_language', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('id_assignee', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('create_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.Column('due_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('id_mt_service', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('term_base', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('translation_memory', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('qa_model', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('status', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
        sa.Column('status_percentage', sa.REAL(), autoincrement=False, nullable=True),
        sa.Column('analysis_wc', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('pretranslate_100', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['id_assignee'], ['users.id'], name='projects_id_assignee_fkey'),
        sa.ForeignKeyConstraint(['id_mt_service'], ['mt_services.id'], name='projects_id_mt_service_fkey'),
        sa.ForeignKeyConstraint(['id_source_language'], ['languages.id'], name='projects_id_source_language_fkey'),
        sa.PrimaryKeyConstraint('id', name='projects_pkey'),
        sa.UniqueConstraint('id_short', name='projects_id_short_key'),
        postgresql_ignore_search_path=False
        )

def downgrade() -> None:
    op.drop_table('projects')
    op.drop_table('mt_services')
    op.drop_table('languages')
