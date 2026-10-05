"""
Real End-to-End Knowledge Base Pipeline Verification Script for Phase 6.

Tests against:
- Real MySQL 8.0 instance (karnataka_guide)
- Real physical storage (storage/documents)
- Real persistent ChromaDB (storage/chroma)
- Real SentenceTransformer embeddings (all-MiniLM-L6-v2, 384 dimensions)
- Real PyMuPDF multi-page document parsing & semantic chunking
"""

import asyncio
from datetime import datetime, timezone
import io
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog
import fitz
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.errors import ConflictException
from app.core.security import hash_password
from app.infrastructure.db.models.admin import Admin, AdminRole
from app.infrastructure.db.models.audit import AuditLog
from app.infrastructure.db.models.chunk import DocumentChunk, Embedding
from app.infrastructure.db.models.document import Document, DocumentStatus
from app.infrastructure.db.models.generation import (
    GenerationLifecycleStatus,
    GenerationStage,
    GenerationStatus,
    KnowledgeGeneration,
)
from app.application.documents.service import delete_document, upload_document
from app.application.documents.storage import remove_pdf_from_storage
from app.application.knowledge.service import KnowledgeService
from app.application.knowledge.vector_store import get_chroma_client, get_collection_name
from app.application.knowledge.embeddings import get_embedding_model, generate_embeddings

logger = structlog.get_logger(__name__)


class MockUploadFile:
    """Helper mock for FastAPI UploadFile during direct service testing."""
    def __init__(self, filename: str, content: bytes, content_type: str = "application/pdf"):
        self.filename = filename
        self._content = content
        self.content_type = content_type

    async def read(self) -> bytes:
        return self._content


def _generate_tourism_pdf_pattadakal() -> bytes:
    """Generate a realistic multi-page tourism PDF on Pattadakal."""
    doc = fitz.open()

    # Page 1: Introduction & History
    page1 = doc.new_page()
    page1.insert_text(
        (50, 60),
        "PATTADAKAL UNESCO WORLD HERITAGE SITE (ಪಟ್ಟದಕಲ್ಲು)\n\n"
        "Pattadakal, also called Raktapura, is a complex of 7th and 8th century CE Hindu and Jain temples in northern Karnataka.\n"
        "Located on the west bank of the Malaprabha River in Bagalkot district, this UNESCO World Heritage site represents the high point of an eclectic art which, in the 7th and 8th centuries under the Chalukya dynasty, achieved a harmonious blend of architectural forms from northern and southern India.\n\n"
        "The Chalukya king Vikramaditya II (734–744 CE) commissioned the greatest temple here, the Virupaksha Temple, to commemorate his victory over the Pallavas of Kanchipuram.\n"
        "The complex illustrates the confluence of Nagara (North Indian) and Dravida (South Indian) styles of temple architecture side by side.",
        fontsize=11,
    )

    # Page 2: Temples & Architecture
    page2 = doc.new_page()
    page2.insert_text(
        (50, 60),
        "KEY TEMPLES AND ARCHITECTURAL HIGHLIGHTS\n\n"
        "1. Virupaksha Temple:\n"
        "The largest and most sophisticated temple in Pattadakal. It features rich friezes depicting scenes from the Ramayana, Mahabharata, and Bhagavata Purana.\n"
        "The massive monolithic Nandi pavilion faces the sanctum. The sanctum contains a large black stone Shiva Linga.\n\n"
        "2. Mallikarjuna Temple:\n"
        "Built concurrently with Virupaksha Temple by Queen Trailokyamahadevi. It is nearly identical in design but slightly smaller, with exquisite carvings of Narasimha and Shiva.\n\n"
        "3. Sangameshwara Temple:\n"
        "One of the oldest Dravidian style temples at Pattadakal, commissioned by King Vijayaditya (696–733 CE). It is characterized by its classical simplicity and majestic proportions.",
        fontsize=11,
    )

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _generate_tourism_pdf_badami() -> bytes:
    """Generate a second realistic tourism PDF on Badami Cave Temples."""
    doc = fitz.open()

    page1 = doc.new_page()
    page1.insert_text(
        (50, 60),
        "BADAMI CAVE TEMPLES AND FORTS (ಬಾದಾಮಿ)\n\n"
        "Badami, formerly known as Vatapi, was the regal capital of the Badami Chalukyas from 540 to 757 CE.\n"
        "It is famous for its rock-cut cave temples carved out of the soft sandstone cliffs surrounding the picturesque Agastya Lake.\n\n"
        "The complex comprises four principal caves:\n"
        "- Cave 1: Dedicated to Lord Shiva, featuring the famous 18-armed dancing Nataraja in 81 distinct poses.\n"
        "- Cave 2: Dedicated to Lord Vishnu in his Trivikrama and Varaha incarnations.\n"
        "- Cave 3: The largest cave temple, renowned for intricate carvings of Vishnu seated on the serpent Shesha and Narasimha.\n"
        "- Cave 4: A 6th-century Jain cave temple dedicated to Mahavira and Parshvanatha with beautifully sculpted tirthankaras.",
        fontsize=11,
    )

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


async def main():
    print("=" * 70)
    print("STARTING REAL PHASE 6 KNOWLEDGE BASE PIPELINE VERIFICATION")
    print("=" * 70)

    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Step 1: Ensure an active admin user exists
        admin_stmt = select(Admin).where(Admin.username == "admin")
        admin = (await session.execute(admin_stmt)).scalar_one_or_none()
        if not admin:
            admin = Admin(
                username="admin",
                email="admin@karnataka.gov.in",
                hashed_password=hash_password("Admin@Karnataka2026"),
                role=AdminRole.SUPER_ADMIN,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            print(f"[OK] Created admin user: {admin.id}")
        else:
            print(f"[OK] Found admin user: {admin.username} ({admin.id})")

        # Step 2: Test Document 1 Upload (Pattadakal PDF)
        pdf1_bytes = _generate_tourism_pdf_pattadakal()
        mock_file1 = MockUploadFile("Pattadakal_UNESCO_Guide.pdf", pdf1_bytes)
        doc1 = await upload_document(
            session=session,
            upload_file=mock_file1,
            current_admin=admin,
            ip_address="127.0.0.1",
        )
        print(f"[OK] Document 1 uploaded successfully:")
        print(f"     ID: {doc1.id}")
        print(f"     Original Name: {doc1.original_name}")
        print(f"     Size: {doc1.file_size_bytes} bytes")
        print(f"     SHA-256: {doc1.sha256_hash[:16]}...")
        print(f"     Status: {doc1.status.value}")

        # Step 3: Verify SentenceTransformer singleton model
        emb_model = get_embedding_model()
        print(f"[OK] Embedding Model Loaded: {settings.EMBEDDING_MODEL} (Device: {emb_model.device})")

        # Step 4: Run Knowledge Base Pipeline Build for Generation 1
        print("\n--- Triggering Knowledge Generation 1 Build ---")
        kb_service = KnowledgeService(session=session)
        gen1 = await kb_service.build_generation(
            admin_id=admin.id,
            document_ids=[doc1.id],
            description="Phase 6 Verification Generation 1 - Pattadakal",
        )
        print(f"[OK] Generation 1 Build Completed:")
        print(f"     ID: {gen1.id}")
        print(f"     Version: {gen1.generation_version}")
        print(f"     Status: {gen1.status.value}")
        print(f"     Docs: {gen1.document_count}, Chunks: {gen1.chunk_count}, Embeddings: {gen1.embedding_count}")
        print(f"     Is Active: {gen1.is_active}")
        assert gen1.status == GenerationLifecycleStatus.VALIDATED
        assert gen1.chunk_count > 0
        assert gen1.embedding_count == gen1.chunk_count

        # Step 5: Verify MySQL records for Chunks and Embeddings
        chunks_stmt = select(DocumentChunk).where(DocumentChunk.generation_id == gen1.id)
        chunks = (await session.execute(chunks_stmt)).scalars().all()
        assert len(chunks) == gen1.chunk_count
        print(f"[OK] MySQL document_chunks verified: {len(chunks)} chunks in DB")
        for i, c in enumerate(chunks[:2]):
            print(f"     Chunk {i+1}: Page {c.page_number}, Index {c.chunk_index}, Length {len(c.chunk_text)} chars, Token Est {c.token_count}")
            print(f"     Content snippet: {c.chunk_text[:80]}...")

        embs_stmt = (
            select(Embedding)
            .join(DocumentChunk, Embedding.chunk_id == DocumentChunk.id)
            .where(DocumentChunk.generation_id == gen1.id)
        )
        embs = (await session.execute(embs_stmt)).scalars().all()
        assert len(embs) == gen1.embedding_count
        assert all(e.dimensions == 384 for e in embs)
        assert all(e.model_name == "all-MiniLM-L6-v2" for e in embs)
        print(f"[OK] MySQL embeddings verified: {len(embs)} records with 384 dimensions and correct model name")

        # Step 6: Verify ChromaDB persistent collection
        chroma_client = get_chroma_client()
        col_name = get_collection_name(gen1.id)
        collection = chroma_client.get_collection(name=col_name)
        chroma_count = collection.count()
        assert chroma_count == gen1.chunk_count
        print(f"[OK] Persistent ChromaDB collection verified: '{col_name}' contains {chroma_count} vectors")

        # Step 7: Semantic Search Query in ChromaDB
        search_query = "Who built the Virupaksha temple at Pattadakal and why?"
        print(f"\n--- Testing Semantic Search Query in ChromaDB ---")
        print(f"Query: '{search_query}'")
        query_vecs = generate_embeddings([search_query])
        search_results = collection.query(
            query_embeddings=query_vecs,
            n_results=2,
        )
        print(f"[OK] ChromaDB Semantic Search returned {len(search_results['ids'][0])} results:")
        for idx, (doc_text, distance) in enumerate(zip(search_results["documents"][0], search_results["distances"][0])):
            print(f"     Result {idx+1} [Cosine Distance: {distance:.4f}]:")
            print(f"     {doc_text[:120]}...")

        # Step 8: Promote Generation 1 to ACTIVE
        print("\n--- Promoting Generation 1 to ACTIVE ---")
        promote_resp1 = await kb_service.promote_generation(
            generation_id=gen1.id,
            admin_id=admin.id,
        )
        await session.refresh(gen1)
        assert gen1.is_active is True
        assert gen1.status == GenerationLifecycleStatus.ACTIVE
        print(f"[OK] Generation 1 Promoted:")
        print(f"     Status: {gen1.status.value}, is_active: {gen1.is_active}")

        # Step 9: Verify Active Document Deletion Protection (Expect 409 Conflict)
        print("\n--- Testing Active Document Deletion Guard ---")
        try:
            await delete_document(
                session=session,
                document_id=doc1.id,
                current_admin=admin,
            )
            raise AssertionError("Document deletion should have failed with ConflictException!")
        except ConflictException as exc:
            print(f"[OK] Active document deletion successfully blocked with ConflictException (409):")
            print(f"     Message: {exc.message}")

        # Step 10: Upload Document 2 (Badami PDF) & Build Generation 2
        print("\n--- Uploading Document 2 & Building Generation 2 ---")
        pdf2_bytes = _generate_tourism_pdf_badami()
        mock_file2 = MockUploadFile("Badami_Caves_Guide.pdf", pdf2_bytes)
        doc2 = await upload_document(
            session=session,
            upload_file=mock_file2,
            current_admin=admin,
            ip_address="127.0.0.1",
        )
        print(f"[OK] Document 2 uploaded: {doc2.id} ({doc2.original_name})")

        gen2 = await kb_service.build_generation(
            admin_id=admin.id,
            document_ids=[doc1.id, doc2.id],
            description="Phase 6 Verification Generation 2 - Pattadakal + Badami",
        )
        print(f"[OK] Generation 2 Build Completed: {gen2.id} (Version: {gen2.generation_version}, Chunks: {gen2.chunk_count})")

        # Promote Generation 2 (Generation 1 should be ARCHIVED)
        await kb_service.promote_generation(
            generation_id=gen2.id,
            admin_id=admin.id,
        )
        await session.refresh(gen2)
        assert gen2.is_active is True
        assert gen2.status == GenerationLifecycleStatus.ACTIVE

        # Refresh Gen 1 to verify it is now ARCHIVED and is_active is False
        await session.refresh(gen1)
        assert gen1.is_active is False
        assert gen1.status == GenerationLifecycleStatus.ARCHIVED
        print(f"[OK] Generation 2 is now ACTIVE, Generation 1 automatically transitioned to ARCHIVED.")

        # Step 11: Test Instant Rollback back to Generation 1
        print("\n--- Testing Instant Knowledge Base Rollback to Generation 1 ---")
        await kb_service.rollback_generation(
            target_generation_id=gen1.id,
            admin_id=admin.id,
        )
        await session.refresh(gen1)
        assert gen1.is_active is True
        assert gen1.status == GenerationLifecycleStatus.ACTIVE

        await session.refresh(gen2)
        assert gen2.is_active is False
        assert gen2.status == GenerationLifecycleStatus.ARCHIVED
        print(f"[OK] Rollback successful: Generation 1 restored to ACTIVE, Generation 2 marked ARCHIVED.")

        # Step 12: Verify Audit Log Records in MySQL
        audit_stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(15)
        audit_logs = (await session.execute(audit_stmt)).scalars().all()
        actions = [a.action for a in audit_logs]
        print(f"\n--- Verified MySQL Security Audit Trail ---")
        for log in audit_logs[:6]:
            print(f"     [{log.action}] resource_type={log.resource_type}, resource_id={log.resource_id}, admin_id={log.admin_id}")
        assert "KNOWLEDGE_PROMOTED" in actions
        assert "KNOWLEDGE_ROLLBACK" in actions
        assert "DOCUMENT_UPLOADED" in actions

    await engine.dispose()
    print("\n" + "=" * 70)
    print("ALL PHASE 6 REAL PIPELINE VERIFICATIONS PASSED WITH 100% SUCCESS!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
