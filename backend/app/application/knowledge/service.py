"""
Knowledge base orchestration service managing build, extraction, semantic chunking,
embedding generation, ChromaDB indexing, validation, promotion, and rollback.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from app.application.knowledge.chunker import chunk_extracted_document
from app.application.knowledge.embeddings import generate_embeddings
from app.application.knowledge.extractor import extract_pdf_document
from app.application.knowledge.schemas import (
    GenerationDetailResponse,
    GenerationListResponse,
    GenerationResponse,
    GenerationStatusResponse,
    PromoteRollbackResponse,
)
from app.application.knowledge.vector_store import (
    get_generation_collection_count,
    index_chunks_into_chroma,
)
from app.core.config import Settings, get_settings
from app.core.errors import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.infrastructure.db.models.audit import AuditLog
from app.infrastructure.db.models.chunk import DocumentChunk, Embedding
from app.infrastructure.db.models.document import Document
from app.infrastructure.db.models.generation import (
    GenerationLifecycleStatus,
    GenerationStage,
    GenerationStatus,
    KnowledgeGeneration,
)

logger = structlog.get_logger(__name__)


async def _log_knowledge_audit(
    session: AsyncSession,
    admin_id: str,
    action: str,
    generation_id: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Record a security audit log event for knowledge base lifecycle actions."""
    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        admin_id=admin_id,
        action=action,
        resource_type="KNOWLEDGE_GENERATION",
        resource_id=generation_id,
        details_json=details or {},
    )
    session.add(audit_entry)


class KnowledgeService:
    """Orchestration service for knowledge base building and lifecycle management."""

    def __init__(self, session: AsyncSession, settings: Optional[Settings] = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    async def build_generation(
        self,
        admin_id: str,
        document_ids: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> KnowledgeGeneration:
        """
        Execute full knowledge base generation pipeline:
        1. Select source documents
        2. PyMuPDF extraction & conservative normalization
        3. Semantic chunking preserving page provenance
        4. SentenceTransformer 384d embedding generation
        5. ChromaDB persistent collection indexing
        6. Comprehensive validation
        7. Status transition to VALIDATED
        """
        # 1. Fetch eligible documents
        query = select(Document)
        if document_ids:
            query = query.where(Document.id.in_(document_ids))
        result = await self.session.execute(query)
        documents = result.scalars().all()

        if not documents:
            raise BadRequestException("No valid uploaded documents found to build knowledge generation.")

        # 2. Create KnowledgeGeneration record
        generation_id = str(uuid.uuid4())
        version_tag = f"v_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{generation_id[:6]}"

        generation = KnowledgeGeneration(
            id=generation_id,
            generation_version=version_tag,
            status=GenerationLifecycleStatus.BUILD,
            description=description or f"Knowledge build from {len(documents)} document(s)",
            document_count=len(documents),
            chunk_count=0,
            embedding_count=0,
            embedding_model=self.settings.EMBEDDING_MODEL,
            is_active=False,
            created_by_admin_id=admin_id,
        )
        self.session.add(generation)
        await self.session.flush()

        init_status = GenerationStatus(
            id=str(uuid.uuid4()),
            generation_id=generation_id,
            stage=GenerationStage.INIT,
            progress_pct=5,
            message=f"Build initialized for {len(documents)} document(s).",
        )
        self.session.add(init_status)
        await _log_knowledge_audit(
            self.session,
            admin_id=admin_id,
            action="KNOWLEDGE_BUILD_STARTED",
            generation_id=generation_id,
            details={"version": version_tag, "document_count": len(documents)},
        )
        await self.session.commit()

        storage_root = self.settings.resolved_storage_path

        try:
            # ================= STAGE 1: EXTRACTION =================
            generation.status = GenerationLifecycleStatus.PARSE
            extract_status = GenerationStatus(
                id=str(uuid.uuid4()),
                generation_id=generation_id,
                stage=GenerationStage.EXTRACTION,
                progress_pct=20,
                message=f"Extracting text with PyMuPDF from {len(documents)} documents.",
            )
            self.session.add(extract_status)
            await self.session.commit()

            extracted_docs = []
            for doc in documents:
                file_path = storage_root / doc.filename
                extracted = extract_pdf_document(
                    file_path=file_path,
                    document_id=doc.id,
                    original_name=doc.original_name,
                )
                extracted_docs.append(extracted)

            extract_status.completed_at = datetime.now(timezone.utc)
            extract_status.progress_pct = 35
            extract_status.message = f"Extracted {sum(len(d.pages) for d in extracted_docs)} pages."
            await self.session.commit()

            # ================= STAGE 2: CHUNKING =================
            generation.status = GenerationLifecycleStatus.CHUNK
            chunk_status = GenerationStatus(
                id=str(uuid.uuid4()),
                generation_id=generation_id,
                stage=GenerationStage.CHUNKING,
                progress_pct=40,
                message="Creating semantic chunks preserving page numbers and paragraph boundaries.",
            )
            self.session.add(chunk_status)
            await self.session.commit()

            all_chunk_payloads = []
            for ext_doc in extracted_docs:
                chunks = chunk_extracted_document(
                    doc=ext_doc,
                    target_size=self.settings.CHUNK_TARGET_SIZE,
                    overlap=self.settings.CHUNK_OVERLAP,
                )
                all_chunk_payloads.extend(chunks)

            if not all_chunk_payloads:
                raise BadRequestException("Document extraction produced zero valid semantic chunks.")

            chunk_entities: List[DocumentChunk] = []
            for cp in all_chunk_payloads:
                chunk_obj = DocumentChunk(
                    id=str(uuid.uuid4()),
                    generation_id=generation_id,
                    document_id=cp.document_id,
                    chunk_index=cp.chunk_index,
                    page_number=cp.page_number,
                    section_header=cp.section_header,
                    chunk_text=cp.chunk_text,
                    token_count=cp.token_count,
                    metadata_json=cp.metadata_json,
                )
                self.session.add(chunk_obj)
                chunk_entities.append(chunk_obj)

            generation.chunk_count = len(chunk_entities)
            chunk_status.completed_at = datetime.now(timezone.utc)
            chunk_status.progress_pct = 55
            chunk_status.message = f"Generated {len(chunk_entities)} semantic chunks."
            await self.session.commit()

            # ================= STAGE 3: EMBEDDING =================
            generation.status = GenerationLifecycleStatus.EMBED
            embed_status = GenerationStatus(
                id=str(uuid.uuid4()),
                generation_id=generation_id,
                stage=GenerationStage.EMBEDDING,
                progress_pct=60,
                message=f"Generating 384d vector embeddings using {self.settings.EMBEDDING_MODEL}.",
            )
            self.session.add(embed_status)
            await self.session.commit()

            chunk_texts = [c.chunk_text for c in chunk_entities]
            vectors = generate_embeddings(
                texts=chunk_texts,
                model_name=self.settings.EMBEDDING_MODEL,
                batch_size=self.settings.EMBEDDING_BATCH_SIZE,
                expected_dimension=self.settings.EMBEDDING_DIMENSION,
            )

            embed_status.completed_at = datetime.now(timezone.utc)
            embed_status.progress_pct = 75
            embed_status.message = f"Computed {len(vectors)} dense vector embeddings (dim={self.settings.EMBEDDING_DIMENSION})."
            await self.session.commit()

            # ================= STAGE 4: INDEXING =================
            generation.status = GenerationLifecycleStatus.INDEX
            index_status = GenerationStatus(
                id=str(uuid.uuid4()),
                generation_id=generation_id,
                stage=GenerationStage.INDEXING,
                progress_pct=80,
                message="Indexing vectors into ChromaDB persistent collection.",
            )
            self.session.add(index_status)
            await self.session.commit()

            chunk_ids = [c.id for c in chunk_entities]
            metadatas = [
                {
                    "chunk_id": c.id,
                    "document_id": c.document_id,
                    "generation_id": generation_id,
                    "page_number": c.page_number,
                    "section": c.section_header or "",
                    "source_filename": c.metadata_json.get("source_filename", "") if c.metadata_json else "",
                }
                for c in chunk_entities
            ]

            chroma_count = index_chunks_into_chroma(
                generation_id=generation_id,
                chunk_ids=chunk_ids,
                embeddings=vectors,
                documents=chunk_texts,
                metadatas=metadatas,
            )

            # Persist Embedding records in MySQL
            for c in chunk_entities:
                emb_record = Embedding(
                    id=str(uuid.uuid4()),
                    chunk_id=c.id,
                    vector_db_id=c.id,
                    model_name=self.settings.EMBEDDING_MODEL,
                    dimensions=self.settings.EMBEDDING_DIMENSION,
                )
                self.session.add(emb_record)

            generation.embedding_count = len(chunk_entities)
            index_status.completed_at = datetime.now(timezone.utc)
            index_status.progress_pct = 90
            index_status.message = f"Persisted {chroma_count} vectors into ChromaDB."
            await self.session.commit()

            # ================= STAGE 5: VALIDATION & EVALUATION =================
            eval_status = GenerationStatus(
                id=str(uuid.uuid4()),
                generation_id=generation_id,
                stage=GenerationStage.EVALUATION,
                progress_pct=95,
                message="Validating chunk integrity, embedding dimension, and vector counts.",
            )
            self.session.add(eval_status)
            await self.session.commit()

            # Strict verification criteria
            if generation.chunk_count <= 0:
                raise ValueError("Validation failed: Zero chunks in generation.")
            if generation.embedding_count != generation.chunk_count:
                raise ValueError(
                    f"Validation failed: Embedding count ({generation.embedding_count}) != chunk count ({generation.chunk_count})."
                )
            if chroma_count != generation.chunk_count:
                raise ValueError(
                    f"Validation failed: Chroma vector count ({chroma_count}) != MySQL chunk count ({generation.chunk_count})."
                )

            # Mark generation VALIDATED (ready for promotion)
            generation.status = GenerationLifecycleStatus.VALIDATED
            eval_status.completed_at = datetime.now(timezone.utc)
            eval_status.progress_pct = 100
            eval_status.message = "Knowledge generation build and validation succeeded."

            await _log_knowledge_audit(
                self.session,
                admin_id=admin_id,
                action="KNOWLEDGE_BUILD_COMPLETED",
                generation_id=generation_id,
                details={
                    "version": version_tag,
                    "chunks": generation.chunk_count,
                    "embeddings": generation.embedding_count,
                    "chroma_vectors": chroma_count,
                },
            )
            await self.session.commit()
            await self.session.refresh(generation)
            return generation

        except Exception as exc:
            logger.error("knowledge_build_failed", generation_id=generation_id, error=str(exc))
            generation.status = GenerationLifecycleStatus.FAILED
            error_status = GenerationStatus(
                id=str(uuid.uuid4()),
                generation_id=generation_id,
                stage=GenerationStage.ERROR,
                progress_pct=0,
                message=f"Build failed: {exc}",
                error_details=str(exc),
                completed_at=datetime.now(timezone.utc),
            )
            self.session.add(error_status)
            await _log_knowledge_audit(
                self.session,
                admin_id=admin_id,
                action="KNOWLEDGE_BUILD_FAILED",
                generation_id=generation_id,
                details={"error": str(exc)},
            )
            await self.session.commit()
            raise BadRequestException(f"Knowledge generation build failed: {exc}")

    async def promote_generation(self, generation_id: str, admin_id: str) -> PromoteRollbackResponse:
        """
        Transactionally promote a VALIDATED knowledge generation to ACTIVE status.
        Deactivates any currently active generation.
        """
        gen = await self.session.get(KnowledgeGeneration, generation_id)
        if not gen:
            raise NotFoundException(f"Knowledge generation '{generation_id}' not found.")

        if gen.status not in (GenerationLifecycleStatus.VALIDATED, GenerationLifecycleStatus.ARCHIVED):
            raise ConflictException(
                f"Cannot promote generation with status '{gen.status.value}'. Must be 'VALIDATED' or 'ARCHIVED'."
            )

        # Confirm vector count in ChromaDB matches expected count
        chroma_count = get_generation_collection_count(generation_id)
        if chroma_count != gen.chunk_count:
            raise ConflictException(
                f"ChromaDB vector count mismatch for generation '{generation_id}'. Expected {gen.chunk_count}, got {chroma_count}."
            )

        # Deactivate all currently active generations
        await self.session.execute(
            update(KnowledgeGeneration)
            .where(KnowledgeGeneration.is_active.is_(True))
            .values(is_active=False, status=GenerationLifecycleStatus.ARCHIVED)
        )

        # Promote target generation
        now = datetime.now(timezone.utc)
        gen.is_active = True
        gen.status = GenerationLifecycleStatus.ACTIVE
        gen.promoted_at = now

        await _log_knowledge_audit(
            self.session,
            admin_id=admin_id,
            action="KNOWLEDGE_PROMOTED",
            generation_id=generation_id,
            details={"version": gen.generation_version, "promoted_at": str(now)},
        )
        await self.session.commit()

        logger.info(
            "knowledge_generation_promoted",
            generation_id=generation_id,
            version=gen.generation_version,
            admin_id=admin_id,
        )

        return PromoteRollbackResponse(
            message=f"Knowledge generation '{gen.generation_version}' is now ACTIVE.",
            generation_id=gen.id,
            is_active=True,
            promoted_at=now,
        )

    async def rollback_generation(self, target_generation_id: str, admin_id: str) -> PromoteRollbackResponse:
        """
        Transactionally rollback active knowledge base to a previous VALIDATED or ARCHIVED generation.
        """
        target_gen = await self.session.get(KnowledgeGeneration, target_generation_id)
        if not target_gen:
            raise NotFoundException(f"Target knowledge generation '{target_generation_id}' not found.")

        if target_gen.is_active:
            raise ConflictException(f"Generation '{target_generation_id}' is already ACTIVE.")

        if target_gen.status not in (GenerationLifecycleStatus.VALIDATED, GenerationLifecycleStatus.ARCHIVED):
            raise ConflictException(
                f"Cannot rollback to generation with status '{target_gen.status.value}'. Must be 'VALIDATED' or 'ARCHIVED'."
            )

        # Verify Chroma collection still exists
        chroma_count = get_generation_collection_count(target_generation_id)
        if chroma_count != target_gen.chunk_count:
            raise ConflictException(
                f"ChromaDB collection for generation '{target_generation_id}' is missing or corrupted. Vector count: {chroma_count}."
            )

        # Deactivate current active generation
        await self.session.execute(
            update(KnowledgeGeneration)
            .where(KnowledgeGeneration.is_active.is_(True))
            .values(is_active=False, status=GenerationLifecycleStatus.ARCHIVED)
        )

        # Activate target generation
        now = datetime.now(timezone.utc)
        target_gen.is_active = True
        target_gen.status = GenerationLifecycleStatus.ACTIVE
        target_gen.promoted_at = now

        await _log_knowledge_audit(
            self.session,
            admin_id=admin_id,
            action="KNOWLEDGE_ROLLBACK",
            generation_id=target_generation_id,
            details={"target_version": target_gen.generation_version, "timestamp": str(now)},
        )
        await self.session.commit()

        logger.info(
            "knowledge_generation_rollback_completed",
            target_id=target_generation_id,
            version=target_gen.generation_version,
            admin_id=admin_id,
        )

        return PromoteRollbackResponse(
            message=f"Knowledge base successfully rolled back to '{target_gen.generation_version}'.",
            generation_id=target_gen.id,
            is_active=True,
            promoted_at=now,
        )

    async def list_generations(self, skip: int = 0, limit: int = 50) -> GenerationListResponse:
        """Retrieve paginated list of knowledge generations."""
        total = (
            await self.session.execute(select(func.count(KnowledgeGeneration.id)))
        ).scalar() or 0

        generations = (
            await self.session.execute(
                select(KnowledgeGeneration)
                .order_by(KnowledgeGeneration.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()

        items = [GenerationResponse.model_validate(g) for g in generations]
        return GenerationListResponse(items=items, total=total)

    async def get_generation_detail(self, generation_id: str) -> GenerationDetailResponse:
        """Retrieve complete generation details and granular stage execution log."""
        gen = await self.session.get(KnowledgeGeneration, generation_id)
        if not gen:
            raise NotFoundException(f"Knowledge generation '{generation_id}' not found.")

        stages = (
            await self.session.execute(
                select(GenerationStatus)
                .where(GenerationStatus.generation_id == generation_id)
                .order_by(GenerationStatus.started_at.asc())
            )
        ).scalars().all()

        return GenerationDetailResponse(
            generation=GenerationResponse.model_validate(gen),
            stages=[GenerationStatusResponse.model_validate(s) for s in stages],
        )

    async def is_document_referenced_by_active_generation(self, document_id: str) -> bool:
        """Check whether a document is currently indexed in an ACTIVE knowledge generation."""
        active_gen_query = (
            select(DocumentChunk.id)
            .join(KnowledgeGeneration, DocumentChunk.generation_id == KnowledgeGeneration.id)
            .where(
                DocumentChunk.document_id == document_id,
                KnowledgeGeneration.is_active.is_(True),
            )
            .limit(1)
        )
        result = await self.session.execute(active_gen_query)
        return result.scalar() is not None
