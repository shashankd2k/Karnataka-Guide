"""
Print full untruncated text of chunks in generation 3d4fe607-b1f7-4ee9-8205-2dcd177c8b47.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.chunk import DocumentChunk


async def print_full():
    session_factory = get_session_factory()
    gen_id = "3d4fe607-b1f7-4ee9-8205-2dcd177c8b47"
    async with session_factory() as session:
        chunks = (await session.execute(
            select(DocumentChunk).where(DocumentChunk.generation_id == gen_id).order_by(DocumentChunk.chunk_index)
        )).scalars().all()
        for idx, c in enumerate(chunks, 1):
            source_fn = c.metadata_json.get("source_filename", "") if c.metadata_json else ""
            print(f"==================== CHUNK #{idx} ====================")
            print(f"CHUNK_ID: {c.id}")
            print(f"DOC: {source_fn} (p.{c.page_number})")
            print(f"SECTION: {c.section_header}")
            print("--- FULL TEXT ---")
            print(repr(c.chunk_text))
            print("--- FORMATTED ---")
            print(c.chunk_text)
            print()

if __name__ == "__main__":
    asyncio.run(print_full())
