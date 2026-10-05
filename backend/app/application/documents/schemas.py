"""
Schemas and DTOs for administrator PDF document management.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.infrastructure.db.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    """Safe document metadata response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str = Field(..., description="UUID storage filename")
    original_name: str = Field(..., description="Original uploaded filename")
    file_size_bytes: int = Field(..., description="File size in bytes")
    sha256_hash: str = Field(..., description="SHA-256 cryptographic checksum")
    mime_type: str = Field(..., description="Validated MIME type")
    status: DocumentStatus = Field(..., description="Document lifecycle status")
    page_count: int = Field(default=0, description="Page count (populated during Phase 6 parsing)")
    uploaded_by_admin_id: str
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated document list response schema."""
    items: List[DocumentResponse]
    total: int = Field(..., description="Total count of documents")
    skip: int = Field(..., description="Offset pagination skip")
    limit: int = Field(..., description="Limit of items returned")


class DocumentDeleteResponse(BaseModel):
    """Document deletion response schema."""
    message: str = "Document deleted successfully."
    document_id: str
