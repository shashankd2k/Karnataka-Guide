"""0001_initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-08-26 23:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Admins
    op.create_table(
        'admins',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('SUPER_ADMIN', 'SITE_CURATOR', 'OPERATOR', 'VIEWER', name='adminrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_admin_username', 'admins', ['username'], unique=True)
    op.create_index('idx_admin_email', 'admins', ['email'], unique=True)
    op.create_index('idx_admin_role', 'admins', ['role'], unique=False)

    # 2. Documents
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('UPLOADED', 'PARSED', 'PROCESSED', 'FAILED', name='documentstatus'), nullable=False),
        sa.Column('uploaded_by_admin_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['uploaded_by_admin_id'], ['admins.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_doc_hash', 'documents', ['sha256_hash'], unique=True)
    op.create_index('idx_doc_status', 'documents', ['status'], unique=False)

    # 3. Knowledge Generations
    op.create_table(
        'knowledge_generations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('generation_version', sa.String(length=50), nullable=False),
        sa.Column('status', sa.Enum('BUILD', 'PARSE', 'CHUNK', 'EMBED', 'INDEX', 'VALIDATED', 'ACTIVE', 'ARCHIVED', 'FAILED', name='generationlifecyclestatus'), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('document_count', sa.Integer(), nullable=False),
        sa.Column('chunk_count', sa.Integer(), nullable=False),
        sa.Column('embedding_count', sa.Integer(), nullable=False),
        sa.Column('embedding_model', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by_admin_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('promoted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_admin_id'], ['admins.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_gen_version', 'knowledge_generations', ['generation_version'], unique=True)
    op.create_index('idx_gen_active', 'knowledge_generations', ['is_active'], unique=False)

    # 4. Generation Status
    op.create_table(
        'generation_status',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('generation_id', sa.String(length=36), nullable=False),
        sa.Column('stage', sa.Enum('INIT', 'EXTRACTION', 'CHUNKING', 'EMBEDDING', 'INDEXING', 'EVALUATION', 'COMPLETED', 'ERROR', name='generationstage'), nullable=False),
        sa.Column('progress_pct', sa.Integer(), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['generation_id'], ['knowledge_generations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_status_gen', 'generation_status', ['generation_id'], unique=False)

    # 5. Document Chunks
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('generation_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('section_header', sa.String(length=255), nullable=True),
        sa.Column('chunk_text', sa.Text().with_variant(mysql.MEDIUMTEXT(), 'mysql'), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['generation_id'], ['knowledge_generations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_chunk_page', 'document_chunks', ['page_number'], unique=False)
    op.create_index('idx_chunk_gen_doc', 'document_chunks', ['generation_id', 'document_id'], unique=False)

    # 6. Embeddings
    op.create_table(
        'embeddings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('chunk_id', sa.String(length=36), nullable=False),
        sa.Column('vector_db_id', sa.String(length=100), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('dimensions', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['chunk_id'], ['document_chunks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chunk_id'),
    )
    op.create_index('idx_emb_vector_id', 'embeddings', ['vector_db_id'], unique=False)

    # 7. Chat Sessions
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_uuid', sa.String(length=64), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('client_ip_hash', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_session_uuid', 'chat_sessions', ['session_uuid'], unique=True)
    op.create_index('idx_session_lang', 'chat_sessions', ['language_code'], unique=False)

    # 8. Chat Messages
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('sender_type', sa.Enum('USER', 'ASSISTANT', 'SYSTEM', name='sendertype'), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('detected_language', sa.String(length=10), nullable=False),
        sa.Column('audio_url', sa.String(length=500), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('citations_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_msg_session', 'chat_messages', ['session_id'], unique=False)
    op.create_index('idx_msg_created', 'chat_messages', ['created_at'], unique=False)

    # 9. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('admin_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('details_json', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_audit_admin', 'audit_logs', ['admin_id'], unique=False)
    op.create_index('idx_audit_action', 'audit_logs', ['action'], unique=False)

    # 10. System Logs
    op.create_table(
        'system_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('log_level', sa.String(length=20), nullable=False),
        sa.Column('module', sa.String(length=100), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('context_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_log_level', 'system_logs', ['log_level'], unique=False)
    op.create_index('idx_log_module', 'system_logs', ['module'], unique=False)

    # 11. Deployment History
    op.create_table(
        'deployment_history',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('app_profile', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('git_commit', sa.String(length=40), nullable=True),
        sa.Column('deployed_by', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('deployed_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # 12. Health Metrics
    op.create_table(
        'health_metrics',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('cpu_usage_pct', sa.Float(), nullable=False),
        sa.Column('ram_usage_pct', sa.Float(), nullable=False),
        sa.Column('disk_usage_pct', sa.Float(), nullable=False),
        sa.Column('mysql_healthy', sa.Boolean(), nullable=False),
        sa.Column('chromadb_healthy', sa.Boolean(), nullable=False),
        sa.Column('ollama_healthy', sa.Boolean(), nullable=False),
        sa.Column('whisper_healthy', sa.Boolean(), nullable=False),
        sa.Column('piper_healthy', sa.Boolean(), nullable=False),
        sa.Column('api_latency_p95_ms', sa.Float(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_health_recorded', 'health_metrics', ['recorded_at'], unique=False)

    # 13. Model Registry
    op.create_table(
        'model_registry',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model_type', sa.Enum('LLM', 'EMBEDDING', 'RERANKER', name='modeltype'), nullable=False),
        sa.Column('context_window', sa.Integer(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('config_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_name'),
    )

    # 14. Voice Registry
    op.create_table(
        'voice_registry',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('voice_name', sa.String(length=100), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('provider', sa.Enum('PIPER', 'BROWSER', 'ESPEAK', name='voiceprovider'), nullable=False),
        sa.Column('model_path', sa.String(length=255), nullable=True),
        sa.Column('sample_rate', sa.Integer(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('voice_name'),
    )

    # 15. Translation Registry
    op.create_table(
        'translation_registry',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source_lang', sa.String(length=10), nullable=False),
        sa.Column('target_lang', sa.String(length=10), nullable=False),
        sa.Column('engine', sa.String(length=50), nullable=False),
        sa.Column('package_version', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_lang', 'target_lang', name='uq_lang_pair'),
    )

    # 16. System Settings
    op.create_table(
        'system_settings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('setting_key', sa.String(length=100), nullable=False),
        sa.Column('setting_value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.Enum('STRING', 'NUMBER', 'BOOLEAN', 'JSON', name='settingvaluetype'), nullable=False),
        sa.Column('is_editable', sa.Boolean(), nullable=False),
        sa.Column('updated_by_admin_id', sa.String(length=36), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['updated_by_admin_id'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('setting_key'),
    )


def downgrade() -> None:
    op.drop_table('system_settings')
    op.drop_table('translation_registry')
    op.drop_table('voice_registry')
    op.drop_table('model_registry')
    op.drop_table('health_metrics')
    op.drop_table('deployment_history')
    op.drop_table('system_logs')
    op.drop_table('audit_logs')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_table('embeddings')
    op.drop_table('document_chunks')
    op.drop_table('generation_status')
    op.drop_table('knowledge_generations')
    op.drop_table('documents')
    op.drop_table('admins')
