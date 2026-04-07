"""initial schema with pgvector

Revision ID: 001
Revises:
Create Date: 2026-04-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('google_id', sa.String(255), unique=True, nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('memory_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )

    op.create_table(
        'memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('gcs_blob_path', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=True),
        sa.Column('domain', sa.String(255), nullable=True),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_memories_user_id', 'memories', ['user_id', 'captured_at'])
    op.create_index('idx_memories_status', 'memories', ['status'])
    op.create_index('idx_memories_domain', 'memories', ['user_id', 'domain'])
    op.create_index('idx_memories_url_user', 'memories', ['user_id', 'url'], unique=True, postgresql_where=sa.text('url IS NOT NULL'))
    op.create_index('idx_memories_hash_user', 'memories', ['user_id', 'file_hash'], unique=True, postgresql_where=sa.text('file_hash IS NOT NULL'))

    op.create_table(
        'memory_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('memories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('embedding', sa.dialects.postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('idx_chunks_user_id', 'memory_chunks', ['user_id'])
    op.create_index('idx_chunks_memory_id', 'memory_chunks', ['memory_id'])

    op.execute("ALTER TABLE memory_chunks ALTER COLUMN embedding TYPE vector(768) USING embedding::vector(768)")
    op.execute("CREATE INDEX idx_chunks_embedding ON memory_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)")

    op.create_table(
        'domain_blocklist',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('idx_blocklist_user_domain', 'domain_blocklist', ['user_id', 'domain'], unique=True)


def downgrade() -> None:
    op.drop_table('domain_blocklist')
    op.drop_table('memory_chunks')
    op.drop_table('memories')
    op.drop_table('users')
