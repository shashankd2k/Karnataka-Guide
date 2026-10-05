import json

def main():
    bench_path = r"D:\Karnataka Guide\evidence\20260927_142438_reranker_verification\original_artifacts\benchmark_results.json"
    with open(bench_path, "r", encoding="utf-8") as f:
        bench = json.load(f)

    for qid in ["Q11", "Q14", "Q15", "Q18"]:
        q_obj = bench["queries"][qid]
        q_data = q_obj["rep1_15_then_10"]
        exp = q_obj["expected_chunks_1a2"]
        print(f"=== {qid}: '{q_obj['query_text']}' ===")
        print(f"Expected ID(s): {exp}")
        ev15 = q_data["arm_15"]["final_evidence"]
        ev10 = q_data["arm_10"]["final_evidence"]
        print("Arm 15 Top 5:")
        for i, c in enumerate(ev15):
            marker = " [TARGET]" if c["chunk_id"] in exp else ""
            print(f"  Rank {i+1}: doc={c['doc']}, page={c['page']}, sec='{c['section']}', score={c['score']:+.4f}, id={c['chunk_id']}{marker}")
        print("Arm 10 Top 5:")
        for i, c in enumerate(ev10):
            marker = " [TARGET]" if c["chunk_id"] in exp else ""
            print(f"  Rank {i+1}: doc={c['doc']}, page={c['page']}, sec='{c['section']}', score={c['score']:+.4f}, id={c['chunk_id']}{marker}")
        print()

if __name__ == "__main__":
    main()
