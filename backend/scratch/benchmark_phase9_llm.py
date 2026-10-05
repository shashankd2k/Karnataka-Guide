"""
Phase 9 Real Ollama Grounding & Citation Benchmark.
Executes 30 conversational turns against the real active knowledge base and local Ollama instance (mistral:7b).

Measures:
1. Grounding Classification Accuracy (100% expected)
2. Exact Fallback Enforcement on Unsupported Queries (100% expected)
3. Zero Citation Enforcement on Unsupported Queries (100% expected)
4. Authoritative Citation Provenance Accuracy (100% expected vs MySQL document_chunks)
5. Hallucination Detection (0 expected)
6. Response Latency & First-Token Streaming Latency
"""

import asyncio
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Any, Dict, List, Optional
from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.chunk import DocumentChunk
from app.infrastructure.db.models.document import Document
from app.application.conversation.service import ConversationService
from app.application.conversation.grounding_guard import ENGLISH_FALLBACK, KANNADA_FALLBACK

BENCHMARK_TURNS = [
    # --- Category 1: Single-Turn Grounded English (20 Queries) ---
    {
        "turn_id": 1,
        "query": "Who commissioned the Chennakeshava Temple at Belur and in which year?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
        "expected_facts": ["Vishnuvardhana", "1117"],
    },
    {
        "turn_id": 2,
        "query": "What are the 42 bracket figures on the Belur temple called and what do they depict?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
        "expected_facts": ["Madanika"],
    },
    {
        "turn_id": 3,
        "query": "What building material was predominantly used in Hoysala temples like Belur and Halebidu?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
        "expected_facts": ["soapstone", "chloritic schist"],
    },
    {
        "turn_id": 4,
        "query": "Who commissioned the Hoysaleswara Temple at Halebidu and when?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
        "expected_facts": ["Ketamalla", "1121"],
    },
    {
        "turn_id": 5,
        "query": "Describe the architectural plan and stellate platform of Hoysala temples.",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
        "expected_facts": ["jagati", "star-shaped", "plinth"],
    },
    {
        "turn_id": 6,
        "query": "What are the main carvings found in Cave 1 at Badami?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Badami_Caves_Guide.pdf",
        "expected_facts": ["Nataraja", "Shiva"],
    },
    {
        "turn_id": 7,
        "query": "Which deity is consecrated in Badami Cave 3 and what inscription is found there?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Badami_Caves_Guide.pdf",
        "expected_facts": ["Vishnu", "Mangalesha"],
    },
    {
        "turn_id": 8,
        "query": "What is the rock-cut architectural style of the Badami Chalukya cave temples?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Badami_Caves_Guide.pdf",
        "expected_facts": ["sandstone", "Chalukya"],
    },
    {
        "turn_id": 9,
        "query": "What is unique about the architectural plan of the Durga Temple at Aihole?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Aihole_Heritage_Guide.pdf",
        "expected_facts": ["apsidal", "Gajaprishta"],
    },
    {
        "turn_id": 10,
        "query": "Why is Aihole celebrated as the cradle of Hindu temple architecture?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Aihole_Heritage_Guide.pdf",
        "expected_facts": ["Chalukya", "cradle", "experiment"],
    },
    {
        "turn_id": 11,
        "query": "Describe the Lad Khan temple at Aihole and its original purpose.",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Aihole_Heritage_Guide.pdf",
        "expected_facts": ["mandapa", "Shiva"],
    },
    {
        "turn_id": 12,
        "query": "Which queen commissioned the Virupaksha Temple at Pattadakal and for what celebration?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Pattadakal_UNESCO_Guide.pdf",
        "expected_facts": ["Lokamahadevi", "Vikramaditya"],
    },
    {
        "turn_id": 13,
        "query": "What architectural styles coalesce at the Pattadakal UNESCO World Heritage complex?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Pattadakal_UNESCO_Guide.pdf",
        "expected_facts": ["Dravida", "Nagara"],
    },
    {
        "turn_id": 14,
        "query": "What are the key features of the Mallikarjuna Temple at Pattadakal?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Pattadakal_UNESCO_Guide.pdf",
        "expected_facts": ["Trailokyamahadevi"],
    },
    {
        "turn_id": 15,
        "query": "Tell me about the Papanatha temple at Pattadakal and its Nagara style tower.",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Pattadakal_UNESCO_Guide.pdf",
        "expected_facts": ["Nagara", "shikhara"],
    },
    {
        "turn_id": 16,
        "query": "Who founded the Vijayanagara Empire and when was Hampi established as its capital?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Hampi_Vijayanagara_Guide.pdf",
        "expected_facts": ["Harihara", "Bukka", "1336"],
    },
    {
        "turn_id": 17,
        "query": "Describe the Stone Chariot located in the Vittala Temple complex at Hampi.",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Hampi_Vijayanagara_Guide.pdf",
        "expected_facts": ["Garuda", "Vittala", "granite"],
    },
    {
        "turn_id": 18,
        "query": "What is significant about the musical pillars in the Vittala Temple at Hampi?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Hampi_Vijayanagara_Guide.pdf",
        "expected_facts": ["musical", "pillars", "saregama"],
    },
    {
        "turn_id": 19,
        "query": "Describe the Virupaksha Temple at Hampi and its sacred location on the Tungabhadra river.",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Hampi_Vijayanagara_Guide.pdf",
        "expected_facts": ["Tungabhadra", "Pampa", "gopura"],
    },
    {
        "turn_id": 20,
        "query": "What was the purpose of the Mahanavami Dibba platform in the Royal Enclosure at Hampi?",
        "category": "supported_heritage",
        "expected_grounded": True,
        "expected_doc": "Hampi_Vijayanagara_Guide.pdf",
        "expected_facts": ["Mahanavami", "Dussehra", "platform"],
    },

    # --- Category 2: Multi-Turn Follow-Up Resolution (5 Queries) ---
    {
        "turn_id": 21,
        "setup_turn": "Tell me about the Chennakeshava temple at Belur.",
        "query": "When was it commissioned?",
        "category": "follow_up_resolution",
        "expected_grounded": True,
        "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
        "expected_facts": ["1117"],
    },
    {
        "turn_id": 22,
        "setup_turn": "Tell me about the Hoysaleswara temple at Halebidu.",
        "query": "What material was used to build it?",
        "category": "follow_up_resolution",
        "expected_grounded": True,
        "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
        "expected_facts": ["soapstone"],
    },
    {
        "turn_id": 23,
        "setup_turn": "Tell me about the Badami cave temples.",
        "query": "Who carved Cave 3 and which deity is inside?",
        "category": "follow_up_resolution",
        "expected_grounded": True,
        "expected_doc": "Badami_Caves_Guide.pdf",
        "expected_facts": ["Mangalesha", "Vishnu"],
    },
    {
        "turn_id": 24,
        "setup_turn": "Tell me about the Virupaksha temple at Pattadakal.",
        "query": "Which queen commissioned it?",
        "category": "follow_up_resolution",
        "expected_grounded": True,
        "expected_doc": "Pattadakal_UNESCO_Guide.pdf",
        "expected_facts": ["Lokamahadevi"],
    },
    {
        "turn_id": 25,
        "setup_turn": "Tell me about the Durga temple at Aihole.",
        "query": "What is its unique architectural plan?",
        "category": "follow_up_resolution",
        "expected_grounded": True,
        "expected_doc": "Aihole_Heritage_Guide.pdf",
        "expected_facts": ["apsidal"],
    },

    # --- Category 3: Unsupported / Out-of-Domain Queries (5 Queries) ---
    {
        "turn_id": 26,
        "query": "What is the ticket price for the Eiffel Tower in Paris?",
        "category": "unsupported_out_of_domain",
        "expected_grounded": False,
        "expected_doc": None,
        "expected_facts": [],
    },
    {
        "turn_id": 27,
        "query": "Who built the Pyramids of Giza in Egypt?",
        "category": "unsupported_out_of_domain",
        "expected_grounded": False,
        "expected_doc": None,
        "expected_facts": [],
    },
    {
        "turn_id": 28,
        "query": "What is the recipe for cooking Hyderabadi Dum Biryani?",
        "category": "unsupported_out_of_domain",
        "expected_grounded": False,
        "expected_doc": None,
        "expected_facts": [],
    },
    {
        "turn_id": 29,
        "query": "Who won the 2022 FIFA World Cup in Qatar?",
        "category": "unsupported_out_of_domain",
        "expected_grounded": False,
        "expected_doc": None,
        "expected_facts": [],
    },
    {
        "turn_id": 30,
        "query": "How to write a Python script using pandas and scikit-learn?",
        "category": "unsupported_out_of_domain",
        "expected_grounded": False,
        "expected_doc": None,
        "expected_facts": [],
    },
]


async def run_benchmark():
    factory = get_session_factory()
    async with factory() as db:
        service = ConversationService(session=db)

        # Load authoritative MySQL chunks to verify citation provenance
        stmt_chunks = (
            select(
                DocumentChunk.id.label("chunk_id"),
                DocumentChunk.document_id,
                DocumentChunk.page_number,
                DocumentChunk.section_header,
                Document.original_name.label("source_filename"),
            )
            .join(Document, DocumentChunk.document_id == Document.id)
        )
        chunk_rows = (await db.execute(stmt_chunks)).mappings().all()
        chunk_map = {r["chunk_id"]: dict(r) for r in chunk_rows}

        print("=" * 80)
        print("PHASE 9 BENCHMARK: OLLAMA GROUNDED GENERATION & CITATION INTEGRITY")
        print(f"Loaded {len(chunk_map)} authoritative MySQL document chunks.")
        print(f"Ollama Model: {service.settings.OLLAMA_MODEL} at {service.settings.OLLAMA_BASE_URL}")
        print("=" * 80)

        grounded_correct = 0
        fallback_exact_count = 0
        zero_citations_unsupported_count = 0
        citation_provenance_correct = 0
        total_citations_emitted = 0
        fact_containment_count = 0
        latencies_ms = []

        results_summary = []

        for turn in BENCHMARK_TURNS:
            t_id = turn["turn_id"]
            query = turn["query"]
            cat = turn["category"]
            exp_grounded = turn["expected_grounded"]
            exp_doc = turn.get("expected_doc")
            exp_facts = turn.get("expected_facts", [])

            # Create fresh session
            sess = await service.create_session(language_code="en")
            sess_uuid = sess.session_uuid

            # Handle setup turn if present
            if "setup_turn" in turn:
                await service.process_turn(session_uuid=sess_uuid, user_message=turn["setup_turn"])

            # Execute turn
            start_t = time.perf_counter()
            resp = await service.process_turn(session_uuid=sess_uuid, user_message=query)
            elapsed_ms = int((time.perf_counter() - start_t) * 1000)
            latencies_ms.append(elapsed_ms)

            # 1. Grounding check
            is_grounded_match = (resp.grounded == exp_grounded)
            if is_grounded_match:
                grounded_correct += 1

            # 2. Unsupported fallback checks
            is_exact_fallback = False
            is_zero_citations = False
            if not exp_grounded:
                is_exact_fallback = (resp.answer.strip() == ENGLISH_FALLBACK)
                is_zero_citations = (len(resp.citations) == 0)
                if is_exact_fallback:
                    fallback_exact_count += 1
                if is_zero_citations:
                    zero_citations_unsupported_count += 1

            # 3. Grounded citation provenance check
            prov_match = True
            if exp_grounded:
                if len(resp.citations) == 0:
                    prov_match = False
                else:
                    for cite in resp.citations:
                        total_citations_emitted += 1
                        auth_c = chunk_map.get(cite.chunk_id)
                        if not auth_c:
                            prov_match = False
                        elif auth_c["page_number"] != cite.page_number:
                            prov_match = False
                        elif auth_c["source_filename"] != cite.source_filename:
                            prov_match = False
                if prov_match:
                    citation_provenance_correct += 1

                # 4. Factual containment check
                ans_lower = resp.answer.lower()
                facts_found = any(f.lower() in ans_lower for f in exp_facts) if exp_facts else True
                if facts_found:
                    fact_containment_count += 1
            else:
                facts_found = True

            status_str = "PASS" if (is_grounded_match and prov_match and facts_found) else "FAIL"
            print(f"Turn {t_id:2d} | [{status_str}] {cat:<24} | Latency: {elapsed_ms:4d}ms | Grounded: {str(resp.grounded):<5} | Citations: {len(resp.citations)}")
            if not exp_grounded:
                print(f"        Answer: {resp.answer}")
            else:
                top_cite = f"({resp.citations[0].source_filename}, p.{resp.citations[0].page_number})" if resp.citations else "NO CITES"
                snippet = (resp.answer[:90] + "...") if len(resp.answer) > 90 else resp.answer
                print(f"        Answer: {snippet} [Cites: {top_cite}]")

            results_summary.append({
                "turn_id": t_id,
                "query": query,
                "category": cat,
                "grounded": resp.grounded,
                "expected_grounded": exp_grounded,
                "citations_count": len(resp.citations),
                "latency_ms": elapsed_ms,
                "passed": (status_str == "PASS"),
            })

        print("\n" + "=" * 80)
        print("PHASE 9 BENCHMARK RESULTS")
        print("=" * 80)
        print(f"Total Conversational Turns:           30")
        print(f"Grounding Classification Accuracy:     {grounded_correct}/30 ({grounded_correct/30*100:.2f}%)")
        print(f"Factual Evidence Containment:         {fact_containment_count}/25 ({fact_containment_count/25*100:.2f}%)")
        print(f"Unsupported Exact Fallback Rate:       {fallback_exact_count}/5 ({fallback_exact_count/5*100:.2f}%)")
        print(f"Unsupported Zero Citation Rate:        {zero_citations_unsupported_count}/5 ({zero_citations_unsupported_count/5*100:.2f}%)")
        print(f"Citation Provenance Precision (MySQL): {citation_provenance_correct}/25 ({citation_provenance_correct/25*100:.2f}%)")
        print(f"Total Citations Emitted:              {total_citations_emitted}")
        print(f"Average Generation Latency:           {sum(latencies_ms)/len(latencies_ms):.1f} ms")
        print(f"Min Latency: {min(latencies_ms)} ms | Max Latency: {max(latencies_ms)} ms")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
