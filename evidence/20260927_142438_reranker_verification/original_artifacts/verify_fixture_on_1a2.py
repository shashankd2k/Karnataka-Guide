import asyncio
import json
import sys
from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.chunk import DocumentChunk
from app.application.rag.service import RAGRetrievalService
from app.application.rag.schemas import RetrievalDiagnosticRequest

async def verify_queries():
    factory = get_session_factory()
    async with factory() as session:
        # Load chunks from 6ee and 1a2
        c_6ee = (await session.execute(
            select(DocumentChunk).where(DocumentChunk.generation_id == '6ee08b45-823a-4bd5-8604-920bbdd61d58')
        )).scalars().all()
        c_1a2 = (await session.execute(
            select(DocumentChunk).where(DocumentChunk.generation_id == '1a2c6365-1bee-4478-9599-a706ee5c7221')
        )).scalars().all()
        
        map_6ee_to_1a2 = {}
        for a in c_6ee:
            for b in c_1a2:
                if a.chunk_text.strip() == b.chunk_text.strip():
                    map_6ee_to_1a2[a.id] = b.id
                    break
                    
        print(f"Mapping 6ee -> 1a2 complete: {len(map_6ee_to_1a2)} / {len(c_6ee)} chunks mapped.")
        
        with open('/app/scratch/canonical_24_queries.json', 'r', encoding='utf-8') as f:
            queries = json.load(f)
            
        service = RAGRetrievalService(session=session)
        hits1 = 0
        hits5 = 0
        rrs = []
        bib_intrusions = 0
        
        print("\nTesting 24 queries against active generation 1a2c6365-1bee-4478-9599-a706ee5c7221 (candidates=15):")
        print("-" * 80)
        
        for q in queries:
            expected_1a2 = [map_6ee_to_1a2[cid] for cid in q['expected_chunks'] if cid in map_6ee_to_1a2]
            req = RetrievalDiagnosticRequest(
                query=q['query'],
                top_k=5,
                rerank_candidates=15,
                enable_reranker=True,
                filter_noise=True,
                suppress_duplicates=True,
            )
            resp = await service.retrieve_evidence(req)
            
            # Check bibliography intrusion
            for cand in resp.results:
                text_lower = cand.text.lower()
                sec_lower = (cand.section or "").lower()
                if "bibliography" in sec_lower or "references" in sec_lower or "isbn:" in text_lower:
                    bib_intrusions += 1

            ranks = [idx for idx, r in enumerate(resp.results, 1) if r.chunk_id in expected_1a2]
            first_rank = ranks[0] if ranks else None
            if first_rank == 1:
                hits1 += 1
            if first_rank and first_rank <= 5:
                hits5 += 1
                rrs.append(1.0 / first_rank)
            else:
                rrs.append(0.0)
            status = f"Rank {first_rank}" if first_rank else "MISSED (>5)"
            print(f"[{q['id']}] ({q['category'][:15]:15s}) -> {status:12s} | Score: {resp.results[0].reranker_score:6.2f} | Q: {q['query'][:40]}...")
            
        print("-" * 80)
        hit1_pct = (hits1 / len(queries)) * 100.0
        recall5_pct = (hits5 / len(queries)) * 100.0
        mrr = sum(rrs) / len(queries)
        print(f"Hit@1 Rate: {hit1_pct:.2f}% ({hits1}/{len(queries)})")
        print(f"Recall@5  : {recall5_pct:.2f}% ({hits5}/{len(queries)})")
        print(f"MRR       : {mrr:.4f}")
        print(f"Bib Leaks : {bib_intrusions}")

if __name__ == '__main__':
    asyncio.run(verify_queries())
