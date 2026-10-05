"""
Inspect Cross-Encoder scores on relevant vs unsupported queries.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.application.rag.service import RAGRetrievalService
from app.application.rag.schemas import RetrievalDiagnosticRequest


async def inspect_scores():
    session_factory = get_session_factory()
    async with session_factory() as session:
        service = RAGRetrievalService(session=session)

        test_queries = [
            ("Relevant (High)", "Who commissioned the Belur Chennakeshava temple?"),
            ("Relevant (High)", "Which queen built the Virupaksha temple at Pattadakal?"),
            ("Relevant (Medium)", "monolithic Stone Chariot Garuda shrine"),
            ("Relevant (Paraphrase)", "Where can I see rock-cut shrines situated directly beside a sacred lake?"),
            ("Unsupported (General)", "What is the capital city of France?"),
            ("Unsupported (Sports)", "Who won the 2024 ICC T20 cricket world cup?"),
            ("Unsupported (Science)", "How does nuclear fusion generate energy in the sun?"),
            ("Unsupported (Tourism outside KA)", "What are the visiting hours for the Taj Mahal in Agra?"),
        ]

        print("=" * 80)
        print("CROSS-ENCODER SCORE INSPECTION")
        print("=" * 80)

        for label, q in test_queries:
            req = RetrievalDiagnosticRequest(
                query=q,
                top_k=3,
                dense_top_k=15,
                bm25_top_k=15,
                rerank_candidates=10,
                enable_reranker=True,
                filter_noise=True,
                suppress_duplicates=True,
            )
            resp = await service.retrieve_evidence(req)
            top_score = resp.results[0].reranker_score if resp.results else None
            top_doc = resp.results[0].source_filename if resp.results else "None"
            top_sec = resp.results[0].section if resp.results else "None"
            top_score_str = f"{top_score:7.4f}" if top_score is not None else "   None"
            print(f"[{label:28s}] Top Score: {top_score_str} | Doc: {top_doc} ({top_sec}) | Q: '{q}'")

if __name__ == "__main__":
    asyncio.run(inspect_scores())
