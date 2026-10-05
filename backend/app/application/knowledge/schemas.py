"""
Schemas and DTOs for Knowledge Base generation builds, monitoring, promotion, and rollback.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.infrastructure.db.models.generation import (
    GenerationLifecycleStatus,
    GenerationStage,
)


class BuildGenerationRequest(BaseModel):
    """Request payload for triggering a knowledge generation build."""
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific document IDs to include. If omitted, all valid uploaded documents are indexed.",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional human-readable description for this knowledge generation version.",
    )


class GenerationResponse(BaseModel):
    """Knowledge generation summary schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    generation_version: str
    status: GenerationLifecycleStatus
    description: Optional[str] = None
    document_count: int
    chunk_count: int
    embedding_count: int
    embedding_model: str
    is_active: bool
    created_by_admin_id: str
    created_at: datetime
    promoted_at: Optional[datetime] = None


class GenerationStatusResponse(BaseModel):
    """Granular stage progress schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    generation_id: str
    stage: GenerationStage
    progress_pct: int
    message: Optional[str] = None
    error_details: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class GenerationDetailResponse(BaseModel):
    """Detailed generation view including all execution stages."""
    generation: GenerationResponse
    stages: List[GenerationStatusResponse]


class GenerationListResponse(BaseModel):
    """List of knowledge generations."""
    items: List[GenerationResponse]
    total: int


class PromoteRollbackResponse(BaseModel):
    """Response returned upon promoting or rolling back a knowledge generation."""
    message: str
    generation_id: str
    is_active: bool
    promoted_at: Optional[datetime] = None
