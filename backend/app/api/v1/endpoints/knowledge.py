"""
Administrative Knowledge Base management endpoints for building, inspecting, promoting, and rolling back generations.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.auth.dependencies import get_current_admin, require_role
from app.application.knowledge.schemas import (
    BuildGenerationRequest,
    GenerationDetailResponse,
    GenerationListResponse,
    GenerationResponse,
    PromoteRollbackResponse,
)
from app.application.knowledge.service import KnowledgeService
from app.infrastructure.db.models.admin import Admin, AdminRole
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/admin/knowledge", tags=["Admin Knowledge Base"])


@router.post(
    "/generations/build",
    response_model=GenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Knowledge Base Generation Build",
    description="Builds an immutable, versioned knowledge generation from uploaded documents using PyMuPDF, SentenceTransformers, and ChromaDB.",
)
async def build_knowledge_generation(
    payload: BuildGenerationRequest,
    current_admin: Admin = Depends(require_role(AdminRole.SUPER_ADMIN, AdminRole.SITE_CURATOR)),
    session: AsyncSession = Depends(get_db_session),
) -> GenerationResponse:
    service = KnowledgeService(session=session)
    generation = await service.build_generation(
        admin_id=current_admin.id,
        document_ids=payload.document_ids,
        description=payload.description,
    )
    return GenerationResponse.model_validate(generation)


@router.get(
    "/generations",
    response_model=GenerationListResponse,
    summary="List Knowledge Generations",
    description="List all knowledge base generations with lifecycle status, document, chunk, and embedding counts.",
)
async def list_knowledge_generations(
    skip: int = Query(default=0, ge=0, description="Offset for pagination"),
    limit: int = Query(default=50, ge=1, le=100, description="Page limit"),
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> GenerationListResponse:
    service = KnowledgeService(session=session)
    return await service.list_generations(skip=skip, limit=limit)


@router.get(
    "/generations/{generation_id}",
    response_model=GenerationDetailResponse,
    summary="Get Knowledge Generation Details & Stages",
    description="Retrieve complete generation summary along with detailed stage execution history and diagnostics.",
)
async def get_knowledge_generation_detail(
    generation_id: str,
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> GenerationDetailResponse:
    service = KnowledgeService(session=session)
    return await service.get_generation_detail(generation_id=generation_id)


@router.post(
    "/generations/{generation_id}/promote",
    response_model=PromoteRollbackResponse,
    summary="Promote Knowledge Generation to Active",
    description="Transactionally promotes a validated knowledge generation to ACTIVE status, deactivating previous active generations.",
)
async def promote_knowledge_generation(
    generation_id: str,
    current_admin: Admin = Depends(require_role(AdminRole.SUPER_ADMIN, AdminRole.SITE_CURATOR)),
    session: AsyncSession = Depends(get_db_session),
) -> PromoteRollbackResponse:
    service = KnowledgeService(session=session)
    return await service.promote_generation(generation_id=generation_id, admin_id=current_admin.id)


@router.post(
    "/generations/{generation_id}/rollback",
    response_model=PromoteRollbackResponse,
    summary="Rollback Knowledge Base to Target Generation",
    description="Transactionally rolls back the active knowledge base to a previous valid generation without re-indexing.",
)
async def rollback_knowledge_generation(
    generation_id: str,
    current_admin: Admin = Depends(require_role(AdminRole.SUPER_ADMIN, AdminRole.SITE_CURATOR)),
    session: AsyncSession = Depends(get_db_session),
) -> PromoteRollbackResponse:
    service = KnowledgeService(session=session)
    return await service.rollback_generation(target_generation_id=generation_id, admin_id=current_admin.id)
