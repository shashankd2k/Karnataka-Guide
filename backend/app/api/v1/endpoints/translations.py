"""
Admin API endpoints for inspection of translation model registries and capabilities.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.dependencies import get_current_admin
from app.domain.ports.translation import ITranslationProvider
from app.infrastructure.db.models.admin import Admin
from app.infrastructure.db.models.system import TranslationRegistry
from app.infrastructure.db.session import get_db_session
from app.infrastructure.translation.nllb import NLLBTranslationProvider

router = APIRouter(prefix="/admin", tags=["Admin Translation Registry"])


class TranslationRegistryItem(BaseModel):
    id: str
    source_lang: str
    target_lang: str
    engine: str
    package_version: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TranslationRegistryResponse(BaseModel):
    provider_engine: str
    provider_healthy: bool
    supported_languages: List[str]
    translations: List[TranslationRegistryItem]


@router.get(
    "/translations",
    response_model=TranslationRegistryResponse,
    status_code=status.HTTP_200_OK,
    summary="List Registered Translation Engines & Pairs",
    description="Returns installed translation models, active language directions, and provider health status.",
)
async def list_translation_registry(
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> TranslationRegistryResponse:
    """
    Fetch active translation registry pairs from MySQL and check provider health.
    """
    provider: ITranslationProvider = NLLBTranslationProvider()
    is_healthy = await provider.check_health()
    supported = provider.get_supported_languages()

    stmt = select(TranslationRegistry).order_by(TranslationRegistry.source_lang)
    result = await session.execute(stmt)
    registry_items = result.scalars().all()

    return TranslationRegistryResponse(
        provider_engine="nllb-200",
        provider_healthy=is_healthy,
        supported_languages=supported,
        translations=[
            TranslationRegistryItem.model_validate(item) for item in registry_items
        ],
    )
