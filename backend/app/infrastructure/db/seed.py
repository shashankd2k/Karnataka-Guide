"""
Idempotent baseline seed data for model, voice, translation registries, and settings.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from app.infrastructure.db.models.system import (
    ModelRegistry,
    ModelType,
    SettingValueType,
    SystemSetting,
    TranslationRegistry,
    VoiceProvider,
    VoiceRegistry,
)

logger = structlog.get_logger("app.db.seed")

# 1. Approved AI Models
APPROVED_MODELS = [
    {
        "model_name": "llama3.1:8b",
        "provider": "ollama",
        "model_type": ModelType.LLM,
        "context_window": 8192,
        "is_default": True,
        "is_active": True,
    },
    {
        "model_name": "mistral:7b",
        "provider": "ollama",
        "model_type": ModelType.LLM,
        "context_window": 8192,
        "is_default": False,
        "is_active": True,
    },
    {
        "model_name": "qwen2.5",
        "provider": "ollama",
        "model_type": ModelType.LLM,
        "context_window": 8192,
        "is_default": False,
        "is_active": True,
    },
    {
        "model_name": "gemma2",
        "provider": "ollama",
        "model_type": ModelType.LLM,
        "context_window": 8192,
        "is_default": False,
        "is_active": True,
    },
    {
        "model_name": "all-MiniLM-L6-v2",
        "provider": "sentence-transformers",
        "model_type": ModelType.EMBEDDING,
        "context_window": 512,
        "is_default": True,
        "is_active": True,
    },
    {
        "model_name": "ms-marco-MiniLM-L-6-v2",
        "provider": "cross-encoder",
        "model_type": ModelType.RERANKER,
        "context_window": 512,
        "is_default": True,
        "is_active": True,
    },
]

# 2. Approved Voices
APPROVED_VOICES = [
    {
        "voice_name": "piper_en_lessac_medium",
        "language_code": "en",
        "provider": VoiceProvider.PIPER,
        "model_path": "storage/models/voices/en/en_US-lessac-medium.onnx",
        "sample_rate": 22050,
        "is_default": True,
    },
    {
        "voice_name": "mms_kn_vits",
        "language_code": "kn",
        "provider": VoiceProvider.MMS_TTS,
        "model_path": "facebook/mms-tts-kan",
        "sample_rate": 16000,
        "is_default": True,
    },
]

# 3. Approved Translation Pairs
APPROVED_TRANSLATIONS = [
    {
        "source_lang": "en",
        "target_lang": "kn",
        "engine": "nllb",
        "package_version": "nllb-200-distilled-600M",
        "is_active": True,
    },
    {
        "source_lang": "kn",
        "target_lang": "en",
        "engine": "nllb",
        "package_version": "nllb-200-distilled-600M",
        "is_active": True,
    },
]

# 4. Default System Settings
DEFAULT_SETTINGS = [
    {
        "setting_key": "strict_grounding_threshold",
        "setting_value": "0.65",
        "value_type": SettingValueType.NUMBER,
        "is_editable": True,
    },
    {
        "setting_key": "default_tourist_language",
        "setting_value": "kn",
        "value_type": SettingValueType.STRING,
        "is_editable": True,
    },
    {
        "setting_key": "enable_voice_synthesis",
        "setting_value": "true",
        "value_type": SettingValueType.BOOLEAN,
        "is_editable": True,
    },
    {
        "setting_key": "max_context_token_budget",
        "setting_value": "4096",
        "value_type": SettingValueType.NUMBER,
        "is_editable": True,
    },
]


async def seed_initial_registry_data(session: AsyncSession) -> None:
    """Idempotently seed the approved models, voices, translations, and settings."""
    logger.info("starting_registry_seed")

    # 1. Models
    for m in APPROVED_MODELS:
        stmt = select(ModelRegistry).where(ModelRegistry.model_name == m["model_name"])
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if not existing:
            session.add(ModelRegistry(**m))

    # 2. Voices
    for v in APPROVED_VOICES:
        stmt = select(VoiceRegistry).where(VoiceRegistry.voice_name == v["voice_name"])
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if not existing:
            session.add(VoiceRegistry(**v))

    # 3. Translations
    for t in APPROVED_TRANSLATIONS:
        stmt = select(TranslationRegistry).where(
            TranslationRegistry.source_lang == t["source_lang"],
            TranslationRegistry.target_lang == t["target_lang"],
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if not existing:
            session.add(TranslationRegistry(**t))

    # 4. Settings
    for s in DEFAULT_SETTINGS:
        stmt = select(SystemSetting).where(SystemSetting.setting_key == s["setting_key"])
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if not existing:
            session.add(SystemSetting(**s))

    await session.flush()
    logger.info("registry_seed_completed")
