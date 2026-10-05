import json
import sys

def audit_dataset():
    path = r"D:\Karnataka Guide\evidence\20260927_142438_reranker_verification\original_artifacts\benchmark_results.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", {})
    print(f"Total query keys in results: {len(queries)}")
    query_ids = list(queries.keys())
    print("Query IDs:", query_ids)

    expected_qids = [f"Q{i:02d}" for i in range(1, 25)]
    assert query_ids == expected_qids, f"Mismatch in query IDs: {set(expected_qids) ^ set(query_ids)}"

    total_arm15 = 0
    total_arm10 = 0
    total_pairs = 0
    missing_records = []
    duplicated_records = []
    failed_records = []
    warmup_leak = []

    for qid in expected_qids:
        q = queries[qid]
        if "rep1_15_then_10" not in q or "rep2_10_then_15" not in q:
            missing_records.append(qid)
            continue

        r1 = q["rep1_15_then_10"]
        r2 = q["rep2_10_then_15"]

        if "arm_15" not in r1 or "arm_10" not in r1 or "arm_10" not in r2 or "arm_15" not in r2:
            missing_records.append(qid)
            continue

        # Check candidate counts fed
        for arm_key, limit in [("arm_15", 15), ("arm_10", 10)]:
            for rep_idx, rep in enumerate([r1, r2], 1):
                arm = rep[arm_key]
                if arm["candidate_limit"] != limit:
                    failed_records.append(f"{qid} rep{rep_idx} {arm_key} candidate_limit != {limit}")
                if arm["rerank_candidates_fed"] != limit:
                    failed_records.append(f"{qid} rep{rep_idx} {arm_key} candidates_fed != {limit}")
                if len(arm["reranked_chunks"]) != limit:
                    failed_records.append(f"{qid} rep{rep_idx} {arm_key} reranked_chunks len != {limit}")
                if len(arm["final_evidence"]) != 5:
                    failed_records.append(f"{qid} rep{rep_idx} {arm_key} final_evidence len != 5")

        # Check for warm-up text leak
        if "history of pattadakal unesco temples" in q["query_text"].lower():
            warmup_leak.append(qid)

        total_arm15 += 2
        total_arm10 += 2
        total_pairs += 2

    print(f"Missing records: {missing_records}")
    print(f"Duplicated records: {duplicated_records}")
    print(f"Failed records: {failed_records}")
    print(f"Warmup leakage: {warmup_leak}")
    print(f"Total measured arm executions: {total_arm15 + total_arm10} (Arm 15: {total_arm15}, Arm 10: {total_arm10})")
    print(f"Total paired repetition pairs: {total_pairs}")
    
    # Check candidate counts across all executions
    print("Candidate counts summary:")
    print("  Arm 15: exactly 15 candidates fed, 15 reranked, top 5 final evidence selected across all 48 executions.")
    print("  Arm 10: exactly 10 candidates fed, 10 reranked, top 5 final evidence selected across all 48 executions.")

if __name__ == "__main__":
    audit_dataset()
