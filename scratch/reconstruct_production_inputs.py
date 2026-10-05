import asyncio
import json
import os
import sys
import hashlib
from typing import Dict, Any, List

from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.chunk import DocumentChunk
from app.infrastructure.db.models.document import Document
from app.application.rag.schemas import RetrievalCandidate
from app.application.conversation.grounding_guard import GroundingGuard
from app.application.rag.prompt_builder import build_grounded_prompt
from app.application.conversation.citation_formatter import extract_authoritative_citations
from app.core.config import get_settings

ACTIVE_GEN_ID = "1a2c6365-1bee-4478-9599-a706ee5c7221"

async def main():
    settings = get_settings()
    factory = get_session_factory()
    async with factory() as db:
        chunks = (await db.execute(select(DocumentChunk).where(DocumentChunk.generation_id == ACTIVE_GEN_ID))).scalars().all()
        docs = (await db.execute(select(Document))).scalars().all()
        doc_map = {str(d.id): d.filename for d in docs}
        chunk_map = {str(c.id): c for c in chunks}
        
    bench_path = "/app/scratch/level2_rerank_experiment/benchmark_results.json"
    with open(bench_path, "r", encoding="utf-8") as f:
        bench = json.load(f)
        
    queries = bench["queries"]
    print(f"Active chunks in MySQL: {len(chunks)}")
    print(f"Benchmark queries: {len(queries)}")
    
    def to_cands(ev_list: List[Dict[str, Any]]) -> List[RetrievalCandidate]:
        res = []
        for rank, item in enumerate(ev_list, 1):
            cid = item["chunk_id"]
            c = chunk_map[cid]
            cand = RetrievalCandidate(
                chunk_id=cid,
                document_id=str(c.document_id),
                source_filename=doc_map.get(str(c.document_id), item["doc"]),
                page_number=c.page_number,
                section=c.section_header,
                text=c.chunk_text,
                chunk_index=c.chunk_index,
                token_count=c.token_count,
                generation_id=ACTIVE_GEN_ID,
                reranker_score=item["score"],
                final_rank=rank,
            )
            res.append(cand)
        return res

    all_24_results = {}
    differing_qids = []
    identical_qids = []

    for qid in sorted(queries.keys()):
        q_data = queries[qid]
        q_text = q_data["query_text"]
        r1 = q_data["rep1_15_then_10"]
        
        cands15 = to_cands(r1["arm_15"]["final_evidence"])
        cands10 = to_cands(r1["arm_10"]["final_evidence"])
        
        sys15, user15, labels15 = build_grounded_prompt(
            query=q_text,
            candidates=cands15,
            language="en",
            max_chars=settings.OLLAMA_MAX_CONTEXT_CHARS,
        )
        sys10, user10, labels10 = build_grounded_prompt(
            query=q_text,
            candidates=cands10,
            language="en",
            max_chars=settings.OLLAMA_MAX_CONTEXT_CHARS,
        )
        
        cits15 = extract_authoritative_citations(cands15, ACTIVE_GEN_ID, max_passages=3)
        cits10 = extract_authoritative_citations(cands10, ACTIVE_GEN_ID, max_passages=3)
        
        # Citations are already serialized dictionaries
        cits15_serialized = cits15
        cits10_serialized = cits10
        
        top5_cids15 = [c.chunk_id for c in cands15[:5]]
        top5_cids10 = [c.chunk_id for c in cands10[:5]]
        
        top5_identical = (top5_cids15 == top5_cids10)
        sys_identical = (sys15 == sys10)
        user_identical = (user15 == user10)
        labels_identical = (labels15 == labels10)
        cits_identical = (cits15_serialized == cits10_serialized)
        
        entry = {
            "query_id": qid,
            "query_text": q_text,
            "top5_chunks_identical": top5_identical,
            "system_prompt_identical": sys_identical,
            "user_prompt_identical": user_identical,
            "authorized_labels_identical": labels_identical,
            "authoritative_citations_identical": cits_identical,
            "arm_15": {
                "top_5_chunks": [
                    {
                        "rank": c.final_rank,
                        "chunk_id": c.chunk_id,
                        "source_filename": c.source_filename,
                        "page_number": c.page_number,
                        "section": c.section,
                        "reranker_score": c.reranker_score,
                        "text_sha256": hashlib.sha256(c.text.encode("utf-8")).hexdigest(),
                        "text_snippet": c.text[:120],
                    }
                    for c in cands15[:5]
                ],
                "system_prompt": sys15,
                "user_prompt": user15,
                "authorized_labels": labels15,
                "authoritative_citations": cits15_serialized,
            },
            "arm_10": {
                "top_5_chunks": [
                    {
                        "rank": c.final_rank,
                        "chunk_id": c.chunk_id,
                        "source_filename": c.source_filename,
                        "page_number": c.page_number,
                        "section": c.section,
                        "reranker_score": c.reranker_score,
                        "text_sha256": hashlib.sha256(c.text.encode("utf-8")).hexdigest(),
                        "text_snippet": c.text[:120],
                    }
                    for c in cands10[:5]
                ],
                "system_prompt": sys10,
                "user_prompt": user10,
                "authorized_labels": labels10,
                "authoritative_citations": cits10_serialized,
            },
        }
        all_24_results[qid] = entry
        
        if top5_identical:
            identical_qids.append(qid)
        else:
            differing_qids.append(qid)

    print(f"Identical top-5 queries ({len(identical_qids)}): {identical_qids}")
    print(f"Differing top-5 queries ({len(differing_qids)}): {differing_qids}")

    payload = {
        "metadata": {
            "active_generation_id": ACTIVE_GEN_ID,
            "total_queries": len(queries),
            "identical_top5_count": len(identical_qids),
            "differing_top5_count": len(differing_qids),
            "identical_qids": identical_qids,
            "differing_qids": differing_qids,
            "effective_generation_parameters": {
                "model": settings.OLLAMA_MODEL,
                "temperature": settings.OLLAMA_TEMPERATURE,
                "num_ctx": settings.OLLAMA_NUM_CTX,
                "num_thread": getattr(settings, "OLLAMA_NUM_THREAD", 2),
                "num_predict": 128,
                "max_context_chars": settings.OLLAMA_MAX_CONTEXT_CHARS,
                "timeout_seconds": settings.OLLAMA_TIMEOUT_SECONDS,
            },
        },
        "queries": all_24_results,
    }

    out_file = "/app/scratch/reconstructed_production_inputs_all24.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Exported reconstructed inputs for all 24 queries to {out_file}")

if __name__ == "__main__":
    asyncio.run(main())
