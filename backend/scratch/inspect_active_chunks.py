"""
Inspect all 22 chunks of the active generation and output their text and IDs.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.generation import KnowledgeGeneration
from app.infrastructure.db.models.chunk import DocumentChunk


async def inspect_active():
    session_factory = get_session_factory()
    async with session_factory() as session:
        active_gen = (await session.execute(
            select(KnowledgeGeneration).where(KnowledgeGeneration.is_active.is_(True))
        )).scalar_one()

        print(f"ACTIVE GENERATION: {active_gen.id} (ver: {active_gen.generation_version})")
        print(f"Total Chunks: {active_gen.chunk_count}, Total Docs: {active_gen.document_count}")

        chunks = (await session.execute(
            select(DocumentChunk).where(DocumentChunk.generation_id == active_gen.id).order_by(DocumentChunk.chunk_index)
        )).scalars().all()

        for idx, c in enumerate(chunks, 1):
            source_fn = c.metadata_json.get("source_filename", "") if c.metadata_json else ""
            print(f"\n==================== CHUNK #{idx} ====================")
            print(f"CHUNK_ID: {c.id}")
            print(f"DOC: {source_fn} (p.{c.page_number})")
            print(f"SECTION: {c.section_header}")
            print("--- TEXT ---")
            print(c.chunk_text)

if __name__ == "__main__":
    asyncio.run(inspect_active())
