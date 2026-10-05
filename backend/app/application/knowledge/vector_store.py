"""
ChromaDB persistent vector store adapter with collection-per-generation partitioning.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog
from app.core.config import get_settings

logger = structlog.get_logger(__name__)

# Process-level persistent client singleton
_CHROMA_CLIENT: Optional[Any] = None


def get_collection_name(generation_id: str) -> str:
    """Generate a valid, deterministic Chroma collection name from generation UUID."""
    sanitized_id = generation_id.replace("-", "_")
    return f"gen_{sanitized_id}"


def get_chroma_client(persist_path: Optional[Path] = None):
    """
    Get or create the persistent ChromaDB client anchored to the configured storage path.
    Custom persist_paths (e.g. in tests) return isolated client instances without polluting the global singleton.
    """
    global _CHROMA_CLIENT
    if persist_path is not None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        persist_path.mkdir(parents=True, exist_ok=True)
        logger.info("initializing_custom_chromadb_client", path=str(persist_path))
        return chromadb.PersistentClient(
            path=str(persist_path),
            settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True),
        )

    if _CHROMA_CLIENT is None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        settings = get_settings()
        target_path = settings.resolved_chroma_path
        target_path.mkdir(parents=True, exist_ok=True)

        logger.info("initializing_chromadb_client", path=str(target_path))
        _CHROMA_CLIENT = chromadb.PersistentClient(
            path=str(target_path),
            settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True),
        )

    return _CHROMA_CLIENT


def get_or_create_generation_collection(generation_id: str, client=None):
    """Create or retrieve isolated Chroma collection for a specific knowledge generation."""
    c = client or get_chroma_client()
    col_name = get_collection_name(generation_id)
    return c.get_or_create_collection(
        name=col_name,
        metadata={"generation_id": generation_id, "hnsw:space": "cosine"},
    )


def index_chunks_into_chroma(
    generation_id: str,
    chunk_ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    batch_size: int = 200,
    client=None,
) -> int:
    """
    Index chunk vectors, raw text, and metadata mappings into ChromaDB in batches.
    Returns total number of items indexed.
    """
    if not chunk_ids:
        return 0

    collection = get_or_create_generation_collection(generation_id, client=client)

    # Sanitize metadatas for Chroma (values must be str, int, float, or bool)
    sanitized_metadatas: List[Dict[str, Any]] = []
    for m in metadatas:
        clean_m: Dict[str, Any] = {}
        for k, v in m.items():
            if isinstance(v, (str, int, float, bool)):
                clean_m[k] = v
            elif v is None:
                clean_m[k] = ""
            else:
                clean_m[k] = str(v)
        sanitized_metadatas.append(clean_m)

    total_chunks = len(chunk_ids)
    for start_idx in range(0, total_chunks, batch_size):
        end_idx = min(start_idx + batch_size, total_chunks)
        collection.add(
            ids=chunk_ids[start_idx:end_idx],
            embeddings=embeddings[start_idx:end_idx],
            documents=documents[start_idx:end_idx],
            metadatas=sanitized_metadatas[start_idx:end_idx],
        )

    indexed_count = collection.count()
    logger.info(
        "chroma_indexing_completed",
        generation_id=generation_id,
        collection=get_collection_name(generation_id),
        count=indexed_count,
    )
    return indexed_count


def get_generation_collection_count(generation_id: str, client=None) -> int:
    """Get the current item count in a generation collection."""
    c = client or get_chroma_client()
    col_name = get_collection_name(generation_id)
    try:
        col = c.get_collection(name=col_name)
        return col.count()
    except Exception:
        return 0


def delete_generation_collection(generation_id: str, client=None) -> bool:
    """Delete a Chroma collection for a discarded/cleaned generation."""
    c = client or get_chroma_client()
    col_name = get_collection_name(generation_id)
    try:
        c.delete_collection(name=col_name)
        logger.info("chroma_collection_deleted", collection=col_name)
        return True
    except Exception as e:
        logger.warning("chroma_collection_delete_failed", collection=col_name, error=str(e))
        return False
