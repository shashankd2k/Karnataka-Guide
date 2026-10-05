"""
Consolidated API v1 routing namespace.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    diagnostics,
    documents,
    health,
    knowledge,
    tourist,
    translations,
    voice,
)

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="", tags=["Health"])
api_router.include_router(auth.router, prefix="/admin/auth", tags=["Admin Auth"])
api_router.include_router(documents.router, prefix="/admin/documents", tags=["Admin Documents"])
api_router.include_router(knowledge.router, prefix="", tags=["Admin Knowledge Base"])
api_router.include_router(diagnostics.router, prefix="", tags=["Admin Retrieval Diagnostics"])
api_router.include_router(translations.router, prefix="", tags=["Admin Translation Registry"])
api_router.include_router(tourist.router, prefix="", tags=["Public Tourist Chat"])
api_router.include_router(voice.router, prefix="", tags=["Public Tourist Voice"])
