"""
Unit tests verifying SQLAlchemy ORM metadata and all 16 system tables.
"""

from app.infrastructure.db.models import Base

EXPECTED_TABLES = {
    "admins",
    "documents",
    "knowledge_generations",
    "generation_status",
    "document_chunks",
    "embeddings",
    "chat_sessions",
    "chat_messages",
    "audit_logs",
    "system_logs",
    "deployment_history",
    "health_metrics",
    "model_registry",
    "voice_registry",
    "translation_registry",
    "system_settings",
}


def test_all_16_tables_registered_in_metadata():
    """Verify that all 16 approved tables exist in SQLAlchemy Declarative Base metadata."""
    registered_tables = set(Base.metadata.tables.keys())
    assert registered_tables == EXPECTED_TABLES
    assert len(registered_tables) == 16


def test_primary_keys_defined_on_all_tables():
    """Verify every table has a defined primary key."""
    for table_name, table in Base.metadata.tables.items():
        assert len(table.primary_key.columns) >= 1, f"Table '{table_name}' is missing a primary key."


def test_foreign_key_relationships():
    """Verify key foreign key cascade and constraint definitions."""
    tables = Base.metadata.tables

    # documents.uploaded_by_admin_id -> admins.id
    doc_fks = list(tables["documents"].foreign_keys)
    assert any(fk.target_fullname == "admins.id" for fk in doc_fks)

    # generation_status.generation_id -> knowledge_generations.id (CASCADE)
    gen_status_fks = list(tables["generation_status"].foreign_keys)
    assert any(fk.target_fullname == "knowledge_generations.id" and fk.ondelete == "CASCADE" for fk in gen_status_fks)

    # document_chunks -> knowledge_generations.id & documents.id
    chunk_fks = list(tables["document_chunks"].foreign_keys)
    assert any(fk.target_fullname == "knowledge_generations.id" for fk in chunk_fks)
    assert any(fk.target_fullname == "documents.id" for fk in chunk_fks)

    # embeddings.chunk_id -> document_chunks.id (CASCADE)
    emb_fks = list(tables["embeddings"].foreign_keys)
    assert any(fk.target_fullname == "document_chunks.id" and fk.ondelete == "CASCADE" for fk in emb_fks)

    # chat_messages.session_id -> chat_sessions.id (CASCADE)
    msg_fks = list(tables["chat_messages"].foreign_keys)
    assert any(fk.target_fullname == "chat_sessions.id" and fk.ondelete == "CASCADE" for fk in msg_fks)


def test_unique_constraints_and_indexes():
    """Verify essential unique constraints and indexes."""
    tables = Base.metadata.tables

    # Admins unique username and email
    admin_cols = {c.name: c for c in tables["admins"].columns}
    assert admin_cols["username"].unique is True
    assert admin_cols["email"].unique is True

    # Documents unique sha256_hash
    doc_cols = {c.name: c for c in tables["documents"].columns}
    assert doc_cols["sha256_hash"].unique is True

    # Knowledge generations unique version
    gen_cols = {c.name: c for c in tables["knowledge_generations"].columns}
    assert gen_cols["generation_version"].unique is True

    # Translation registry unique (source_lang, target_lang)
    trans_table = tables["translation_registry"]
    trans_uq = [c for c in trans_table.constraints if getattr(c, "name", None) == "uq_lang_pair"]
    assert len(trans_uq) == 1
