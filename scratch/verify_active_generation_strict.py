import asyncio
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.generation import KnowledgeGeneration, GenerationLifecycleStatus
from sqlalchemy import select

async def verify_active_gen():
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(KnowledgeGeneration).where(KnowledgeGeneration.is_active == True)
        res = await session.execute(stmt)
        active_list = res.scalars().all()
        
        print(f"Total active generations found: {len(active_list)}")
        
        # Explicitly enforce EXACTLY ONE active generation
        if len(active_list) != 1:
            raise AssertionError(f"Expected exactly 1 active generation, found {len(active_list)}!")
            
        gen = active_list[0]
        gen_id = str(gen.id)
        status = gen.status
        is_active = gen.is_active
        
        print(f"Generation ID: {gen_id}")
        print(f"Status: {status} (type: {type(status)})")
        print(f"Is Active: {is_active}")
        
        expected_id = "1a2c6365-1bee-4478-9599-a706ee5c7221"
        assert gen_id == expected_id, f"Expected ID {expected_id}, got {gen_id}"
        
        # Verify status matches valid active lifecycle status
        assert status == GenerationLifecycleStatus.ACTIVE or str(status) == "ACTIVE", f"Expected ACTIVE status, got {status}"
        assert is_active is True, f"Expected is_active to be True, got {is_active}"
        
        print("\nPASS: Active generation invariant strictly verified: EXACTLY ONE active generation matching 1a2c6365-1bee-4478-9599-a706ee5c7221 with ACTIVE status.")

if __name__ == "__main__":
    asyncio.run(verify_active_gen())
