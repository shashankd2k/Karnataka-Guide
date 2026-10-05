"""
Pydantic schemas for RAG retrieval candidates, diagnostic requests, and responses.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RetrievalCandidate(BaseModel):
    """Rich retrieval candidate structure with full multi-stage score and provenance tracking."""
    chunk_id: str
    document_id: str
    generation_id: str
    text: str
    page_number: int = Field(..., description="1-indexed source document page number")
    section: Optional[str] = None
    source_filename: str = Field(..., description="Original filename of the source document")
    
    # Stage-level ranks and scores
    dense_rank: Optional[int] = Field(None, description="1-indexed rank from ChromaDB dense retrieval")
    dense_score: Optional[float] = Field(None, description="Dense cosine distance/similarity score")
    bm25_rank: Optional[int] = Field(None, description="1-indexed rank from BM25 sparse retrieval")
    bm25_score: Optional[float] = Field(None, description="Raw Okapi BM25 score")
    rrf_score: Optional[float] = Field(None, description="Reciprocal Rank Fusion score")
    reranker_score: Optional[float] = Field(None, description="Cross-Encoder relevance logit score")
    final_rank: int = Field(..., description="1-indexed final ranking order")
    
    # Metadata
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class TimingMetrics(BaseModel):
    """Sub-millisecond accurate stage latency measurements in milliseconds."""
    dense_ms: float = Field(0.0, description="Dense retrieval time in ms")
    bm25_ms: float = Field(0.0, description="BM25 retrieval time in ms")
    fusion_ms: float = Field(0.0, description="RRF fusion time in ms")
    rerank_ms: float = Field(0.0, description="Cross-Encoder reranking time in ms")
    total_ms: float = Field(0.0, description="Total end-to-end retrieval time in ms")


class RetrievalDiagnosticRequest(BaseModel):
    """Request payload for admin retrieval diagnostic testing."""
    query: str = Field(..., min_length=1, max_length=1000, description="Tourist query to test retrieval against")
    top_k: Optional[int] = Field(None, ge=1, le=50, description="Final number of evidence chunks to return")
    dense_top_k: Optional[int] = Field(None, ge=1, le=100, description="Top-k dense vector candidates to retrieve")
    bm25_top_k: Optional[int] = Field(None, ge=1, le=100, description="Top-k BM25 keyword candidates to retrieve")
    rerank_candidates: Optional[int] = Field(None, ge=1, le=50, description="Top fused candidates to feed to Cross-Encoder")
    enable_reranker: bool = Field(True, description="Whether to apply Cross-Encoder reranking")
    filter_noise: bool = Field(True, description="Whether to filter out bibliography and TOC noise chunks")
    suppress_duplicates: bool = Field(True, description="Whether to suppress near-duplicate chunks")


class RetrievalDiagnosticResponse(BaseModel):
    """Diagnostic response detailing the full hybrid retrieval pipeline stages and evidence."""
    query: str
    normalized_query: str
    active_generation_id: Optional[str]
    active_generation_version: Optional[str]
    dense_candidates_count: int
    bm25_candidates_count: int
    fused_candidates_count: int
    final_count: int
    results: List[RetrievalCandidate]
    timings_ms: TimingMetrics
    diagnostic_notes: List[str] = Field(default_factory=list)
