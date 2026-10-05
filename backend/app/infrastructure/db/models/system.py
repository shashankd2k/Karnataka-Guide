"""
System deployment, health telemetry, registries, and settings models.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.db.models.base import Base


class DeploymentHistory(Base):
    """Application releases and deployment profile rollouts."""
    __tablename__ = "deployment_history"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    app_profile: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    git_commit: Mapped[Optional[str]] = mapped_column(
        String(40),
        nullable=True,
    )
    deployed_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="SYSTEM",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class HealthMetric(Base):
    """Periodic hardware and subsystem telemetry metrics."""
    __tablename__ = "health_metrics"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    cpu_usage_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    ram_usage_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    disk_usage_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    mysql_healthy: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    chromadb_healthy: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    ollama_healthy: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    whisper_healthy: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    piper_healthy: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    api_latency_p95_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )


class ModelType(str, PyEnum):
    """Registered AI model categories."""
    LLM = "LLM"
    EMBEDDING = "EMBEDDING"
    RERANKER = "RERANKER"


class ModelRegistry(Base):
    """Catalog of approved LLM, embedding, and re-ranking models."""
    __tablename__ = "model_registry"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ollama",
    )
    model_type: Mapped[ModelType] = mapped_column(
        Enum(ModelType),
        nullable=False,
    )
    context_window: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=8192,
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    config_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
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


class VoiceProvider(str, PyEnum):
    """TTS voice synthesis engine providers."""
    PIPER = "PIPER"
    MMS_TTS = "MMS_TTS"
    BROWSER = "BROWSER"
    ESPEAK = "ESPEAK"


class VoiceRegistry(Base):
    """Catalog of speech synthesis voices."""
    __tablename__ = "voice_registry"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    voice_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    language_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    provider: Mapped[VoiceProvider] = mapped_column(
        Enum(VoiceProvider),
        nullable=False,
        default=VoiceProvider.PIPER,
    )
    model_path: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    sample_rate: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=22050,
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TranslationRegistry(Base):
    """Offline translation package registry."""
    __tablename__ = "translation_registry"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    source_lang: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    target_lang: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    engine: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="argos",
    )
    package_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("source_lang", "target_lang", name="uq_lang_pair"),
    )


class SettingValueType(str, PyEnum):
    """Type format of stored system setting."""
    STRING = "STRING"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"


class SystemSetting(Base):
    """Runtime dynamic platform settings."""
    __tablename__ = "system_settings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    setting_key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    setting_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    value_type: Mapped[SettingValueType] = mapped_column(
        Enum(SettingValueType),
        nullable=False,
        default=SettingValueType.STRING,
    )
    is_editable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    updated_by_admin_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
