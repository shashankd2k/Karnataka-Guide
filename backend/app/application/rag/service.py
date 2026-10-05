"""
RAG Hybrid Retrieval Service orchestrating Dense Vector search, BM25 Keyword search,
Reciprocal Rank Fusion, Cross-Encoder Re-ranking, Noise filtering, and Timing telemetry.
"""

import time
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from app.core.config import get_settings
from app.infrastructure.db.models.generation import KnowledgeGeneration, GenerationLifecycleStatus
from app.application.rag.normalization import normalize_query_for_search
from app.application.rag.dense import retrieve_dense_candidates
from app.application.rag.bm25 import get_or_build_bm25_index
from app.application.rag.fusion import reciprocal_rank_fusion
from app.application.rag.reranker import rerank_candidates
from app.application.rag.filters import filter_noise_chunks, suppress_duplicate_chunks
from app.application.rag.schemas import (
    RetrievalCandidate,
    RetrievalDiagnosticRequest,
    RetrievalDiagnosticResponse,
    TimingMetrics,
)

logger = structlog.get_logger(__name__)


class RAGRetrievalService:
    """Service orchestrating hybrid retrieval across active knowledge base generations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    async def get_active_generation(self) -> Optional[KnowledgeGeneration]:
        """Fetch the current active knowledge generation from MySQL."""
        stmt = (
            select(KnowledgeGeneration)
            .where(
                KnowledgeGeneration.is_active.is_(True),
                KnowledgeGeneration.status == GenerationLifecycleStatus.ACTIVE,
            )
            .order_by(KnowledgeGeneration.promoted_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def retrieve_evidence(
        self,
        request: RetrievalDiagnosticRequest,
    ) -> RetrievalDiagnosticResponse:
        """
        Execute full multi-stage hybrid retrieval for evidence extraction.
        
        Stages:
            1. Query Normalization & Active Generation Lookup
            2. Dense Vector Retrieval (ChromaDB)
            3. Sparse Keyword Retrieval (BM25)
            4. Reciprocal Rank Fusion (RRF k=60)
            5. Cross-Encoder Re-ranking (ms-marco-MiniLM-L-6-v2)
            6. Heuristic Noise & Bibliography Filtering
            7. Near-Duplicate Suppression
        """
        start_total = time.perf_counter()
        notes: List[str] = []

        # 1. Parameter defaults from settings
        dense_k = request.dense_top_k or self.settings.RETRIEVAL_DENSE_TOP_K
        bm25_k = request.bm25_top_k or self.settings.RETRIEVAL_BM25_TOP_K
        rrf_k = self.settings.RETRIEVAL_RRF_K
        rerank_n = request.rerank_candidates or self.settings.RETRIEVAL_RERANK_CANDIDATES
        final_k = request.top_k or self.settings.RETRIEVAL_FINAL_TOP_K

        # Normalize query
        raw_query = request.query.strip()
        normalized_query = normalize_query_for_search(raw_query)

        # Active generation check
        active_gen = await self.get_active_generation()
        if not active_gen:
            total_duration = (time.perf_counter() - start_total) * 1000
            notes.append("No ACTIVE knowledge generation found in database.")
            logger.warning("retrieval_failed_no_active_generation", query=raw_query)
            return RetrievalDiagnosticResponse(
                query=raw_query,
                normalized_query=normalized_query,
                active_generation_id=None,
                active_generation_version=None,
                dense_candidates_count=0,
                bm25_candidates_count=0,
                fused_candidates_count=0,
                final_count=0,
                results=[],
                timings_ms=TimingMetrics(total_ms=round(total_duration, 2)),
                diagnostic_notes=notes,
            )

        gen_id = active_gen.id
        gen_ver = active_gen.generation_version

        # 2. Dense Vector Retrieval
        t_dense_start = time.perf_counter()
        dense_candidates = retrieve_dense_candidates(
            query_text=normalized_query,
            generation_id=gen_id,
            top_k=dense_k,
        )
        dense_duration = (time.perf_counter() - t_dense_start) * 1000

        # 3. Sparse BM25 Retrieval
        t_bm25_start = time.perf_counter()
        bm25_index = await get_or_build_bm25_index(
            generation_id=gen_id,
            session=self.session,
        )
        bm25_candidates = []
        if bm25_index:
            bm25_candidates = bm25_index.query(
                query_text=normalized_query,
                top_k=bm25_k,
            )
        else:
            notes.append(f"BM25 index could not be built for generation {gen_id}.")
        bm25_duration = (time.perf_counter() - t_bm25_start) * 1000

        # 4. Reciprocal Rank Fusion (RRF)
        t_fusion_start = time.perf_counter()
        fused_candidates = reciprocal_rank_fusion(
            dense_candidates=dense_candidates,
            bm25_candidates=bm25_candidates,
            k=rrf_k,
            top_n=rerank_n,
        )
        fusion_duration = (time.perf_counter() - t_fusion_start) * 1000

        # 5. Cross-Encoder Re-ranking
        t_rerank_start = time.perf_counter()
        if request.enable_reranker and fused_candidates:
            scored_candidates = rerank_candidates(
                query_text=raw_query,  # Use raw query for nuanced Cross-Encoder attention
                candidates=fused_candidates,
                model_name=self.settings.CROSS_ENCODER_MODEL,
            )
        else:
            scored_candidates = fused_candidates
        rerank_duration = (time.perf_counter() - t_rerank_start) * 1000

        # 6. Noise & Bibliography Filtering
        processed = scored_candidates
        if request.filter_noise:
            processed = filter_noise_chunks(processed, query_text=raw_query)

        # 7. Duplicate Suppression
        if request.suppress_duplicates:
            processed = suppress_duplicate_chunks(processed)

        # Final top-k selection
        final_results = processed[:final_k]
        total_duration = (time.perf_counter() - start_total) * 1000

        timings = TimingMetrics(
            dense_ms=round(dense_duration, 2),
            bm25_ms=round(bm25_duration, 2),
            fusion_ms=round(fusion_duration, 2),
            rerank_ms=round(rerank_duration, 2),
            total_ms=round(total_duration, 2),
        )

        logger.info(
            "hybrid_retrieval_completed",
            generation_id=gen_id,
            version=gen_ver,
            dense_count=len(dense_candidates),
            bm25_count=len(bm25_candidates),
            fused_count=len(fused_candidates),
            final_count=len(final_results),
            total_ms=timings.total_ms,
        )

        return RetrievalDiagnosticResponse(
            query=raw_query,
            normalized_query=normalized_query,
            active_generation_id=gen_id,
            active_generation_version=gen_ver,
            dense_candidates_count=len(dense_candidates),
            bm25_candidates_count=len(bm25_candidates),
            fused_candidates_count=len(fused_candidates),
            final_count=len(final_results),
            results=final_results,
            timings_ms=timings,
            diagnostic_notes=notes,
        )
