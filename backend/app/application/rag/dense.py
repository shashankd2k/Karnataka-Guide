"""
Dense semantic vector retrieval against active ChromaDB generation collections.
"""

from typing import List, Optional
import structlog
from app.core.config import get_settings
from app.application.knowledge.embeddings import generate_embeddings
from app.application.knowledge.vector_store import (
    get_chroma_client,
    get_or_create_generation_collection,
    get_collection_name,
)
from app.application.rag.schemas import RetrievalCandidate

logger = structlog.get_logger(__name__)


def retrieve_dense_candidates(
    query_text: str,
    generation_id: str,
    top_k: int = 25,
    client=None,
) -> List[RetrievalCandidate]:
    """
    Retrieve top-k dense semantic vector candidates from the active generation ChromaDB collection.
    
    Args:
        query_text: Cleaned user query text.
        generation_id: Active knowledge generation UUID.
        top_k: Maximum number of semantic vector candidates to retrieve.
        client: Optional existing ChromaDB PersistentClient instance.
    
    Returns:
        List of RetrievalCandidate objects ranked by dense semantic similarity.
    """
    if not query_text.strip() or not generation_id:
        return []

    settings = get_settings()
    if client is None:
        client = get_chroma_client(persist_path=settings.resolved_chroma_path)

    collection_name = get_collection_name(generation_id)
    collection = get_or_create_generation_collection(generation_id, client=client)
    total_vectors = collection.count()

    if total_vectors == 0:
        logger.warning(
            "dense_retrieval_empty_collection",
            generation_id=generation_id,
            collection_name=collection_name,
        )
        return []

    # Generate 384-dimensional query embedding using singleton model
    query_vector = generate_embeddings([query_text], model_name=settings.EMBEDDING_MODEL)[0]

    # Query ChromaDB collection
    query_k = min(top_k, total_vectors)
    res = collection.query(
        query_embeddings=[query_vector],
        n_results=query_k,
        include=["documents", "metadatas", "distances"],
    )

    candidates: List[RetrievalCandidate] = []
    if not res or not res.get("ids") or not res["ids"][0]:
        return candidates

    ids = res["ids"][0]
    docs = res["documents"][0] if res.get("documents") else [""] * len(ids)
    metas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(ids)
    distances = res["distances"][0] if res.get("distances") else [0.0] * len(ids)

    for rank_idx, (chunk_id, doc_text, metadata, dist) in enumerate(
        zip(ids, docs, metas, distances), start=1
    ):
        doc_id = str(metadata.get("document_id", ""))
        page_num = int(metadata.get("page_number", 1))
        section = metadata.get("section") or metadata.get("section_title")
        source_filename = str(metadata.get("source_filename") or metadata.get("original_name") or "unknown.pdf")

        # Chroma default cosine distance is in range [0, 2]; similarity = 1 - (dist / 2) or 1 - dist
        dense_score = max(0.0, float(1.0 - dist))

        candidates.append(
            RetrievalCandidate(
                chunk_id=str(chunk_id),
                document_id=doc_id,
                generation_id=generation_id,
                text=doc_text,
                page_number=page_num,
                section=section,
                source_filename=source_filename,
                dense_rank=rank_idx,
                dense_score=round(dense_score, 4),
                final_rank=rank_idx,
                metadata_json=metadata,
            )
        )

    logger.debug(
        "dense_retrieval_completed",
        generation_id=generation_id,
        candidates_count=len(candidates),
        top_k=top_k,
    )
    return candidates
