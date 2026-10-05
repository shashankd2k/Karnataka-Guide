"""
Inspect all chunks across all generations in MySQL.
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


async def inspect_all():
    session_factory = get_session_factory()
    async with session_factory() as session:
        chunks = (await session.execute(select(DocumentChunk))).scalars().all()
        print(f"Total chunks in DB across all generations: {len(chunks)}")
        for c in chunks:
            print(f"\nGen: {c.generation_id} | Doc: {c.document_id} | Page: {c.page_number} | Sec: '{c.section_header}'")
            print(f"Text:\n{c.chunk_text}")

if __name__ == "__main__":
    asyncio.run(inspect_all())
