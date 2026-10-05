"""
Inspect documents and chunks in MySQL.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.document import Document
from app.infrastructure.db.models.generation import KnowledgeGeneration
from app.infrastructure.db.models.chunk import DocumentChunk


async def inspect():
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Documents
        docs = (await session.execute(select(Document))).scalars().all()
        print(f"=== Documents in DB ({len(docs)}) ===")
        for d in docs:
            print(f"ID: {d.id} | Name: {d.original_name} | Pages: {d.page_count} | Status: {d.status}")

        # Generations
        gens = (await session.execute(select(KnowledgeGeneration))).scalars().all()
        print(f"\n=== Knowledge Generations ({len(gens)}) ===")
        for g in gens:
            print(f"ID: {g.id} | Ver: {g.generation_version} | Active: {g.is_active} | Status: {g.status} | Docs: {g.document_count} | Chunks: {g.chunk_count}")

        # Chunks for active generation
        active_gen = (await session.execute(
            select(KnowledgeGeneration).where(KnowledgeGeneration.is_active.is_(True))
        )).scalar_one_or_none()

        if active_gen:
            chunks = (await session.execute(
                select(DocumentChunk).where(DocumentChunk.generation_id == active_gen.id).order_by(DocumentChunk.chunk_index)
            )).scalars().all()
            print(f"\n=== Active Gen Chunks ({len(chunks)}) ===")
            for idx, c in enumerate(chunks, 1):
                source_fn = c.metadata_json.get("source_filename", "") if c.metadata_json else ""
                print(f"\n--- Chunk #{idx} (ID: {c.id}, Doc: {c.document_id}, Page: {c.page_number}, Sec: '{c.section_header}', Source: '{source_fn}') ---")
                print(f"Text ({len(c.chunk_text)} chars):\n{c.chunk_text}")

if __name__ == "__main__":
    asyncio.run(inspect())
