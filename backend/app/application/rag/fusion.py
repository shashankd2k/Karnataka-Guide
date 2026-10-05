"""
Reciprocal Rank Fusion (RRF) for merging dense vector and sparse BM25 candidate rankings.
"""

from typing import Dict, List
from app.application.rag.schemas import RetrievalCandidate


def reciprocal_rank_fusion(
    dense_candidates: List[RetrievalCandidate],
    bm25_candidates: List[RetrievalCandidate],
    k: int = 60,
    top_n: int = 15,
) -> List[RetrievalCandidate]:
    """
    Fuse dense and BM25 candidate lists using standard Reciprocal Rank Fusion.
    
    Formula:
        RRF(d) = sum_{m in {dense, bm25}} (1 / (k + rank_m(d)))
    
    Args:
        dense_candidates: Ranked list from dense vector search.
        bm25_candidates: Ranked list from sparse BM25 search.
        k: Smoothing constant (default: 60).
        top_n: Number of top fused candidates to return.
        
    Returns:
        Combined list of RetrievalCandidate items sorted by RRF score descending.
    """
    # Dictionary mapping chunk_id -> combined candidate
    merged: Dict[str, RetrievalCandidate] = {}
    rrf_scores: Dict[str, float] = {}

    # 1. Process Dense candidates
    for rank_idx, candidate in enumerate(dense_candidates, start=1):
        c_id = candidate.chunk_id
        score_contrib = 1.0 / (k + rank_idx)
        rrf_scores[c_id] = rrf_scores.get(c_id, 0.0) + score_contrib
        
        # Clone candidate
        c_copy = candidate.model_copy()
        c_copy.dense_rank = rank_idx
        merged[c_id] = c_copy

    # 2. Process BM25 candidates
    for rank_idx, candidate in enumerate(bm25_candidates, start=1):
        c_id = candidate.chunk_id
        score_contrib = 1.0 / (k + rank_idx)
        rrf_scores[c_id] = rrf_scores.get(c_id, 0.0) + score_contrib

        if c_id in merged:
            # Update existing dense candidate with BM25 metadata
            merged[c_id].bm25_rank = rank_idx
            merged[c_id].bm25_score = candidate.bm25_score
        else:
            # New candidate present only in BM25
            c_copy = candidate.model_copy()
            c_copy.bm25_rank = rank_idx
            merged[c_id] = c_copy

    # 3. Assign final RRF scores
    fused_list: List[RetrievalCandidate] = []
    for c_id, candidate in merged.items():
        candidate.rrf_score = round(rrf_scores[c_id], 6)
        fused_list.append(candidate)

    # 4. Sort descending by RRF score (tie-break by dense_rank, then bm25_rank)
    fused_list.sort(
        key=lambda c: (
            c.rrf_score or 0.0,
            -(c.dense_rank or 999),
            -(c.bm25_rank or 999),
        ),
        reverse=True,
    )

    # 5. Assign updated final_rank
    for idx, candidate in enumerate(fused_list, start=1):
        candidate.final_rank = idx

    return fused_list[:top_n]
