"""
Expanded 24-Query Source-Grounded RAG Retrieval Benchmark for Phase 7.
Evaluates:
- Hit@1, Recall@5, Precision@5, MRR against explicit ground-truth chunk IDs
- Bibliography / Reference leakage rate (0% expected)
- Duplicate result rate (0% expected)
- Stage-level latencies: dense_ms, bm25_ms, fusion_ms, rerank_ms, total_ms
- Weak/Failure query analysis for non-rank-1 or missed results
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from typing import List, Dict, Set, Any
from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.generation import KnowledgeGeneration, GenerationLifecycleStatus
from app.infrastructure.db.models.chunk import DocumentChunk
from app.application.rag.service import RAGRetrievalService
from app.application.rag.schemas import RetrievalDiagnosticRequest


async def run_benchmark():
    session_factory = get_session_factory()
    async with session_factory() as session:
        # 1. Fetch active generation
        active_gen = (await session.execute(
            select(KnowledgeGeneration)
            .where(
                KnowledgeGeneration.is_active.is_(True),
                KnowledgeGeneration.status == GenerationLifecycleStatus.ACTIVE,
            )
            .order_by(KnowledgeGeneration.promoted_at.desc())
        )).scalar_one_or_none()

        if not active_gen:
            print("[ERROR] No ACTIVE knowledge generation found.")
            return

        # Fetch all chunks in active generation
        chunks = (await session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.generation_id == active_gen.id)
            .order_by(DocumentChunk.chunk_index)
        )).scalars().all()

        chunk_by_id = {c.id: c for c in chunks}
        doc_ids = {c.document_id for c in chunks}
        pages_by_doc: Dict[str, Set[int]] = {}
        for c in chunks:
            pages_by_doc.setdefault(c.document_id, set()).add(c.page_number)
        total_pages = sum(len(p) for p in pages_by_doc.values())

        print("=" * 80)
        print("REAL SOURCE-GROUNDED RAG RETRIEVAL BENCHMARK (PHASE 7)")
        print("=" * 80)
        print(f"Active Generation ID : {active_gen.id}")
        print(f"Version              : {active_gen.generation_version}")
        print(f"Corpus Documents     : {len(doc_ids)}")
        print(f"Corpus Pages         : {total_pages}")
        print(f"Corpus Total Chunks  : {len(chunks)}")
        print("=" * 80)

        # Explicit Ground-Truth Benchmark Queries mapped to active chunk IDs
        # Each query has:
        # - query: string
        # - category: query category
        # - expected_chunk_ids: list of valid ground truth chunk IDs
        # - expected_desc: description of expected factual evidence
        benchmark_queries = [
            # 1. Founder / Patron
            {
                "id": "Q01",
                "category": "founder/patron",
                "query": "Who commissioned the Belur Chennakeshava temple and why?",
                "expected_chunks": ["8d583c25-2413-48c7-997d-8de0153f0cd3", "e7d436d1-6513-45eb-a205-d3da802e21b4"],
                "expected_desc": "King Vishnuvardhana, Battle of Talakadu (Belur_Halebidu_Hoysala_Guide.pdf, p.2)",
            },
            # 2. Founder / Patron
            {
                "id": "Q02",
                "category": "founder/patron",
                "query": "Which queen built the Virupaksha temple at Pattadakal?",
                "expected_chunks": ["aff8d390-d5a4-4361-bec5-4ae6246585fd"],
                "expected_desc": "Queen Lokamahadevi, victory over Pallavas of Kanchipuram (Pattadakal_UNESCO_Guide.pdf, p.2)",
            },
            # 3. Construction Date
            {
                "id": "Q03",
                "category": "construction date",
                "query": "What year was the Belur Chennakeshava temple commissioned?",
                "expected_chunks": ["8d583c25-2413-48c7-997d-8de0153f0cd3"],
                "expected_desc": "1117 CE (Belur_Halebidu_Hoysala_Guide.pdf, p.2)",
            },
            # 4. Construction Date / Epigraphy
            {
                "id": "Q04",
                "category": "construction date",
                "query": "When was Badami Cave 3 carved and which king commissioned it?",
                "expected_chunks": ["beeeec65-5f80-46d5-837a-b913bc2ba236"],
                "expected_desc": "578 CE / Saka 500 by King Mangalesha (Badami_Caves_Guide.pdf, p.2)",
            },
            # 5. History
            {
                "id": "Q05",
                "category": "history",
                "query": "Who were the founding brothers of the Vijayanagara Empire at Hampi?",
                "expected_chunks": ["149f3694-3af4-4ca4-ab3f-f0284c2c85ab"],
                "expected_desc": "Harihara I and Bukka Raya I in 1336 CE (Hampi_Vijayanagara_Guide.pdf, p.1)",
            },
            # 6. History
            {
                "id": "Q06",
                "category": "history",
                "query": "Aihole inscription Pulakeshin II victory over Emperor Harsha of Kannauj",
                "expected_chunks": ["d9d9b05e-6184-4f37-a14f-a73c3d2d2807"],
                "expected_desc": "634 CE Meguti Hill inscription by poet Ravikirti, Narmada battle (Aihole_Heritage_Guide.pdf, p.2)",
            },
            # 7. Architecture (Plan)
            {
                "id": "Q07",
                "category": "architecture",
                "query": "What is the unique architectural floor plan of Durga Temple at Aihole?",
                "expected_chunks": ["41dfbf1e-a2ed-456c-9283-99bd749201ae"],
                "expected_desc": "Apsidal / gajaprishta horseshoe plan (Aihole_Heritage_Guide.pdf, p.1)",
            },
            # 8. Architecture (Confluence)
            {
                "id": "Q08",
                "category": "architecture",
                "query": "Harmonious confluence of Nagara and Dravida architectural styles at Pattadakal",
                "expected_chunks": ["9b83c145-367e-4917-bc6b-6fd3e0230dbb", "d2c053c3-7777-4371-ad12-7fac1771581c"],
                "expected_desc": "Blend of northern Nagara and southern Dravida styles (Pattadakal_UNESCO_Guide.pdf, p.1)",
            },
            # 9. Sculpture
            {
                "id": "Q09",
                "category": "sculpture",
                "query": "18-armed dancing Nataraja with 81 distinct poses at Badami Cave 1",
                "expected_chunks": ["0f3e33e1-c416-432e-9145-eea73222c222"],
                "expected_desc": "Cave 1 dancing Nataraja 81 mudras (Badami_Caves_Guide.pdf, p.2)",
            },
            # 10. Sculpture
            {
                "id": "Q10",
                "category": "sculpture",
                "query": "Famous Darpana Sundari bracket figure admiring mirror at Belur",
                "expected_chunks": ["e7d436d1-6513-45eb-a205-d3da802e21b4"],
                "expected_desc": "42 Madanika bracket figures, Darpana Sundari (Belur_Halebidu_Hoysala_Guide.pdf, p.2)",
            },
            # 11. Sculpture / Friezes
            {
                "id": "Q11",
                "category": "sculpture",
                "query": "Eight tiers of relief friezes with charging war elephants at Halebidu",
                "expected_chunks": ["4325e2b0-35dd-4c0c-bf0f-be4b72cc9201"],
                "expected_desc": "1,248 charging war elephants on base tiers (Belur_Halebidu_Hoysala_Guide.pdf, p.3)",
            },
            # 12. Inscriptions
            {
                "id": "Q12",
                "category": "inscriptions",
                "query": "Poet Ravikirti Sanskrit inscription on Meguti hill at Aihole",
                "expected_chunks": ["d9d9b05e-6184-4f37-a14f-a73c3d2d2807"],
                "expected_desc": "634 CE Meguti Jain temple Sanskrit inscription (Aihole_Heritage_Guide.pdf, p.2)",
            },
            # 13. Structural Components
            {
                "id": "Q13",
                "category": "structural components",
                "query": "Monolithic musical pillars sa-re-ga-ma in Vijaya Vittala temple Ranga Mandapa",
                "expected_chunks": ["c52e4f68-b957-42e5-a04b-bd65acb7e475", "bc0e1d21-5688-44bd-9fa6-3a2f65828601"],
                "expected_desc": "56 musical pillars in Ranga Mandapa (Hampi_Vijayanagara_Guide.pdf, p.2)",
            },
            # 14. Structural Components / Material
            {
                "id": "Q14",
                "category": "structural components",
                "query": "What soft stone material was used for star-shaped Hoysala temple platforms?",
                "expected_chunks": ["5aa05424-f78b-4ede-b8bb-29b6f6e427bb"],
                "expected_desc": "Chloritic schist soapstone on star-shaped jagati (Belur_Halebidu_Hoysala_Guide.pdf, p.1)",
            },
            # 15. Cultural Context / Religion
            {
                "id": "Q15",
                "category": "cultural context",
                "query": "Jain Cave 4 at Badami Mahavira on Simhasana lion throne and Bahubali",
                "expected_chunks": ["511f03b9-f238-4353-9112-82014de82298"],
                "expected_desc": "Lord Mahavira on lion throne, Bahubali kayotsarga (Badami_Caves_Guide.pdf, p.3)",
            },
            # 16. Cultural Context
            {
                "id": "Q16",
                "category": "cultural context",
                "query": "Pattadakal coronation site for Early Chalukya kings on Malaprabha river",
                "expected_chunks": ["d2c053c3-7777-4371-ad12-7fac1771581c", "9b83c145-367e-4917-bc6b-6fd3e0230dbb"],
                "expected_desc": "Pattadakallu coronation site on west bank of Malaprabha (Pattadakal_UNESCO_Guide.pdf, p.1)",
            },
            # 17. Exact Keyword Query
            {
                "id": "Q17",
                "category": "exact keyword queries",
                "query": "monolithic Stone Chariot Garuda shrine Indian 50-rupee currency note",
                "expected_chunks": ["c52e4f68-b957-42e5-a04b-bd65acb7e475"],
                "expected_desc": "Stone Chariot at Vijaya Vittala temple (Hampi_Vijayanagara_Guide.pdf, p.2)",
            },
            # 18. Exact Keyword Query
            {
                "id": "Q18",
                "category": "exact keyword queries",
                "query": "Lad Khan temple timber-imitation joinery stone roof slabs floral lattice",
                "expected_chunks": ["92b35baa-62d9-47fb-88a7-297e3a2aa93c"],
                "expected_desc": "Lad Khan assembly hall and Shiva shrine (Aihole_Heritage_Guide.pdf, p.2)",
            },
            # 19. Semantic Paraphrase
            {
                "id": "Q19",
                "category": "semantic paraphrases",
                "query": "Where can I see rock-cut shrines situated directly beside a sacred lake?",
                "expected_chunks": ["511f03b9-f238-4353-9112-82014de82298", "812a2c73-3120-48c5-b85f-319cf1e7dcb6"],
                "expected_desc": "Bhutanatha temple extending into Agastya Lake (Badami_Caves_Guide.pdf, p.3)",
            },
            # 20. Semantic Paraphrase
            {
                "id": "Q20",
                "category": "semantic paraphrases",
                "query": "Which medieval queen celebrated victory over Pallavas by building a grand temple?",
                "expected_chunks": ["aff8d390-d5a4-4361-bec5-4ae6246585fd"],
                "expected_desc": "Queen Lokamahadevi, Virupaksha temple (Pattadakal_UNESCO_Guide.pdf, p.2)",
            },
            # 21. Spelling Variant
            {
                "id": "Q21",
                "category": "spelling variants",
                "query": "Vatapi rock cut caverns Agastya Thirtha Bagalkote",
                "expected_chunks": ["812a2c73-3120-48c5-b85f-319cf1e7dcb6"],
                "expected_desc": "Vatapi capital of Chalukyas, Agastya Tirtha (Badami_Caves_Guide.pdf, p.1)",
            },
            # 22. Diacritic Variant
            {
                "id": "Q22",
                "category": "diacritic variants",
                "query": "Saṅgameśvara temple King Vijayāditya Pattadakallu Drāviḍa",
                "expected_chunks": ["0ffa2732-da98-43cd-aa18-8bc19e29e942"],
                "expected_desc": "Sangameshwara temple by King Vijayaditya 696-733 CE (Pattadakal_UNESCO_Guide.pdf, p.2)",
            },
            # 23. Related / Confusing Entities
            {
                "id": "Q23",
                "category": "related/confusing entities",
                "query": "Virupaksha temple dedicated to Lord Shiva at Hampi with 50-meter eastern gopuram",
                "expected_chunks": ["c52e4f68-b957-42e5-a04b-bd65acb7e475"],
                "expected_desc": "Virupaksha Temple at Hampi (Hampi_Vijayanagara_Guide.pdf, p.2)",
            },
            # 24. Related / Confusing Entities
            {
                "id": "Q24",
                "category": "related/confusing entities",
                "query": "Mallikarjuna temple at Pattadakal built by Queen Trailokyamahadevi",
                "expected_chunks": ["aff8d390-d5a4-4361-bec5-4ae6246585fd", "0ffa2732-da98-43cd-aa18-8bc19e29e942"],
                "expected_desc": "Mallikarjuna temple by Trailokyamahadevi (Pattadakal_UNESCO_Guide.pdf, p.2)",
            },
        ]

        total_questions = len(benchmark_queries)
        hits_at_1 = 0
        hits_at_5 = 0
        precisions_at_5 = []
        reciprocal_ranks = []
        timing_records = []
        bib_intrusions = 0
        duplicate_hits = 0
        total_retrieved_candidates = 0

        failed_weak_queries = []

        service = RAGRetrievalService(session=session)

        print(f"\nEXECUTING {total_questions} SOURCE-GROUNDED BENCHMARK QUERIES...")
        print("-" * 80)

        for q in benchmark_queries:
            q_id = q["id"]
            q_cat = q["category"]
            q_text = q["query"]
            expected_cids = set(q["expected_chunks"])
            expected_desc = q["expected_desc"]

            req = RetrievalDiagnosticRequest(
                query=q_text,
                top_k=5,
                dense_top_k=25,
                bm25_top_k=25,
                rerank_candidates=15,
                enable_reranker=True,
                filter_noise=True,
                suppress_duplicates=True,
            )

            resp = await service.retrieve_evidence(req)
            t = resp.timings_ms
            timing_records.append({
                "dense_ms": t.dense_ms or 0.0,
                "bm25_ms": t.bm25_ms or 0.0,
                "fusion_ms": t.fusion_ms or 0.0,
                "rerank_ms": t.rerank_ms or 0.0,
                "total_ms": t.total_ms or 0.0,
            })

            retrieved_chunks = resp.results
            total_retrieved_candidates += len(retrieved_chunks)

            # Check duplicates in retrieved results
            seen_cids = set()
            for cand in retrieved_chunks:
                if cand.chunk_id in seen_cids:
                    duplicate_hits += 1
                seen_cids.add(cand.chunk_id)

                # Check bibliography intrusion
                text_lower = cand.text.lower()
                sec_lower = (cand.section or "").lower()
                if "bibliography" in sec_lower or "references" in sec_lower or "isbn:" in text_lower:
                    bib_intrusions += 1

            # Determine rank of first relevant ground truth chunk
            first_relevant_rank = None
            relevant_in_top_5 = 0
            for rank_idx, cand in enumerate(retrieved_chunks, 1):
                if cand.chunk_id in expected_cids:
                    if first_relevant_rank is None:
                        first_relevant_rank = rank_idx
                    relevant_in_top_5 += 1

            # Calculate Hit@1, Recall@5, Precision@5, MRR
            if first_relevant_rank == 1:
                hits_at_1 += 1

            if first_relevant_rank is not None and first_relevant_rank <= 5:
                hits_at_5 += 1
                reciprocal_ranks.append(1.0 / first_relevant_rank)
            else:
                reciprocal_ranks.append(0.0)

            # Precision@5 = (relevant chunks retrieved in top 5) / (total retrieved up to 5)
            p_at_5 = relevant_in_top_5 / max(len(retrieved_chunks), 1)
            precisions_at_5.append(p_at_5)

            # Log weak or failed queries
            if first_relevant_rank != 1:
                top_results_summary = [
                    f"Rank {idx}: [Doc: {c.source_filename} (p.{c.page_number}), Sec: '{c.section}'] (Score: {c.reranker_score})"
                    for idx, c in enumerate(retrieved_chunks[:3], 1)
                ]
                failed_weak_queries.append({
                    "id": q_id,
                    "category": q_cat,
                    "query": q_text,
                    "expected": expected_desc,
                    "first_rank": first_relevant_rank,
                    "top_results": top_results_summary,
                })

            status_str = f"Rank {first_relevant_rank}" if first_relevant_rank else "MISSED"
            print(f"[{q_id}] ({q_cat:20s}) -> {status_str:10s} | Total: {t.total_ms:5.1f}ms | Query: {q_text[:45]}...")

        # Aggregate Metrics Calculation
        hit_at_1_pct = (hits_at_1 / total_questions) * 100.0
        recall_at_5_pct = (hits_at_5 / total_questions) * 100.0
        avg_precision_at_5 = (sum(precisions_at_5) / total_questions) * 100.0
        mrr = sum(reciprocal_ranks) / total_questions

        bib_intrusion_rate = (bib_intrusions / max(total_retrieved_candidates, 1)) * 100.0
        duplicate_rate = (duplicate_hits / max(total_retrieved_candidates, 1)) * 100.0

        # Latency statistics (Overall & Warm steady-state excluding first cold query)
        avg_dense = sum(r["dense_ms"] for r in timing_records) / total_questions
        avg_bm25 = sum(r["bm25_ms"] for r in timing_records) / total_questions
        avg_fusion = sum(r["fusion_ms"] for r in timing_records) / total_questions
        avg_rerank = sum(r["rerank_ms"] for r in timing_records) / total_questions
        avg_total = sum(r["total_ms"] for r in timing_records) / total_questions

        warm_records = timing_records[1:] if len(timing_records) > 1 else timing_records
        warm_total = sum(r["total_ms"] for r in warm_records) / len(warm_records)
        warm_dense = sum(r["dense_ms"] for r in warm_records) / len(warm_records)
        warm_rerank = sum(r["rerank_ms"] for r in warm_records) / len(warm_records)

        print("\n" + "=" * 80)
        print("EXPANDED RETRIEVAL BENCHMARK RESULTS")
        print("=" * 80)
        print(f"Corpus Documents            : {len(doc_ids)}")
        print(f"Corpus Pages                : {total_pages}")
        print(f"Corpus Total Chunks         : {len(chunks)}")
        print(f"Benchmark Question Count    : {total_questions}")
        print("-" * 80)
        print(f"Hit@1 Rate                  : {hit_at_1_pct:.2f}% ({hits_at_1}/{total_questions})")
        print(f"Recall@5                    : {recall_at_5_pct:.2f}% ({hits_at_5}/{total_questions})")
        print(f"Precision@5                 : {avg_precision_at_5:.2f}%")
        print(f"Mean Reciprocal Rank (MRR)  : {mrr:.4f}")
        print(f"Bibliography Intrusion Rate : {bib_intrusion_rate:.2f}% ({bib_intrusions} leaks)")
        print(f"Duplicate Result Rate       : {duplicate_rate:.2f}% ({duplicate_hits} dups)")
        print("-" * 80)
        print("MEASURED LATENCIES (AVERAGE ACROSS ALL 24 QUERIES):")
        print(f"  - Dense Vector Latency     : {avg_dense:6.2f} ms")
        print(f"  - Sparse BM25 Latency      : {avg_bm25:6.2f} ms")
        print(f"  - RRF Fusion Latency       : {avg_fusion:6.2f} ms")
        print(f"  - Cross-Encoder Re-rank    : {avg_rerank:6.2f} ms")
        print(f"  - Total End-to-End Latency : {avg_total:6.2f} ms")
        print("-" * 80)
        print(f"STEADY-STATE WARM AVERAGE (Q2-Q24):")
        print(f"  - Dense Warm Latency       : {warm_dense:6.2f} ms")
        print(f"  - Re-rank Warm Latency     : {warm_rerank:6.2f} ms")
        print(f"  - Total Warm Latency       : {warm_total:6.2f} ms")
        print("=" * 80)

        print("\n" + "=" * 80)
        print("FAILURE & WEAK QUERY ANALYSIS")
        print("=" * 80)
        if not failed_weak_queries:
            print("Zero weak or failed queries! All 24 queries achieved Rank 1.")
        else:
            for item in failed_weak_queries:
                print(f"\nQuery [{item['id']}]: '{item['query']}'")
                print(f"  Category          : {item['category']}")
                print(f"  Expected Evidence : {item['expected']}")
                print(f"  First Relevant Pos: Rank {item['first_rank'] if item['first_rank'] else 'MISSED (>5)'}")
                print(f"  Top Retrieved:")
                for r in item["top_results"]:
                    print(f"    {r}")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
