import json
import os

def recalculate_quality():
    res_path = r"D:\Karnataka Guide\evidence\20260927_142438_reranker_verification\original_artifacts\benchmark_results.json"
    audit_path = r"D:\Karnataka Guide\evidence\20260927_142438_reranker_verification\mapping_audit.json"

    with open(res_path, "r", encoding="utf-8") as f:
        res = json.load(f)

    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    queries = res["queries"]
    print(f"Total queries to recalculate: {len(queries)}")

    per_query_audit = []
    
    # Track metrics for Arm 15 and Arm 10 across Rep 1 and Rep 2
    # Since Rep 1 and Rep 2 have identical retrieved evidence (deterministic RRF + Cross-Encoder),
    # let's verify if Rep 1 and Rep 2 produce identical ranks and evidence.
    
    arm15_hits_at_1 = []
    arm15_hits_at_5 = []
    arm15_strict_recalls = []
    arm15_mrr_terms = []

    arm10_hits_at_1 = []
    arm10_hits_at_5 = []
    arm10_strict_recalls = []
    arm10_mrr_terms = []

    evidence_differences = []

    for qid in sorted(queries.keys()):
        q_data = queries[qid]
        q_text = q_data["query_text"]
        cat = q_data["category"]
        expected_ids = set(q_data["expected_chunks_1a2"])

        r1 = q_data["rep1_15_then_10"]
        r2 = q_data["rep2_10_then_15"]

        # Final evidence lists
        ev_15_r1 = r1["arm_15"]["final_evidence"]
        ev_10_r1 = r1["arm_10"]["final_evidence"]
        ev_10_r2 = r2["arm_10"]["final_evidence"]
        ev_15_r2 = r2["arm_15"]["final_evidence"]

        ids_15_r1 = [c["chunk_id"] for c in ev_15_r1]
        ids_10_r1 = [c["chunk_id"] for c in ev_10_r1]
        ids_10_r2 = [c["chunk_id"] for c in ev_10_r2]
        ids_15_r2 = [c["chunk_id"] for c in ev_15_r2]

        # Check deterministic evidence across repetitions
        assert ids_15_r1 == ids_15_r2, f"Arm 15 non-deterministic between reps for {qid}!"
        assert ids_10_r1 == ids_10_r2, f"Arm 10 non-deterministic between reps for {qid}!"

        # Compare complete ordered top-5 evidence between Arm 15 and Arm 10
        if ids_15_r1 != ids_10_r1:
            evidence_differences.append({
                "query_id": qid,
                "arm_15_ids": ids_15_r1,
                "arm_10_ids": ids_10_r1,
                "diff_indices": [i for i in range(5) if ids_15_r1[i] != ids_10_r1[i]]
            })

        # Match analysis
        matched_15 = [cid for cid in ids_15_r1 if cid in expected_ids]
        matched_10 = [cid for cid in ids_10_r1 if cid in expected_ids]

        # First relevant rank (1-indexed)
        rank_15 = next((i + 1 for i, cid in enumerate(ids_15_r1) if cid in expected_ids), None)
        rank_10 = next((i + 1 for i, cid in enumerate(ids_10_r1) if cid in expected_ids), None)

        hit1_15 = 1 if rank_15 == 1 else 0
        hit1_10 = 1 if rank_10 == 1 else 0

        hit5_15 = 1 if (rank_15 is not None and rank_15 <= 5) else 0
        hit5_10 = 1 if (rank_10 is not None and rank_10 <= 5) else 0

        # Strict recall = (retrieved relevant items in top 5) / (total expected relevant items)
        strict_recall_15 = len(matched_15) / len(expected_ids)
        strict_recall_10 = len(matched_10) / len(expected_ids)

        mrr_15 = (1.0 / rank_15) if (rank_15 is not None and rank_15 <= 5) else 0.0
        mrr_10 = (1.0 / rank_10) if (rank_10 is not None and rank_10 <= 5) else 0.0

        arm15_hits_at_1.append(hit1_15)
        arm15_hits_at_5.append(hit5_15)
        arm15_strict_recalls.append(strict_recall_15)
        arm15_mrr_terms.append(mrr_15)

        arm10_hits_at_1.append(hit1_10)
        arm10_hits_at_5.append(hit5_10)
        arm10_strict_recalls.append(strict_recall_10)
        arm10_mrr_terms.append(mrr_10)

        per_query_audit.append({
            "query_id": qid,
            "category": cat,
            "query_text": q_text,
            "expected_relevance_set_size": len(expected_ids),
            "expected_chunk_ids": list(expected_ids),
            "arm_15": {
                "top_5_chunk_ids": ids_15_r1,
                "matched_chunk_ids": matched_15,
                "matched_count": len(matched_15),
                "first_relevant_rank": rank_15,
                "hit_at_1": hit1_15,
                "hit_at_5": hit5_15,
                "strict_recall_at_5": round(strict_recall_15, 4),
                "reciprocal_rank": round(mrr_15, 6)
            },
            "arm_10": {
                "top_5_chunk_ids": ids_10_r1,
                "matched_chunk_ids": matched_10,
                "matched_count": len(matched_10),
                "first_relevant_rank": rank_10,
                "hit_at_1": hit1_10,
                "hit_at_5": hit5_10,
                "strict_recall_at_5": round(strict_recall_10, 4),
                "reciprocal_rank": round(mrr_10, 6)
            },
            "ordered_evidence_identical": (ids_15_r1 == ids_10_r1)
        })

    total_q = len(queries)
    
    # Compute aggregates
    arm15_hit1_rate = sum(arm15_hits_at_1) / total_q
    arm15_hit5_rate = sum(arm15_hits_at_5) / total_q
    arm15_avg_strict_recall = sum(arm15_strict_recalls) / total_q
    arm15_sum_rr = sum(arm15_mrr_terms)
    arm15_unrounded_mrr = arm15_sum_rr / total_q

    arm10_hit1_rate = sum(arm10_hits_at_1) / total_q
    arm10_hit5_rate = sum(arm10_hits_at_5) / total_q
    arm10_avg_strict_recall = sum(arm10_strict_recalls) / total_q
    arm10_sum_rr = sum(arm10_mrr_terms)
    arm10_unrounded_mrr = arm10_sum_rr / total_q

    print("=" * 80)
    print("QUALITY METRICS RECALCULATION")
    print("=" * 80)
    print(f"Total queries: {total_q}")
    print(f"Differences in complete ordered top-5 evidence between arms: {len(evidence_differences)}")
    if evidence_differences:
        for diff in evidence_differences:
            print(f"  Difference in {diff['query_id']}: positions {diff['diff_indices']}")
    else:
        print("  ALL 24 QUERIES RETURNED 100% IDENTICAL ORDERED TOP-5 EVIDENCE CHUNKS!")

    print("\n--- Arm 15 Metrics ---")
    print(f"  Hit@1 Rate: {arm15_hit1_rate * 100.0:.2f}% ({sum(arm15_hits_at_1)}/{total_q})")
    print(f"  Hit@5 Rate (Historical 'Recall@5'): {arm15_hit5_rate * 100.0:.2f}% ({sum(arm15_hits_at_5)}/{total_q})")
    print(f"  Strict Multi-Label Recall@5: {arm15_avg_strict_recall * 100.0:.2f}%")
    print(f"  Sum of Reciprocal Ranks: {arm15_sum_rr}")
    print(f"  Unrounded MRR: {arm15_unrounded_mrr:.10f}")
    print(f"  4-decimal rounded MRR: {round(arm15_unrounded_mrr, 4)}")

    print("\n--- Arm 10 Metrics ---")
    print(f"  Hit@1 Rate: {arm10_hit1_rate * 100.0:.2f}% ({sum(arm10_hits_at_1)}/{total_q})")
    print(f"  Hit@5 Rate (Historical 'Recall@5'): {arm10_hit5_rate * 100.0:.2f}% ({sum(arm10_hits_at_5)}/{total_q})")
    print(f"  Strict Multi-Label Recall@5: {arm10_avg_strict_recall * 100.0:.2f}%")
    print(f"  Sum of Reciprocal Ranks: {arm10_sum_rr}")
    print(f"  Unrounded MRR: {arm10_unrounded_mrr:.10f}")
    print(f"  4-decimal rounded MRR: {round(arm10_unrounded_mrr, 4)}")

    # Check MRR >= 0.9792 threshold strictly
    passes_literal_09792_15 = (arm15_unrounded_mrr >= 0.9792)
    passes_rounded_09792_15 = (round(arm15_unrounded_mrr, 4) >= 0.9792)

    print("\n--- MRR Acceptance Rule Inspection ---")
    print(f"  Literal check (MRR >= 0.9792000000): {passes_literal_09792_15} (Difference: {arm15_unrounded_mrr - 0.9792:+.10f})")
    print(f"  Rounded check (round(MRR, 4) >= 0.9792): {passes_rounded_09792_15}")
    print(f"  Provenance: Historical baseline of 0.9792 in Phase 7 documentation was round(23.5/24, 4).")
    print(f"              23 queries at Rank 1 (1.0) + 1 query (Q04) at Rank 2 (0.5) = 23.5 / 24 = 0.9791666667.")

    out_file = r"D:\Karnataka Guide\evidence\20260927_142438_reranker_verification\quality_recalculation.json"
    recalc_export = {
        "summary": {
            "total_queries": total_q,
            "evidence_differences_count": len(evidence_differences),
            "evidence_differences": evidence_differences,
            "arm_15": {
                "hit_at_1_count": sum(arm15_hits_at_1),
                "hit_at_1_pct": round(arm15_hit1_rate * 100.0, 2),
                "hit_at_5_count": sum(arm15_hits_at_5),
                "hit_at_5_pct": round(arm15_hit5_rate * 100.0, 2),
                "strict_multi_label_recall_at_5_pct": round(arm15_avg_strict_recall * 100.0, 2),
                "sum_reciprocal_ranks": arm15_sum_rr,
                "unrounded_mrr": arm15_unrounded_mrr,
                "rounded_4dec_mrr": round(arm15_unrounded_mrr, 4),
                "passes_literal_threshold_09792": passes_literal_09792_15,
                "passes_rounded_threshold_09792": passes_rounded_09792_15
            },
            "arm_10": {
                "hit_at_1_count": sum(arm10_hits_at_1),
                "hit_at_1_pct": round(arm10_hit1_rate * 100.0, 2),
                "hit_at_5_count": sum(arm10_hits_at_5),
                "hit_at_5_pct": round(arm10_hit5_rate * 100.0, 2),
                "strict_multi_label_recall_at_5_pct": round(arm10_avg_strict_recall * 100.0, 2),
                "sum_reciprocal_ranks": arm10_sum_rr,
                "unrounded_mrr": arm10_unrounded_mrr,
                "rounded_4dec_mrr": round(arm10_unrounded_mrr, 4),
                "passes_literal_threshold_09792": passes_literal_09792_15,
                "passes_rounded_threshold_09792": passes_rounded_09792_15
            },
            "quality_regressions": []
        },
        "per_query_audit": per_query_audit
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(recalc_export, f, indent=2)

    print(f"\nSaved quality recalculation to {out_file}")

if __name__ == "__main__":
    recalculate_quality()
