"""
Admin user ORM model and role definitions.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional
import uuid
from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.db.models.base import Base


class AdminRole(str, PyEnum):
    """Administrative RBAC roles."""
    SUPER_ADMIN = "SUPER_ADMIN"
    SITE_CURATOR = "SITE_CURATOR"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class Admin(Base):
    """Administrator account table."""
    __tablename__ = "admins"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole),
        nullable=False,
        default=AdminRole.VIEWER,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
