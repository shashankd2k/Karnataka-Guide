import asyncio
import json
import os
import sys
import time
import hashlib
from typing import Dict, Any, List

from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.chunk import DocumentChunk
from app.infrastructure.db.models.document import Document
from app.application.rag.schemas import RetrievalCandidate, RetrievalDiagnosticRequest
from app.application.conversation.grounding_guard import GroundingGuard
from app.application.rag.prompt_builder import build_grounded_prompt
from app.application.rag.service import RAGRetrievalService
from app.application.conversation.citation_formatter import (
    extract_authoritative_citations,
    sanitize_model_citations,
)
from app.application.translation.service import TranslationService
from app.infrastructure.llm.ollama import OllamaLLMProvider
from app.core.config import get_settings

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ACTIVE_GEN_ID = "1a2c6365-1bee-4478-9599-a706ee5c7221"

async def main():
    print("=" * 80)
    print("FOCUSED ANSWER AND CITATION VALIDATION (15 vs 10 CANDIDATES)")
    print("=" * 80)
    settings = get_settings()
    print(f"Production Settings:")
    print(f"  RETRIEVAL_RERANK_CANDIDATES: {settings.RETRIEVAL_RERANK_CANDIDATES}")
    print(f"  OLLAMA_MODEL: {settings.OLLAMA_MODEL}")
    print(f"  OLLAMA_TEMPERATURE: {settings.OLLAMA_TEMPERATURE}")
    print(f"  OLLAMA_NUM_CTX: {settings.OLLAMA_NUM_CTX}")
    num_threads = getattr(settings, "OLLAMA_NUM_THREAD", 2)
    print(f"  OLLAMA_NUM_THREAD: {num_threads} (default in OllamaLLMProvider)")
    print(f"  OLLAMA_MAX_CONTEXT_CHARS: {settings.OLLAMA_MAX_CONTEXT_CHARS}")
    print(f"  OLLAMA_KEEP_ALIVE: {settings.OLLAMA_KEEP_ALIVE}")
    print(f"  OLLAMA_TIMEOUT_SECONDS: {settings.OLLAMA_TIMEOUT_SECONDS}")

    factory = get_session_factory()
    async with factory() as db_session:
        # 1. Verify Active Generation and load all chunks
        stmt_chunks = select(DocumentChunk).where(
            DocumentChunk.generation_id == ACTIVE_GEN_ID
        ).order_by(DocumentChunk.chunk_index)
        db_chunks = (await db_session.execute(stmt_chunks)).scalars().all()
        print(f"\nLoaded {len(db_chunks)} chunks for active generation {ACTIVE_GEN_ID} from MySQL.")

        # Document provenance
        docs = (await db_session.execute(select(Document))).scalars().all()
        doc_map = {str(d.id): d.filename for d in docs}

        chunk_dict: Dict[str, DocumentChunk] = {str(c.id): c for c in db_chunks}

        # Load previous benchmark results
        bench_path = "/app/scratch/level2_rerank_experiment/benchmark_results.json"
        with open(bench_path, "r", encoding="utf-8") as f:
            bench_data = json.load(f)

        queries_data = bench_data["queries"]
        print(f"Loaded {len(queries_data)} queries from {bench_path}")

        # Reconstruct candidates helper
        def build_candidates_from_evidence(ev_list: List[Dict[str, Any]]) -> List[RetrievalCandidate]:
            cands = []
            for rank_idx, item in enumerate(ev_list, 1):
                cid = item["chunk_id"]
                c_db = chunk_dict[cid]
                # Validate text hash matches
                real_text = c_db.chunk_text
                cand = RetrievalCandidate(
                    chunk_id=cid,
                    document_id=str(c_db.document_id),
                    source_filename=doc_map.get(str(c_db.document_id), item["doc"]),
                    page_number=c_db.page_number,
                    section=c_db.section_header,
                    text=real_text,
                    chunk_index=c_db.chunk_index,
                    token_count=c_db.token_count,
                    generation_id=ACTIVE_GEN_ID,
                    reranker_score=item["score"],
                    final_rank=rank_idx,
                )
                cands.append(cand)
            return cands

        # 2. Reconstruct Model Inputs for all 24 queries
        print("\n" + "=" * 80)
        print("RECONSTRUCTING MODEL INPUTS (ALL 24 QUERIES)")
        print("=" * 80)

        identical_20_checks = []
        differing_4_inputs = {}

        for qid in sorted(queries_data.keys()):
            q_info = queries_data[qid]
            q_text = q_info["query_text"]
            r1 = q_info["rep1_15_then_10"]

            ev15 = r1["arm_15"]["final_evidence"]
            ev10 = r1["arm_10"]["final_evidence"]

            cands_15 = build_candidates_from_evidence(ev15)
            cands_10 = build_candidates_from_evidence(ev10)

            # Build grounded prompt
            sys_15, user_15, labels_15 = build_grounded_prompt(
                query=q_text,
                candidates=cands_15,
                language="en",
                max_chars=settings.OLLAMA_MAX_CONTEXT_CHARS,
            )
            cits_15 = extract_authoritative_citations(
                candidates=cands_15,
                active_generation_id=ACTIVE_GEN_ID,
                max_passages=3,
            )

            sys_10, user_10, labels_10 = build_grounded_prompt(
                query=q_text,
                candidates=cands_10,
                language="en",
                max_chars=settings.OLLAMA_MAX_CONTEXT_CHARS,
            )
            cits_10 = extract_authoritative_citations(
                candidates=cands_10,
                active_generation_id=ACTIVE_GEN_ID,
                max_passages=3,
            )

            is_sys_ident = (sys_15 == sys_10)
            is_user_ident = (user_15 == user_10)
            is_labels_ident = (labels_15 == labels_10)
            is_cits_ident = (cits_15 == cits_10)

            if qid in ["Q11", "Q14", "Q15", "Q18"]:
                differing_4_inputs[qid] = {
                    "query_text": q_text,
                    "arm_15": {
                        "system_prompt": sys_15,
                        "user_prompt": user_15,
                        "authorized_labels": labels_15,
                        "authoritative_citations": cits_15,
                        "top_5_ids": [c.chunk_id for c in cands_15],
                        "top_5_scores": [c.reranker_score for c in cands_15],
                    },
                    "arm_10": {
                        "system_prompt": sys_10,
                        "user_prompt": user_10,
                        "authorized_labels": labels_10,
                        "authoritative_citations": cits_10,
                        "top_5_ids": [c.chunk_id for c in cands_10],
                        "top_5_scores": [c.reranker_score for c in cands_10],
                    },
                    "system_prompt_identical": is_sys_ident,
                    "user_prompt_identical": is_user_ident,
                    "labels_identical": is_labels_ident,
                    "citations_identical": is_cits_ident,
                }
            else:
                identical_20_checks.append({
                    "query_id": qid,
                    "system_prompt_identical": is_sys_ident,
                    "user_prompt_identical": is_user_ident,
                    "labels_identical": is_labels_ident,
                    "citations_identical": is_cits_ident,
                })

        all_20_ident = all(
            c["system_prompt_identical"] and c["user_prompt_identical"] and c["labels_identical"] and c["citations_identical"]
            for c in identical_20_checks
        )
        print(f"20 Identical-Retrieval Queries Prompt Comparison:")
        print(f"  All 20 queries have 100% IDENTICAL system prompt: {all(c['system_prompt_identical'] for c in identical_20_checks)}")
        print(f"  All 20 queries have 100% IDENTICAL user prompt: {all(c['user_prompt_identical'] for c in identical_20_checks)}")
        print(f"  All 20 queries have 100% IDENTICAL authorized labels: {all(c['labels_identical'] for c in identical_20_checks)}")
        print(f"  All 20 queries have 100% IDENTICAL authoritative citations: {all(c['citations_identical'] for c in identical_20_checks)}")
        print(f"  OVERALL 20-QUERY IDENTITY VERIFIED: {all_20_ident}")

        print("\n4 Changed-Evidence Queries Prompt Comparison Summary:")
        for qid in ["Q11", "Q14", "Q15", "Q18"]:
            diff_info = differing_4_inputs[qid]
            print(f"  [{qid}]: User Prompt Identical: {diff_info['user_prompt_identical']}, Labels Identical: {diff_info['labels_identical']}, Citations Identical: {diff_info['citations_identical']}")

        # 3. Bounded Paired LLM Generation Checks (Q11, Q14, Q15, Q18 in English)
        print("\n" + "=" * 80)
        print("BOUNDED PAIRED LLM GENERATION CHECKS (8 ENGLISH CALLS, SERIAL)")
        print("=" * 80)

        llm_provider = OllamaLLMProvider()
        llm_results = {}

        for qid in ["Q11", "Q14", "Q15", "Q18"]:
            diff_info = differing_4_inputs[qid]
            q_text = diff_info["query_text"]
            print(f"\n--- Processing {qid}: '{q_text}' ---")

            llm_results[qid] = {}

            # Execute Arm 15
            print(f"  Executing Arm 15 LLM generation...")
            t0 = time.perf_counter()
            raw_15 = await llm_provider.generate_text(
                system_prompt=diff_info["arm_15"]["system_prompt"],
                user_prompt=diff_info["arm_15"]["user_prompt"],
                temperature=settings.OLLAMA_TEMPERATURE,
            )
            dur_15 = round((time.perf_counter() - t0) * 1000, 2)
            san_15 = sanitize_model_citations(raw_15, diff_info["arm_15"]["authorized_labels"])
            print(f"  Arm 15 completed in {dur_15} ms")
            print(f"  Arm 15 Sanitized Answer: {san_15}")

            llm_results[qid]["arm_15"] = {
                "duration_ms": dur_15,
                "raw_answer": raw_15,
                "sanitized_answer": san_15,
                "authorized_labels": diff_info["arm_15"]["authorized_labels"],
                "authoritative_citations": diff_info["arm_15"]["authoritative_citations"],
                "top_5_ids": diff_info["arm_15"]["top_5_ids"],
                "top_5_scores": diff_info["arm_15"]["top_5_scores"],
            }

            # Execute Arm 10
            print(f"  Executing Arm 10 LLM generation...")
            t0 = time.perf_counter()
            raw_10 = await llm_provider.generate_text(
                system_prompt=diff_info["arm_10"]["system_prompt"],
                user_prompt=diff_info["arm_10"]["user_prompt"],
                temperature=settings.OLLAMA_TEMPERATURE,
            )
            dur_10 = round((time.perf_counter() - t0) * 1000, 2)
            san_10 = sanitize_model_citations(raw_10, diff_info["arm_10"]["authorized_labels"])
            print(f"  Arm 10 completed in {dur_10} ms")
            print(f"  Arm 10 Sanitized Answer: {san_10}")

            llm_results[qid]["arm_10"] = {
                "duration_ms": dur_10,
                "raw_answer": raw_10,
                "sanitized_answer": san_10,
                "authorized_labels": diff_info["arm_10"]["authorized_labels"],
                "authoritative_citations": diff_info["arm_10"]["authoritative_citations"],
                "top_5_ids": diff_info["arm_10"]["top_5_ids"],
                "top_5_scores": diff_info["arm_10"]["top_5_scores"],
            }

        # 4. Paired Kannada check for Q14
        print("\n" + "=" * 80)
        print("PAIRED KANNADA CHECK FOR Q14 (TRANSLATION + RETRIEVAL + LLM + TRANSLATION)")
        print("=" * 80)
        kannada_q14_query = "ನಕ್ಷತ್ರಾಕಾರದ ಹೊಯ್ಸಳ ದೇವಾಲಯದ ಜಗತಿಗೆ ಯಾವ ಮೃದುವಾದ ಕಲ್ಲಿನ ವಸ್ತುವನ್ನು ಬಳಸಲಾಗಿತ್ತು?"
        print(f"Kannada Query Text: {kannada_q14_query}")
        print("Label: Additional case outside the canonical 24-query benchmark")

        trans_service = TranslationService()
        rag_service = RAGRetrievalService(session=db_session)
        guard = GroundingGuard()

        # Step 1: Translate query
        t0 = time.perf_counter()
        prep_q, ent_list = trans_service.prepare_retrieval_query(kannada_q14_query)
        en_search_query = await trans_service.translate_retrieval_query(
            query=kannada_q14_query,
            from_lang="kn",
            to_lang="en",
        )
        q_trans_ms = round((time.perf_counter() - t0) * 1000, 2)
        print(f"Translated query to English in {q_trans_ms} ms: '{en_search_query}'")

        kannada_results = {}
        for arm_cand_limit, arm_name in [(15, "arm_15"), (10, "arm_10")]:
            print(f"\nExecuting Kannada pipeline for {arm_name} (candidates={arm_cand_limit})...")
            t_arm_start = time.perf_counter()
            req = RetrievalDiagnosticRequest(
                query=en_search_query,
                top_k=5,
                dense_top_k=25,
                bm25_top_k=25,
                rerank_candidates=arm_cand_limit,
                enable_reranker=True,
                filter_noise=True,
                suppress_duplicates=True,
            )
            ret_resp = await rag_service.retrieve_evidence(req)
            gr_res = guard.evaluate(
                candidates=ret_resp.results,
                language="kn",
                active_generation_id=ACTIVE_GEN_ID,
            )

            # Build prompt
            sys_pr, user_pr, auth_lbls = build_grounded_prompt(
                query=en_search_query,
                candidates=ret_resp.results,
                language="en",
                max_chars=settings.OLLAMA_MAX_CONTEXT_CHARS,
            )
            cits = extract_authoritative_citations(
                candidates=ret_resp.results,
                active_generation_id=ACTIVE_GEN_ID,
                max_passages=3,
            )

            # LLM English generation
            t_llm = time.perf_counter()
            en_raw = await llm_provider.generate_text(
                system_prompt=sys_pr,
                user_prompt=user_pr,
                temperature=settings.OLLAMA_TEMPERATURE,
            )
            en_llm_ms = round((time.perf_counter() - t_llm) * 1000, 2)
            en_san = sanitize_model_citations(en_raw, auth_lbls)

            # Response translation to Kannada
            t_trans_resp = time.perf_counter()
            kn_answer = await trans_service.translate_response(
                response=en_san,
                from_lang="en",
                to_lang="kn",
            )
            resp_trans_ms = round((time.perf_counter() - t_trans_resp) * 1000, 2)
            total_kn_ms = round((time.perf_counter() - t_arm_start) * 1000, 2)

            print(f"  {arm_name} LLM generated English in {en_llm_ms} ms: '{en_san}'")
            print(f"  {arm_name} Translated to Kannada in {resp_trans_ms} ms: '{kn_answer}'")
            print(f"  {arm_name} Total pipeline duration: {total_kn_ms} ms")

            kannada_results[arm_name] = {
                "candidate_limit": arm_cand_limit,
                "retrieval_timings_ms": ret_resp.timings_ms.model_dump(),
                "llm_duration_ms": en_llm_ms,
                "response_translation_ms": resp_trans_ms,
                "total_duration_ms": total_kn_ms,
                "english_raw_answer": en_raw,
                "english_sanitized_answer": en_san,
                "kannada_final_answer": kn_answer,
                "authorized_labels": auth_lbls,
                "authoritative_citations": cits,
                "top_5_ids": [c.chunk_id for c in ret_resp.results],
                "top_5_scores": [c.reranker_score for c in ret_resp.results],
            }

        # 5. Out-of-corpus fallback checks
        print("\n" + "=" * 80)
        print("OUT-OF-CORPUS FALLBACK CHECKS")
        print("=" * 80)

        fallback_checks = {}

        # English out-of-corpus query
        en_ooc_query = "What is the ticket price for the Eiffel Tower in Paris?"
        print(f"Testing English Out-of-Corpus Query: '{en_ooc_query}'")
        for cand_lim, arm_name in [(15, "arm_15"), (10, "arm_10")]:
            req = RetrievalDiagnosticRequest(
                query=en_ooc_query,
                top_k=5,
                dense_top_k=25,
                bm25_top_k=25,
                rerank_candidates=cand_lim,
                enable_reranker=True,
                filter_noise=True,
                suppress_duplicates=True,
            )
            resp = await rag_service.retrieve_evidence(req)
            gr = guard.evaluate(
                candidates=resp.results,
                language="en",
                active_generation_id=ACTIVE_GEN_ID,
            )
            top_score = resp.results[0].reranker_score if resp.results else None
            expected_msg = "Information is not available in the knowledge base."
            is_match = (gr.fallback_message == expected_msg) and (not gr.is_grounded)
            print(f"  {arm_name}: Top score: {top_score:.4f}, is_grounded: {gr.is_grounded}, message: '{gr.fallback_message}' (Match: {is_match})")
            fallback_checks[f"en_{arm_name}"] = {
                "query": en_ooc_query,
                "candidate_limit": cand_lim,
                "top_score": top_score,
                "is_grounded": gr.is_grounded,
                "fallback_message": gr.fallback_message,
                "expected_message": expected_msg,
                "exact_match": is_match,
            }

        # Kannada out-of-corpus query
        kn_ooc_query = "ಪ್ಯಾರಿಸ್‌ನಲ್ಲಿರುವ ಐಫೆಲ್ ಗೋಪುರದ ಟಿಕೆಟ್ ದರ ಎಷ್ಟು?"
        print(f"\nTesting Kannada Out-of-Corpus Query: '{kn_ooc_query}'")
        kn_trans_query = await trans_service.translate_retrieval_query(
            query=kn_ooc_query,
            from_lang="kn",
            to_lang="en",
        )
        print(f"  Translated retrieval query: '{kn_trans_query}'")
        for cand_lim, arm_name in [(15, "arm_15"), (10, "arm_10")]:
            req = RetrievalDiagnosticRequest(
                query=kn_trans_query,
                top_k=5,
                dense_top_k=25,
                bm25_top_k=25,
                rerank_candidates=cand_lim,
                enable_reranker=True,
                filter_noise=True,
                suppress_duplicates=True,
            )
            resp = await rag_service.retrieve_evidence(req)
            gr = guard.evaluate(
                candidates=resp.results,
                language="kn",
                active_generation_id=ACTIVE_GEN_ID,
            )
            top_score = resp.results[0].reranker_score if resp.results else None
            expected_msg = "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."
            is_match = (gr.fallback_message == expected_msg) and (not gr.is_grounded)
            print(f"  {arm_name}: Top score: {top_score:.4f}, is_grounded: {gr.is_grounded}, message: '{gr.fallback_message}' (Match: {is_match})")
            fallback_checks[f"kn_{arm_name}"] = {
                "query": kn_ooc_query,
                "candidate_limit": cand_lim,
                "top_score": top_score,
                "is_grounded": gr.is_grounded,
                "fallback_message": gr.fallback_message,
                "expected_message": expected_msg,
                "exact_match": is_match,
            }

        # Export full results to JSON
        export_data = {
            "metadata": {
                "active_generation_id": ACTIVE_GEN_ID,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "settings": {
                    "RETRIEVAL_RERANK_CANDIDATES_PRODUCTION": settings.RETRIEVAL_RERANK_CANDIDATES,
                    "OLLAMA_MODEL": settings.OLLAMA_MODEL,
                    "OLLAMA_TEMPERATURE": settings.OLLAMA_TEMPERATURE,
                    "OLLAMA_NUM_CTX": settings.OLLAMA_NUM_CTX,
                    "OLLAMA_NUM_THREAD": getattr(settings, "OLLAMA_NUM_THREAD", 2),
                    "OLLAMA_MAX_CONTEXT_CHARS": settings.OLLAMA_MAX_CONTEXT_CHARS,
                    "OLLAMA_KEEP_ALIVE": settings.OLLAMA_KEEP_ALIVE,
                    "OLLAMA_TIMEOUT_SECONDS": settings.OLLAMA_TIMEOUT_SECONDS,
                },
                "execution_mode": "component_replay_with_production_adapter",
            },
            "identical_20_queries_input_audit": {
                "total_queries_checked": len(identical_20_checks),
                "all_inputs_identical": all_20_ident,
                "queries": identical_20_checks,
            },
            "differing_4_queries_reconstructed_inputs": differing_4_inputs,
            "differing_4_queries_llm_answers": llm_results,
            "q14_kannada_validation": {
                "kannada_query": kannada_q14_query,
                "translated_retrieval_query": en_search_query,
                "query_translation_duration_ms": q_trans_ms,
                "results": kannada_results,
            },
            "out_of_corpus_fallback_checks": fallback_checks,
        }

        out_path = "/app/scratch/level2_rerank_experiment/answer_validation_results.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully exported validation results to {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
