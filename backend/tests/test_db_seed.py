"""
Unit tests for deterministic and idempotent registry seed data.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.infrastructure.db.models import (
    Base,
    ModelRegistry,
    SystemSetting,
    TranslationRegistry,
    VoiceRegistry,
)
from app.infrastructure.db.seed import (
    APPROVED_MODELS,
    APPROVED_TRANSLATIONS,
    APPROVED_VOICES,
    DEFAULT_SETTINGS,
    seed_initial_registry_data,
)


@pytest.fixture
async def memory_db_session():
    """Async session for in-memory SQLite (used exclusively for isolated model seed unit tests)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_seed_initial_registry_data_populates_all_defaults(memory_db_session: AsyncSession):
    """Verify seed function inserts all approved models, voices, translations, and settings."""
    await seed_initial_registry_data(memory_db_session)
    await memory_db_session.commit()

    # Verify models
    models = (await memory_db_session.execute(Base.metadata.tables["model_registry"].select())).fetchall()
    assert len(models) == len(APPROVED_MODELS)

    # Verify voices
    voices = (await memory_db_session.execute(Base.metadata.tables["voice_registry"].select())).fetchall()
    assert len(voices) == len(APPROVED_VOICES)

    # Verify translations
    translations = (await memory_db_session.execute(Base.metadata.tables["translation_registry"].select())).fetchall()
    assert len(translations) == len(APPROVED_TRANSLATIONS)

    # Verify settings
    settings = (await memory_db_session.execute(Base.metadata.tables["system_settings"].select())).fetchall()
    assert len(settings) == len(DEFAULT_SETTINGS)


@pytest.mark.asyncio
async def test_seed_initial_registry_data_is_idempotent(memory_db_session: AsyncSession):
    """Verify running seed multiple times does not produce duplicate records."""
    await seed_initial_registry_data(memory_db_session)
    await memory_db_session.commit()

    # Re-run seed on existing data
    await seed_initial_registry_data(memory_db_session)
    await memory_db_session.commit()

    models = (await memory_db_session.execute(Base.metadata.tables["model_registry"].select())).fetchall()
    assert len(models) == len(APPROVED_MODELS)
