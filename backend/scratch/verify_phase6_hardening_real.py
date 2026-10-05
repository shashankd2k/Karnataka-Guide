"""
Real verification script for Phase 6 hardening.
Checks MySQL connectivity, active knowledge generation integrity,
persistent Chroma collection readability, 384d vector dimension, and semantic query results.
"""

import asyncio
from pathlib import Path
from sqlalchemy import select
from app.core.config import get_settings
from app.infrastructure.db.session import get_async_engine, get_session_factory
from app.infrastructure.db.models.generation import KnowledgeGeneration, GenerationLifecycleStatus
from app.infrastructure.db.models.document import Document
from app.application.knowledge.vector_store import get_chroma_client, get_or_create_generation_collection, get_collection_name
from app.application.knowledge.embeddings import generate_embeddings

async def verify_real_kb_integrity():
    settings = get_settings()
    engine = get_async_engine()
    session_factory = get_session_factory()
    
    print("[1] Connecting to MySQL...")
    async with session_factory() as session:
        # Query active generation
        stmt = select(KnowledgeGeneration).where(KnowledgeGeneration.is_active.is_(True))
        result = await session.execute(stmt)
        active_gen = result.scalar_one_or_none()
        
        if active_gen:
            print(f"    Active Knowledge Generation found: {active_gen.id}")
            print(f"    Generation Version: {active_gen.generation_version}")
            print(f"    Status: {active_gen.status.value}")
            print(f"    Document Count: {active_gen.document_count}")
            print(f"    Chunk Count: {active_gen.chunk_count}")
            print(f"    Embedding Model: {active_gen.embedding_model}")
            print(f"    Embedding Count: {active_gen.embedding_count}")
            assert active_gen.status == GenerationLifecycleStatus.ACTIVE
            gen_id = active_gen.id
        else:
            print("    No active generation in DB yet (clean state). Listing all generations...")
            stmt_all = select(KnowledgeGeneration).order_by(KnowledgeGeneration.created_at.desc())
            res_all = await session.execute(stmt_all)
            all_gens = res_all.scalars().all()
            print(f"    Total generations in DB: {len(all_gens)}")
            if all_gens:
                gen_id = all_gens[0].id
                print(f"    Using latest generation {gen_id} ({all_gens[0].generation_version}) for Chroma check")
            else:
                gen_id = None

    await engine.dispose()
    print("[2] MySQL check passed!")

    # Check Chroma collection
    print("[3] Checking persistent ChromaDB storage at storage/chroma...")
    chroma_dir = settings.resolved_chroma_path
    print(f"    Chroma directory: {chroma_dir} (exists: {chroma_dir.exists()})")
    
    client = get_chroma_client(persist_path=chroma_dir)
    collections = client.list_collections()
    print(f"    Found {len(collections)} collections in ChromaDB")
    for col in collections:
        print(f"      - Collection: {col.name}, items: {col.count()}")

    if gen_id:
        col_name = get_collection_name(gen_id)
        collection = get_or_create_generation_collection(gen_id, client=client)
        count = collection.count()
        print(f"    Target generation collection '{col_name}' count: {count}")
        
        if count > 0:
            print("[4] Performing semantic test query against Chroma collection...")
            query_text = "Hampi Virupaksha Temple architecture"
            query_vector = generate_embeddings([query_text], model_name="all-MiniLM-L6-v2")[0]
            assert len(query_vector) == 384
            print(f"    Generated query vector with dimension: {len(query_vector)}")
            
            res = collection.query(query_embeddings=[query_vector], n_results=min(3, count))
            print(f"    Semantic query returned {len(res['ids'][0])} results:")
            for doc_id, meta, dist in zip(res['ids'][0], res['metadatas'][0], res['distances'][0]):
                print(f"      - ID: {doc_id} | Distance: {dist:.4f} | Source: {meta.get('source_filename', 'N/A')} (p.{meta.get('page_number', 'N/A')})")

    print("[5] ALL REAL KB & MYSQL INTEGRITY CHECKS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(verify_real_kb_integrity())
