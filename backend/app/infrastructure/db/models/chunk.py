"""
Document chunks and vector embedding metadata models.
"""

from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.db.models.base import Base


class DocumentChunk(Base):
    """Extracted and parsed semantic text chunk."""
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    generation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_generations.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    section_header: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    chunk_text: Mapped[str] = mapped_column(
        Text().with_variant(MEDIUMTEXT, "mysql"),
        nullable=False,
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_chunk_gen_doc", "generation_id", "document_id"),
    )


class Embedding(Base):
    """Vector database reference mapping for document chunks."""
    __tablename__ = "embeddings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    vector_db_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="all-MiniLM-L6-v2",
    )
    dimensions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=384,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
