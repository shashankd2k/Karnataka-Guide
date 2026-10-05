"""
Document ORM model for source PDF files.
"""

from datetime import datetime
from enum import Enum as PyEnum
import uuid
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.db.models.base import Base


class DocumentStatus(str, PyEnum):
    """Lifecycle status of an uploaded PDF document."""
    UPLOADED = "UPLOADED"
    PARSED = "PARSED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class Document(Base):
    """Uploaded PDF document metadata."""
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    original_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="application/pdf",
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    page_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus),
        nullable=False,
        default=DocumentStatus.UPLOADED,
        index=True,
    )
    uploaded_by_admin_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("admins.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
