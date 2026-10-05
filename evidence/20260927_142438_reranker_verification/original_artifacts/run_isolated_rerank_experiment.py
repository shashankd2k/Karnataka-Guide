"""
Isolated Level 2 Reranker Experiment: 15 vs 10 Candidates.
Strictly adheres to governance instructions:
- Single benchmark process with single loaded Cross-Encoder instance for both arms.
- Cold model initialization measured separately.
- Dedicated warm-up execution explicitly excluded from measured dataset.
- 24 canonical queries evaluated across 2 paired repetitions:
    Repetition 1: Arm 15 -> Arm 10
    Repetition 2: Arm 10 -> Arm 15
  Total measured arm executions = 24 * 4 = 96.
- Ordered candidate set prepared once per query via production Dense + BM25 + RRF;
  fresh independent deep copies provided to Arm 15 (top 15) and Arm 10 (top 10).
- Production post-rerank pipeline preserved:
    1. Cross-Encoder reranking
    2. filter_noise_chunks (score-independent)
    3. suppress_duplicate_chunks (order-dependent)
    4. Top-5 final evidence selection
- Canonical metrics calculated per arm and query:
    Hit@1, Recall@5, Reciprocal Rank, Bibliography Intrusions
- Latency isolation:
    Reranker-only latency (measured via high-resolution perf_counter_ns)
    Separately recorded: dense_ms, bm25_ms, fusion_ms, filter_ms
- GroundingGuard verification against score >= -6.0 and out-of-corpus fallback check.
- Incremental persistence after each query pair.
"""

import asyncio
import os
import sys
import time
import json
import copy
from pathlib import Path
from typing import List, Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.generation import KnowledgeGeneration, GenerationLifecycleStatus
from app.infrastructure.db.models.chunk import DocumentChunk
from app.application.rag.normalization import normalize_query_for_search
from app.application.rag.dense import retrieve_dense_candidates
from app.application.rag.bm25 import get_or_build_bm25_index
from app.application.rag.fusion import reciprocal_rank_fusion
from app.application.rag.reranker import get_cross_encoder_model
from app.application.rag.filters import filter_noise_chunks, suppress_duplicate_chunks
from app.application.rag.schemas import RetrievalCandidate
from app.application.conversation.grounding_guard import GroundingGuard, ENGLISH_FALLBACK
from app.core.config import get_settings


def get_memory_info() -> Dict[str, Any]:
    """Retrieve system and container memory info."""
    mem_info = {}
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    if key in ("MemTotal", "MemFree", "MemAvailable", "SwapTotal", "SwapFree"):
                        mem_info[key + "_kB"] = int(val)
    except Exception as e:
        mem_info["error"] = str(e)

    # Process RSS
    try:
        import psutil
        p = psutil.Process(os.getpid())
        p_mem = p.memory_info()
        mem_info["process_rss_mb"] = round(p_mem.rss / (1024 * 1024), 2)
        mem_info["process_vms_mb"] = round(p_mem.vms / (1024 * 1024), 2)
    except Exception:
        pass
    return mem_info


def execute_rerank_arm(
    raw_query: str,
    candidates: List[RetrievalCandidate],
    candidate_limit: int,
    cross_encoder_model,
) -> Dict[str, Any]:
    """
    Execute one arm of the reranker experiment:
    1. Slice fresh candidates to candidate_limit.
    2. Measure Cross-Encoder inference latency.
    3. Sort descending by Cross-Encoder score (tie-breaker: RRF score).
    4. Run filter_noise_chunks (score-independent).
    5. Run suppress_duplicate_chunks (order-dependent).
    6. Take top 5 final evidence chunks.
    """
    arm_candidates = [c.model_copy() for c in candidates[:candidate_limit]]

    # Prepare input pairs
    pairs = [[raw_query, c.text] for c in arm_candidates]

    # Measure Cross-Encoder latency with nanosecond precision
    t_rerank_start = time.perf_counter_ns()
    scores = cross_encoder_model.predict(pairs)
    t_rerank_end = time.perf_counter_ns()
    rerank_duration_ms = (t_rerank_end - t_rerank_start) / 1_000_000.0

    # Attach scores
    scored_candidates: List[RetrievalCandidate] = []
    for c, score in zip(arm_candidates, scores):
        c_copy = c.model_copy()
        c_copy.reranker_score = round(float(score), 4)
        scored_candidates.append(c_copy)

    # Sort descending by Cross-Encoder relevance score
    scored_candidates.sort(
        key=lambda c: (
            c.reranker_score if c.reranker_score is not None else -999.0,
            c.rrf_score if c.rrf_score is not None else 0.0,
        ),
        reverse=True,
    )
    for idx, c in enumerate(scored_candidates, start=1):
        c.final_rank = idx

    # Measure post-rerank filtering latency
    t_filter_start = time.perf_counter_ns()
    filtered = filter_noise_chunks(scored_candidates, query_text=raw_query)
    deduped = suppress_duplicate_chunks(filtered)
    final_evidence = deduped[:5]
    t_filter_end = time.perf_counter_ns()
    filter_duration_ms = (t_filter_end - t_filter_start) / 1_000_000.0

    # Inspect bibliography intrusions
    bib_intrusions = 0
    for cand in final_evidence:
        text_lower = cand.text.lower()
        sec_lower = (cand.section or "").lower()
        if "bibliography" in sec_lower or "references" in sec_lower or "isbn:" in text_lower:
            bib_intrusions += 1

    return {
        "candidate_limit": candidate_limit,
        "rerank_candidates_fed": len(arm_candidates),
        "rerank_duration_ms": round(rerank_duration_ms, 3),
        "filter_duration_ms": round(filter_duration_ms, 3),
        "bib_intrusions": bib_intrusions,
        "reranked_chunks": [
            {
                "chunk_id": c.chunk_id,
                "score": c.reranker_score,
                "doc": c.source_filename,
                "page": c.page_number,
                "section": c.section,
            }
            for c in scored_candidates
        ],
        "final_evidence": [
            {
                "chunk_id": c.chunk_id,
                "score": c.reranker_score,
                "doc": c.source_filename,
                "page": c.page_number,
                "section": c.section,
                "rank": idx,
            }
            for idx, c in enumerate(final_evidence, start=1)
        ],
        "_final_evidence_objects": final_evidence,
    }


def evaluate_quality(
    final_evidence: List[Dict[str, Any]],
    expected_chunk_ids: List[str],
) -> Dict[str, Any]:
    """Calculate Hit@1, Recall@5, and Reciprocal Rank."""
    expected_set = set(expected_chunk_ids)
    first_rank: Optional[int] = None
    for idx, c in enumerate(final_evidence, start=1):
        if c["chunk_id"] in expected_set:
            if first_rank is None:
                first_rank = idx

    hit_at_1 = 1 if first_rank == 1 else 0
    recall_at_5 = 1 if (first_rank is not None and first_rank <= 5) else 0
    reciprocal_rank = (1.0 / first_rank) if (first_rank is not None and first_rank <= 5) else 0.0

    return {
        "first_relevant_rank": first_rank,
        "hit_at_1": hit_at_1,
        "recall_at_5": recall_at_5,
        "reciprocal_rank": round(reciprocal_rank, 4),
    }


async def run_isolated_experiment():
    output_dir = Path("/app/scratch/level2_rerank_experiment")
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "benchmark_results.json"

    print("=" * 80)
    print("ISOLATED LEVEL 2 RERANKER EXPERIMENT: 15 vs 10 CANDIDATES")
    print("=" * 80)
    start_wall = time.time()
    mem_initial = get_memory_info()
    print(f"Initial Memory: {mem_initial}")

    # 1. Verify Active Generation Read-Only
    session_factory = get_session_factory()
    async with session_factory() as session:
        gens = (await session.execute(
            select(KnowledgeGeneration).where(KnowledgeGeneration.is_active.is_(True))
        )).scalars().all()

        assert len(gens) == 1, f"Expected 1 active generation, found {len(gens)}"
        active_gen = gens[0]
        gen_id = str(active_gen.id)
        assert gen_id == "1a2c6365-1bee-4478-9599-a706ee5c7221", f"Unexpected active generation ID: {gen_id}"
        print(f"Active Generation Verified: {gen_id} (Version: {active_gen.generation_version})")

        # 2. Establish 1-to-1 Ground Truth Chunk ID Mapping
        # Map 6ee chunk IDs from Phase 7 canonical fixture to 1a2 active generation chunk IDs
        c_6ee = (await session.execute(
            select(DocumentChunk).where(DocumentChunk.generation_id == '6ee08b45-823a-4bd5-8604-920bbdd61d58')
        )).scalars().all()
        c_1a2 = (await session.execute(
            select(DocumentChunk).where(DocumentChunk.generation_id == gen_id)
        )).scalars().all()

        map_6ee_to_1a2 = {}
        for a in c_6ee:
            for b in c_1a2:
                if a.chunk_text.strip() == b.chunk_text.strip():
                    map_6ee_to_1a2[a.id] = b.id
                    break

        assert len(map_6ee_to_1a2) == 22, f"Failed to map all 22 chunks: mapped {len(map_6ee_to_1a2)}"
        print(f"Canonical ground truth chunk mapping verified: 22/22 chunks mapped exactly by text.")

        # 3. Load Canonical 24-Query Fixture
        fixture_path = output_dir / "canonical_24_queries.json"
        with open(fixture_path, "r", encoding="utf-8") as f:
            queries = json.load(f)
        assert len(queries) == 24, f"Expected 24 queries, found {len(queries)}"
        print(f"Loaded {len(queries)} canonical gold-standard queries from {fixture_path.name}")

        # 4. Measure Model Initialization Separately
        print("\nLoading Cross-Encoder model (measuring cold initialization)...")
        settings = get_settings()
        t_model_init_start = time.perf_counter_ns()
        cross_encoder = get_cross_encoder_model(settings.CROSS_ENCODER_MODEL)
        t_model_init_end = time.perf_counter_ns()
        model_init_duration_ms = (t_model_init_end - t_model_init_start) / 1_000_000.0
        print(f"Cross-Encoder Cold Initialization Duration: {model_init_duration_ms:.2f} ms")

        # 5. Build BM25 Index for active generation
        bm25_index = await get_or_build_bm25_index(generation_id=gen_id, session=session)
        assert bm25_index is not None, "BM25 index failed to build"

        # 6. Excluded Warm-Up Execution
        print("\nExecuting warmup pass (excluded from measured results)...")
        warmup_query = "What is the history of Pattadakal UNESCO temples?"
        w_norm = normalize_query_for_search(warmup_query)
        w_dense = retrieve_dense_candidates(query_text=w_norm, generation_id=gen_id, top_k=25)
        w_bm25 = bm25_index.query(query_text=w_norm, top_k=25)
        w_fused = reciprocal_rank_fusion(dense_candidates=w_dense, bm25_candidates=w_bm25, k=60, top_n=15)
        _ = execute_rerank_arm(warmup_query, w_fused, 15, cross_encoder)
        _ = execute_rerank_arm(warmup_query, w_fused, 10, cross_encoder)
        print("Warmup pass completed and excluded.")

        # 7. Check for existing partial results (Resume capability)
        benchmark_data: Dict[str, Any] = {
            "metadata": {
                "active_generation_id": gen_id,
                "cross_encoder_model": settings.CROSS_ENCODER_MODEL,
                "cold_initialization_ms": round(model_init_duration_ms, 2),
                "total_queries": len(queries),
                "planned_arm_executions": len(queries) * 4,
                "memory_initial": mem_initial,
            },
            "queries": {},
        }
        if results_path.exists():
            try:
                with open(results_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if "queries" in existing:
                        benchmark_data["queries"] = existing["queries"]
                        print(f"Resuming: Loaded {len(benchmark_data['queries'])} existing completed queries.")
            except Exception as e:
                print(f"Could not load existing results: {e}. Starting fresh.")

        guard = GroundingGuard(min_score_threshold=settings.CONVERSATION_GROUNDING_MIN_SCORE)

        print("\n" + "=" * 80)
        print("EXECUTING 96 PAIRED ARM EXECUTIONS (2 REPETITIONS PER QUERY, SERIAL)")
        print("  Repetition 1: Arm 15 -> Arm 10")
        print("  Repetition 2: Arm 10 -> Arm 15")
        print("=" * 80)

        for q_idx, q in enumerate(queries, start=1):
            q_id = q["id"]
            if q_id in benchmark_data["queries"]:
                print(f"[{q_idx:02d}/24] Query {q_id} already completed, skipping.")
                continue

            raw_query = q["query"]
            cat = q["category"]
            expected_cids_1a2 = [map_6ee_to_1a2[cid] for cid in q["expected_chunks"] if cid in map_6ee_to_1a2]

            # Retrieval stage (Dense + BM25 + RRF) performed once per query
            t_retrieval_start = time.perf_counter_ns()
            norm_q = normalize_query_for_search(raw_query)

            t_d_start = time.perf_counter_ns()
            dense_cands = retrieve_dense_candidates(query_text=norm_q, generation_id=gen_id, top_k=25)
            dense_ms = (time.perf_counter_ns() - t_d_start) / 1_000_000.0

            t_b_start = time.perf_counter_ns()
            bm25_cands = bm25_index.query(query_text=norm_q, top_k=25)
            bm25_ms = (time.perf_counter_ns() - t_b_start) / 1_000_000.0

            t_f_start = time.perf_counter_ns()
            # Generate top 15 fused candidates
            fused_cands = reciprocal_rank_fusion(
                dense_candidates=dense_cands,
                bm25_candidates=bm25_cands,
                k=60,
                top_n=15,
            )
            fusion_ms = (time.perf_counter_ns() - t_f_start) / 1_000_000.0
            total_retrieval_ms = (time.perf_counter_ns() - t_retrieval_start) / 1_000_000.0

            # Verify that slicing fused_cands[:10] matches reciprocal_rank_fusion with top_n=10
            fused_cands_10_direct = reciprocal_rank_fusion(
                dense_candidates=dense_cands,
                bm25_candidates=bm25_cands,
                k=60,
                top_n=10,
            )
            slice_ids = [c.chunk_id for c in fused_cands[:10]]
            direct_ids = [c.chunk_id for c in fused_cands_10_direct]
            assert slice_ids == direct_ids, f"Discrepancy in RRF candidate order for {q_id}!"

            # Paired execution:
            # Repetition 1: 15-then-10
            rep1_arm15 = execute_rerank_arm(raw_query, fused_cands, 15, cross_encoder)
            rep1_arm10 = execute_rerank_arm(raw_query, fused_cands, 10, cross_encoder)

            # Repetition 2: 10-then-15
            rep2_arm10 = execute_rerank_arm(raw_query, fused_cands, 10, cross_encoder)
            rep2_arm15 = execute_rerank_arm(raw_query, fused_cands, 15, cross_encoder)

            # Evaluate quality metrics for each execution
            q_rep1_15 = evaluate_quality(rep1_arm15["final_evidence"], expected_cids_1a2)
            q_rep1_10 = evaluate_quality(rep1_arm10["final_evidence"], expected_cids_1a2)
            q_rep2_10 = evaluate_quality(rep2_arm10["final_evidence"], expected_cids_1a2)
            q_rep2_15 = evaluate_quality(rep2_arm15["final_evidence"], expected_cids_1a2)

            rep1_arm15["quality"] = q_rep1_15
            rep1_arm10["quality"] = q_rep1_10
            rep2_arm10["quality"] = q_rep2_10
            rep2_arm15["quality"] = q_rep2_15

            # Grounding check on final evidence using real RetrievalCandidate objects
            g_check_15 = guard.evaluate(rep1_arm15["_final_evidence_objects"], "en", gen_id)
            g_check_10 = guard.evaluate(rep1_arm10["_final_evidence_objects"], "en", gen_id)

            # Strip non-serializable candidate objects before persisting
            rep1_arm15.pop("_final_evidence_objects", None)
            rep1_arm10.pop("_final_evidence_objects", None)
            rep2_arm10.pop("_final_evidence_objects", None)
            rep2_arm15.pop("_final_evidence_objects", None)

            # Calculate paired latency delta (T_15 - T_10)
            delta_rep1 = round(rep1_arm15["rerank_duration_ms"] - rep1_arm10["rerank_duration_ms"], 3)
            delta_rep2 = round(rep2_arm15["rerank_duration_ms"] - rep2_arm10["rerank_duration_ms"], 3)

            q_record = {
                "query_id": q_id,
                "category": cat,
                "query_text": raw_query,
                "expected_chunks_1a2": expected_cids_1a2,
                "retrieval_timings_ms": {
                    "dense_ms": round(dense_ms, 2),
                    "bm25_ms": round(bm25_ms, 2),
                    "fusion_ms": round(fusion_ms, 2),
                    "total_retrieval_ms": round(total_retrieval_ms, 2),
                },
                "rep1_15_then_10": {
                    "arm_15": rep1_arm15,
                    "arm_10": rep1_arm10,
                    "paired_rerank_delta_ms": delta_rep1,
                },
                "rep2_10_then_15": {
                    "arm_10": rep2_arm10,
                    "arm_15": rep2_arm15,
                    "paired_rerank_delta_ms": delta_rep2,
                },
                "grounding_guard": {
                    "arm_15_is_grounded": g_check_15.is_grounded,
                    "arm_15_top_score": g_check_15.top_score,
                    "arm_10_is_grounded": g_check_10.is_grounded,
                    "arm_10_top_score": g_check_10.top_score,
                    "grounding_policy_check_threshold": -6.0,
                    "answer_hallucination_assessment": "NOT MEASURED (no answers generated)",
                },
            }

            benchmark_data["queries"][q_id] = q_record

            # Incremental save after each query pair
            with open(results_path, "w", encoding="utf-8") as f:
                json.dump(benchmark_data, f, indent=2)

            # Console log
            print(
                f"[{q_idx:02d}/24] {q_id} ({cat[:14]:14s}) | "
                f"Rep1 Rerank: 15={rep1_arm15['rerank_duration_ms']:5.1f}ms, 10={rep1_arm10['rerank_duration_ms']:5.1f}ms (delta={delta_rep1:+5.1f}ms) | "
                f"Rep2 Rerank: 15={rep2_arm15['rerank_duration_ms']:5.1f}ms, 10={rep2_arm10['rerank_duration_ms']:5.1f}ms (delta={delta_rep2:+5.1f}ms) | "
                f"Rank(15)={q_rep1_15['first_relevant_rank']}, Rank(10)={q_rep1_10['first_relevant_rank']}"
            )

        # 8. Synthetic Out-of-Corpus Fallback Check
        print("\nExecuting Synthetic Out-of-Corpus Fallback Check...")
        ooc_query = "What is the ticket price for the Eiffel Tower in Paris?"
        ooc_norm = normalize_query_for_search(ooc_query)
        ooc_dense = retrieve_dense_candidates(query_text=ooc_norm, generation_id=gen_id, top_k=25)
        ooc_bm25 = bm25_index.query(query_text=ooc_norm, top_k=25)
        ooc_fused = reciprocal_rank_fusion(dense_candidates=ooc_dense, bm25_candidates=ooc_bm25, k=60, top_n=15)
        ooc_arm15 = execute_rerank_arm(ooc_query, ooc_fused, 15, cross_encoder)
        ooc_arm10 = execute_rerank_arm(ooc_query, ooc_fused, 10, cross_encoder)

        ooc_g15 = guard.evaluate(ooc_arm15["_final_evidence_objects"], "en", gen_id)
        ooc_g10 = guard.evaluate(ooc_arm10["_final_evidence_objects"], "en", gen_id)

        ooc_arm15.pop("_final_evidence_objects", None)
        ooc_arm10.pop("_final_evidence_objects", None)

        fallback_check_data = {
            "query": ooc_query,
            "arm_15": {
                "top_score": ooc_g15.top_score,
                "is_grounded": ooc_g15.is_grounded,
                "fallback_message": ooc_g15.fallback_message,
                "matches_expected_fallback": ooc_g15.fallback_message == ENGLISH_FALLBACK,
            },
            "arm_10": {
                "top_score": ooc_g10.top_score,
                "is_grounded": ooc_g10.is_grounded,
                "fallback_message": ooc_g10.fallback_message,
                "matches_expected_fallback": ooc_g10.fallback_message == ENGLISH_FALLBACK,
            },
        }
        print(f"Fallback check Arm 15: top_score={ooc_g15.top_score}, is_grounded={ooc_g15.is_grounded}, fallback='{ooc_g15.fallback_message}'")
        print(f"Fallback check Arm 10: top_score={ooc_g10.top_score}, is_grounded={ooc_g10.is_grounded}, fallback='{ooc_g10.fallback_message}'")

        benchmark_data["out_of_corpus_fallback_check"] = fallback_check_data

        # 9. Compute Overall Aggregate Metrics & Statistical Summary
        mem_final = get_memory_info()
        benchmark_data["metadata"]["memory_final"] = mem_final
        benchmark_data["metadata"]["total_wall_time_seconds"] = round(time.time() - start_wall, 2)

        # Aggregate analysis across all 96 arm executions (48 for Arm 15, 48 for Arm 10)
        arm15_rerank_times = []
        arm10_rerank_times = []
        paired_deltas = []  # T_15 - T_10
        arm15_hit1 = []
        arm10_hit1 = []
        arm15_recall5 = []
        arm10_recall5 = []
        arm15_mrr = []
        arm10_mrr = []
        arm15_bib_leaks = 0
        arm10_bib_leaks = 0
        quality_regressions = []

        for q_id, q_data in benchmark_data["queries"].items():
            r1 = q_data["rep1_15_then_10"]
            r2 = q_data["rep2_10_then_15"]

            # Arm 15 executions
            arm15_rerank_times.extend([r1["arm_15"]["rerank_duration_ms"], r2["arm_15"]["rerank_duration_ms"]])
            arm15_hit1.extend([r1["arm_15"]["quality"]["hit_at_1"], r2["arm_15"]["quality"]["hit_at_1"]])
            arm15_recall5.extend([r1["arm_15"]["quality"]["recall_at_5"], r2["arm_15"]["quality"]["recall_at_5"]])
            arm15_mrr.extend([r1["arm_15"]["quality"]["reciprocal_rank"], r2["arm_15"]["quality"]["reciprocal_rank"]])
            arm15_bib_leaks += r1["arm_15"]["bib_intrusions"] + r2["arm_15"]["bib_intrusions"]

            # Arm 10 executions
            arm10_rerank_times.extend([r1["arm_10"]["rerank_duration_ms"], r2["arm_10"]["rerank_duration_ms"]])
            arm10_hit1.extend([r1["arm_10"]["quality"]["hit_at_1"], r2["arm_10"]["quality"]["hit_at_1"]])
            arm10_recall5.extend([r1["arm_10"]["quality"]["recall_at_5"], r2["arm_10"]["quality"]["recall_at_5"]])
            arm10_mrr.extend([r1["arm_10"]["quality"]["reciprocal_rank"], r2["arm_10"]["quality"]["reciprocal_rank"]])
            arm10_bib_leaks += r1["arm_10"]["bib_intrusions"] + r2["arm_10"]["bib_intrusions"]

            # Paired deltas
            paired_deltas.append(r1["paired_rerank_delta_ms"])
            paired_deltas.append(r2["paired_rerank_delta_ms"])

            # Check quality differences
            rank_15 = r1["arm_15"]["quality"]["first_relevant_rank"]
            rank_10 = r1["arm_10"]["quality"]["first_relevant_rank"]
            if rank_10 != rank_15:
                quality_regressions.append({
                    "query_id": q_id,
                    "query": q_data["query_text"],
                    "rank_arm15": rank_15,
                    "rank_arm10": rank_10,
                    "delta_rank": rank_10 - rank_15 if (rank_10 and rank_15) else "MISSED",
                })

        import statistics

        def get_stats(data: List[float]) -> Dict[str, float]:
            sorted_d = sorted(data)
            n = len(sorted_d)
            return {
                "count": n,
                "mean": round(statistics.mean(sorted_d), 2),
                "median": round(statistics.median(sorted_d), 2),
                "min": round(sorted_d[0], 2),
                "max": round(sorted_d[-1], 2),
                "p90": round(sorted_d[int(0.90 * (n - 1))], 2),
                "p95": round(sorted_d[int(0.95 * (n - 1))], 2),
                "stdev": round(statistics.stdev(sorted_d), 2) if n > 1 else 0.0,
            }

        arm15_stats = get_stats(arm15_rerank_times)
        arm10_stats = get_stats(arm10_rerank_times)
        delta_stats = get_stats(paired_deltas)

        # Quality percentages
        arm15_hit1_pct = round(sum(arm15_hit1) / len(arm15_hit1) * 100.0, 2)
        arm10_hit1_pct = round(sum(arm10_hit1) / len(arm10_hit1) * 100.0, 2)
        arm15_recall5_pct = round(sum(arm15_recall5) / len(arm15_recall5) * 100.0, 2)
        arm10_recall5_pct = round(sum(arm10_recall5) / len(arm10_recall5) * 100.0, 2)
        arm15_mrr_val = round(sum(arm15_mrr) / len(arm15_mrr), 4)
        arm10_mrr_val = round(sum(arm10_mrr) / len(arm10_mrr), 4)

        benchmark_data["summary"] = {
            "sample_counts": {
                "arm_15_executions": len(arm15_rerank_times),
                "arm_10_executions": len(arm10_rerank_times),
                "paired_repetition_pairs": len(paired_deltas),
            },
            "reranker_latency_ms": {
                "arm_15": arm15_stats,
                "arm_10": arm10_stats,
                "paired_delta_15_minus_10": delta_stats,
            },
            "quality_metrics": {
                "arm_15": {
                    "hit_at_1_pct": arm15_hit1_pct,
                    "recall_at_5_pct": arm15_recall5_pct,
                    "mrr": arm15_mrr_val,
                    "bib_intrusions": arm15_bib_leaks,
                },
                "arm_10": {
                    "hit_at_1_pct": arm10_hit1_pct,
                    "recall_at_5_pct": arm10_recall5_pct,
                    "mrr": arm10_mrr_val,
                    "bib_intrusions": arm10_bib_leaks,
                },
                "locked_floors": {
                    "hit_at_1": ">= 95.83%",
                    "recall_at_5": "= 100.0%",
                    "mrr": ">= 0.9792",
                    "bib_intrusions": 0,
                },
                "floors_met_arm15": (
                    arm15_hit1_pct >= 95.83
                    and arm15_recall5_pct == 100.0
                    and arm15_mrr_val >= 0.9792
                    and arm15_bib_leaks == 0
                ),
                "floors_met_arm10": (
                    arm10_hit1_pct >= 95.83
                    and arm10_recall5_pct == 100.0
                    and arm10_mrr_val >= 0.9792
                    and arm10_bib_leaks == 0
                ),
            },
            "quality_regressions": quality_regressions,
        }

        # Final write
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_data, f, indent=2)

        print("\n" + "=" * 80)
        print("EXPERIMENT COMPLETE: SUMMARY OF RESULTS")
        print("=" * 80)
        print(f"Total Measured Arm Executions: 96 (48 Arm 15, 48 Arm 10)")
        print(f"Arm 15 Reranker Latency: Mean={arm15_stats['mean']}ms, Median={arm15_stats['median']}ms, P90={arm15_stats['p90']}ms, P95={arm15_stats['p95']}ms")
        print(f"Arm 10 Reranker Latency: Mean={arm10_stats['mean']}ms, Median={arm10_stats['median']}ms, P90={arm10_stats['p90']}ms, P95={arm10_stats['p95']}ms")
        print(f"Paired Difference (15 - 10): Mean={delta_stats['mean']}ms, Median={delta_stats['median']}ms, Min={delta_stats['min']}ms, Max={delta_stats['max']}ms")
        print("-" * 80)
        print(f"Arm 15 Quality: Hit@1={arm15_hit1_pct}%, Recall@5={arm15_recall5_pct}%, MRR={arm15_mrr_val}, BibLeaks={arm15_bib_leaks}")
        print(f"Arm 10 Quality: Hit@1={arm10_hit1_pct}%, Recall@5={arm10_recall5_pct}%, MRR={arm10_mrr_val}, BibLeaks={arm10_bib_leaks}")
        print(f"Quality Regressions count: {len(quality_regressions)}")
        if quality_regressions:
            for qr in quality_regressions:
                print(f"  Query {qr['query_id']}: Arm15 Rank={qr['rank_arm15']} -> Arm10 Rank={qr['rank_arm10']}")
        print(f"Floors Met Arm 15: {benchmark_data['summary']['quality_metrics']['floors_met_arm15']}")
        print(f"Floors Met Arm 10: {benchmark_data['summary']['quality_metrics']['floors_met_arm10']}")
        print("=" * 80)
        print(f"Results saved to: {results_path}")


if __name__ == "__main__":
    asyncio.run(run_isolated_experiment())
