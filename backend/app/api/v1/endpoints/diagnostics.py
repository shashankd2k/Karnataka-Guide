"""
Administrative RAG retrieval diagnostic and telemetry endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.auth.dependencies import get_current_admin
from app.application.rag.schemas import (
    RetrievalDiagnosticRequest,
    RetrievalDiagnosticResponse,
)
from app.application.rag.service import RAGRetrievalService
from app.infrastructure.db.models.admin import Admin
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/admin", tags=["Admin Retrieval Diagnostics"])


@router.post(
    "/knowledge/retrieval-test",
    response_model=RetrievalDiagnosticResponse,
    status_code=status.HTTP_200_OK,
    summary="Test RAG Hybrid Retrieval",
    description="Executes multi-stage hybrid retrieval (Dense + BM25 + RRF + Cross-Encoder) against the active knowledge generation.",
)
async def test_knowledge_retrieval(
    payload: RetrievalDiagnosticRequest,
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> RetrievalDiagnosticResponse:
    service = RAGRetrievalService(session=session)
    return await service.retrieve_evidence(request=payload)


@router.post(
    "/diagnostics/retrieve",
    response_model=RetrievalDiagnosticResponse,
    status_code=status.HTTP_200_OK,
    summary="Diagnostic Retrieval Query (Alias)",
    description="Alias endpoint for admin retrieval diagnostics.",
)
async def diagnostic_retrieve_alias(
    payload: RetrievalDiagnosticRequest,
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> RetrievalDiagnosticResponse:
    service = RAGRetrievalService(session=session)
    return await service.retrieve_evidence(request=payload)
