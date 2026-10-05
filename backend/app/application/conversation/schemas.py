"""
Pydantic v2 schemas for Public Tourist Conversational APIs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CreateSessionRequest(BaseModel):
    """Optional request payload for initializing a tourist session."""
    language_code: str = Field(default="kn", max_length=10, description="Preferred language code ('kn' or 'en')")

    model_config = ConfigDict(extra="ignore")


class SessionResponse(BaseModel):
    """Tourist session initialization response."""
    session_uuid: str
    language_code: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatTurnRequest(BaseModel):
    """Tourist message turn request."""
    session_uuid: str = Field(..., description="UUID identifier of the active tourist chat session")
    message: str = Field(..., min_length=1, max_length=1000, description="User question or statement (max 1000 chars)")

    model_config = ConfigDict(extra="ignore")


class CitationItem(BaseModel):
    """Page-level citation metadata grounded in real knowledge corpus."""
    citation_label: str = Field(..., description="Citation marker (e.g. '[1]')")
    source_filename: str = Field(..., description="Original filename of the source document")
    page_number: int = Field(..., description="1-indexed physical page number in the source PDF")
    section_header: Optional[str] = Field(None, description="Section header or chapter title")
    chunk_id: Optional[str] = Field(None, description="UUID of the semantic chunk")
    document_id: Optional[str] = Field(None, description="UUID of the source PDF document")
    generation_id: Optional[str] = Field(None, description="UUID of the knowledge generation")
    reranker_score: Optional[float] = Field(None, description="Cross-Encoder relevance score")

    model_config = ConfigDict(from_attributes=True)


class RetrievalMeta(BaseModel):
    """Summary of the evidence retrieval execution."""
    generation_id: Optional[str] = None
    evidence_count: int = 0
    resolved_query: Optional[str] = None


class ChatTurnResponse(BaseModel):
    """Public tourist conversation response contract."""
    session_uuid: str
    message_id: str
    answer: str
    language: str
    grounded: bool
    citations: List[CitationItem] = Field(default_factory=list)
    retrieval: RetrievalMeta
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageItem(BaseModel):
    """Individual conversation message representation in history."""
    id: str
    sender_type: str
    message_text: str
    detected_language: str
    citations: Optional[List[Dict[str, Any]]] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionHistoryResponse(BaseModel):
    """Paginated conversation history for an anonymous session."""
    session_uuid: str
    language_code: str
    total_messages: int
    messages: List[ChatMessageItem]


class DeleteSessionResponse(BaseModel):
    """Session history deletion confirmation."""
    session_uuid: str
    deleted_messages_count: int
    message: str = "Conversation history cleared successfully."
