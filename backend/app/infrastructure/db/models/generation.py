"""
Knowledge generation and generation execution status models.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
import uuid
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.db.models.base import Base


class GenerationLifecycleStatus(str, PyEnum):
    """Immutable knowledge generation lifecycle states."""
    BUILD = "BUILD"
    PARSE = "PARSE"
    CHUNK = "CHUNK"
    EMBED = "EMBED"
    INDEX = "INDEX"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"


class GenerationStage(str, PyEnum):
    """Granular execution stages during knowledge generation."""
    INIT = "INIT"
    EXTRACTION = "EXTRACTION"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    EVALUATION = "EVALUATION"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class KnowledgeGeneration(Base):
    """Immutable, versioned knowledge base generation."""
    __tablename__ = "knowledge_generations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    generation_version: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    status: Mapped[GenerationLifecycleStatus] = mapped_column(
        Enum(GenerationLifecycleStatus),
        nullable=False,
        default=GenerationLifecycleStatus.BUILD,
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    document_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    embedding_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    embedding_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="all-MiniLM-L6-v2",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    created_by_admin_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("admins.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    promoted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class GenerationStatus(Base):
    """Real-time pipeline stage progress and diagnostics."""
    __tablename__ = "generation_status"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    generation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[GenerationStage] = mapped_column(
        Enum(GenerationStage),
        nullable=False,
    )
    progress_pct: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    error_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
