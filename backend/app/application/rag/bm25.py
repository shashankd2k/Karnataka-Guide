"""
Sparse keyword retrieval engine using Okapi BM25 with generation-level caching.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from app.infrastructure.db.models.chunk import DocumentChunk
from app.infrastructure.db.models.document import Document
from app.application.rag.normalization import tokenize_for_bm25
from app.application.rag.schemas import RetrievalCandidate

logger = structlog.get_logger(__name__)


@dataclass
class BM25CorpusItem:
    """Internal lightweight descriptor for an indexed chunk."""
    chunk_id: str
    document_id: str
    generation_id: str
    text: str
    page_number: int
    section: Optional[str]
    source_filename: str
    metadata_json: dict


class BM25GenerationIndex:
    """In-memory Okapi BM25 index for a specific knowledge generation."""

    def __init__(self, generation_id: str, items: List[BM25CorpusItem]):
        self.generation_id = generation_id
        self.items = items
        
        # Tokenize corpus for BM25
        tokenized_corpus = [tokenize_for_bm25(item.text) for item in items]
        self.bm25 = BM25Okapi(tokenized_corpus)
        logger.info(
            "bm25_index_built",
            generation_id=generation_id,
            total_chunks=len(items),
        )

    def query(self, query_text: str, top_k: int = 25) -> List[RetrievalCandidate]:
        """Query the BM25 index and return ranked candidates."""
        tokens = tokenize_for_bm25(query_text)
        if not tokens or not self.items:
            return []

        scores = self.bm25.get_scores(tokens)
        
        # Get top-k indices with non-zero or highest scores
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        candidates: List[RetrievalCandidate] = []
        for rank_idx, idx in enumerate(top_indices, start=1):
            score = float(scores[idx])
            # Only include if score > 0 (or up to min requested if all 0)
            if score <= 0.0 and rank_idx > 1:
                continue

            item = self.items[idx]
            candidates.append(
                RetrievalCandidate(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    generation_id=item.generation_id,
                    text=item.text,
                    page_number=item.page_number,
                    section=item.section,
                    source_filename=item.source_filename,
                    bm25_rank=rank_idx,
                    bm25_score=round(score, 4),
                    final_rank=rank_idx,
                    metadata_json=item.metadata_json,
                )
            )

        return candidates


# Global process-level cache for built BM25 indexes keyed by generation_id
_BM25_CACHE: Dict[str, BM25GenerationIndex] = {}


async def get_or_build_bm25_index(
    generation_id: str,
    session: AsyncSession,
) -> Optional[BM25GenerationIndex]:
    """
    Retrieve an existing in-memory BM25 index or query MySQL to build one.
    """
    global _BM25_CACHE
    if generation_id in _BM25_CACHE:
        return _BM25_CACHE[generation_id]

    # Fetch chunks joined with documents for source filenames
    stmt = (
        select(DocumentChunk, Document.original_name)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(DocumentChunk.generation_id == generation_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        logger.warning("no_chunks_found_for_bm25_indexing", generation_id=generation_id)
        return None

    items: List[BM25CorpusItem] = []
    for chunk, orig_name in rows:
        meta = chunk.metadata_json or {}
        items.append(
            BM25CorpusItem(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                generation_id=chunk.generation_id,
                text=chunk.chunk_text,
                page_number=chunk.page_number,
                section=chunk.section_header,
                source_filename=orig_name or "unknown.pdf",
                metadata_json=meta,
            )
        )

    index = BM25GenerationIndex(generation_id=generation_id, items=items)
    _BM25_CACHE[generation_id] = index
    return index


def clear_bm25_cache():
    """Clear in-memory BM25 indexes (e.g. for testing)."""
    global _BM25_CACHE
    _BM25_CACHE.clear()
