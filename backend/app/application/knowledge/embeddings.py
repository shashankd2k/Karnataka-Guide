"""
Sentence Transformers embedding engine with singleton process caching and batch inference.
"""

from typing import List, Optional
import structlog

logger = structlog.get_logger(__name__)

# Process-level model cache to avoid duplicate weights loading
_MODEL_CACHE: dict = {}


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """
    Retrieve or initialize the SentenceTransformer model singleton.
    Reuses the in-memory model across all requests and knowledge builds.
    """
    global _MODEL_CACHE
    if model_name not in _MODEL_CACHE:
        logger.info("loading_sentence_transformer_model", model_name=model_name)
        from sentence_transformers import SentenceTransformer

        import os
        from app.core.config import AppProfile, get_settings

        settings = get_settings()
        is_offline = (settings.APP_PROFILE == AppProfile.STANDALONE or os.environ.get("HF_HUB_OFFLINE") == "1")
        if is_offline:
            # Strictly load from local cache; prevent silent online downloads in offline/standalone mode
            model = SentenceTransformer(model_name, local_files_only=True)
            logger.info("sentence_transformer_model_loaded_offline", model_name=model_name)
        else:
            # Attempt local cache first, fall back to online download in dev/setup mode
            try:
                model = SentenceTransformer(model_name, local_files_only=True)
                logger.info("sentence_transformer_model_loaded_offline", model_name=model_name)
            except Exception as e:
                logger.info("downloading_or_loading_sentence_transformer_online", model_name=model_name, reason=str(e))
                model = SentenceTransformer(model_name)
                logger.info("sentence_transformer_model_loaded", model_name=model_name)

        _MODEL_CACHE[model_name] = model

    return _MODEL_CACHE[model_name]


def generate_embeddings(
    texts: List[str],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32,
    expected_dimension: int = 384,
) -> List[List[float]]:
    """
    Generate dense vector embeddings for a list of text strings in batches.
    Validates output dimensionality (strictly 384d for all-MiniLM-L6-v2).
    """
    if not texts:
        return []

    model = get_embedding_model(model_name)
    
    # Generate embeddings with batch processing
    embeddings_np = model.encode(
        sentences=texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings_list: List[List[float]] = embeddings_np.tolist()

    # Dimension and count validation
    if len(embeddings_list) != len(texts):
        raise ValueError(
            f"Embedding count mismatch: expected {len(texts)}, got {len(embeddings_list)}"
        )

    for idx, vec in enumerate(embeddings_list):
        if len(vec) != expected_dimension:
            raise ValueError(
                f"Embedding dimension mismatch at index {idx}: expected {expected_dimension}, got {len(vec)}"
            )

    return embeddings_list
