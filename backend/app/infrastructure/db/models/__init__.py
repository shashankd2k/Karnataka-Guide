"""
Unified model registry exporting all 16 system ORM entities.
"""

from app.infrastructure.db.models.admin import Admin, AdminRole
from app.infrastructure.db.models.audit import AuditLog, SystemLog
from app.infrastructure.db.models.base import Base
from app.infrastructure.db.models.chat import ChatMessage, ChatSession, SenderType
from app.infrastructure.db.models.chunk import DocumentChunk, Embedding
from app.infrastructure.db.models.document import Document, DocumentStatus
from app.infrastructure.db.models.generation import (
    GenerationLifecycleStatus,
    GenerationStage,
    GenerationStatus,
    KnowledgeGeneration,
)
from app.infrastructure.db.models.system import (
    DeploymentHistory,
    HealthMetric,
    ModelRegistry,
    ModelType,
    SettingValueType,
    SystemSetting,
    TranslationRegistry,
    VoiceProvider,
    VoiceRegistry,
)

__all__ = [
    "Base",
    "Admin",
    "AdminRole",
    "Document",
    "DocumentStatus",
    "KnowledgeGeneration",
    "GenerationLifecycleStatus",
    "GenerationStage",
    "GenerationStatus",
    "DocumentChunk",
    "Embedding",
    "ChatSession",
    "ChatMessage",
    "SenderType",
    "AuditLog",
    "SystemLog",
    "DeploymentHistory",
    "HealthMetric",
    "ModelRegistry",
    "ModelType",
    "VoiceRegistry",
    "VoiceProvider",
    "TranslationRegistry",
    "SystemSetting",
    "SettingValueType",
]
