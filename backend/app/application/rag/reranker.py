"""
Cross-Encoder re-ranking engine with singleton process caching and offline HuggingFace model cache reuse.
"""

from typing import Dict, List, Optional
import structlog
from app.application.rag.schemas import RetrievalCandidate

logger = structlog.get_logger(__name__)

# Process-level singleton cache for CrossEncoder models
_CROSS_ENCODER_CACHE: Dict[str, object] = {}


def get_cross_encoder_model(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    """
    Retrieve or initialize the CrossEncoder model singleton.
    Reuses in-memory model weights across requests and threads.
    """
    global _CROSS_ENCODER_CACHE
    if model_name not in _CROSS_ENCODER_CACHE:
        logger.info("loading_cross_encoder_model", model_name=model_name)
        from sentence_transformers import CrossEncoder

        import os
        from app.core.config import AppProfile, get_settings

        settings = get_settings()
        is_offline = (settings.APP_PROFILE == AppProfile.STANDALONE or os.environ.get("HF_HUB_OFFLINE") == "1")
        if is_offline:
            # Strictly load from local cache; prevent silent online downloads in offline/standalone mode
            model = CrossEncoder(model_name, local_files_only=True)
            logger.info("cross_encoder_loaded_offline", model_name=model_name)
        else:
            # Attempt local cache first, fall back to online download in dev/setup mode
            try:
                model = CrossEncoder(model_name, local_files_only=True)
                logger.info("cross_encoder_loaded_offline", model_name=model_name)
            except Exception as e:
                logger.info("downloading_or_loading_cross_encoder_online", model_name=model_name, reason=str(e))
                model = CrossEncoder(model_name)
                logger.info("cross_encoder_loaded_successfully", model_name=model_name)

        _CROSS_ENCODER_CACHE[model_name] = model

    return _CROSS_ENCODER_CACHE[model_name]


def rerank_candidates(
    query_text: str,
    candidates: List[RetrievalCandidate],
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> List[RetrievalCandidate]:
    """
    Score and re-rank candidate chunks using joint query-document cross-attention.
    
    Args:
        query_text: Cleaned user query text.
        candidates: List of candidate chunks from RRF fusion.
        model_name: Cross-Encoder model identifier.
        
    Returns:
        List of RetrievalCandidate objects sorted by Cross-Encoder relevance score descending.
    """
    if not candidates:
        return []
    if not query_text.strip():
        return candidates

    model = get_cross_encoder_model(model_name)

    # Format input pairs: [[query, text], ...]
    pairs = [[query_text, candidate.text] for candidate in candidates]

    # Predict relevance scores in a single batch
    scores = model.predict(pairs)

    reranked: List[RetrievalCandidate] = []
    for candidate, score in zip(candidates, scores):
        c_copy = candidate.model_copy()
        c_copy.reranker_score = round(float(score), 4)
        reranked.append(c_copy)

    # Sort descending by Cross-Encoder relevance score
    reranked.sort(
        key=lambda c: (
            c.reranker_score if c.reranker_score is not None else -999.0,
            c.rrf_score if c.rrf_score is not None else 0.0,
        ),
        reverse=True,
    )

    # Re-assign final_rank
    for idx, candidate in enumerate(reranked, start=1):
        candidate.final_rank = idx

    logger.debug(
        "cross_encoder_rerank_completed",
        candidates_count=len(reranked),
        top_score=reranked[0].reranker_score if reranked else None,
    )
    return reranked
