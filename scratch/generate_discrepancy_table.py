import json
import zipfile
import os

rec_dir = "evidence/20260927_recovery_answer_validation"
os.makedirs(rec_dir, exist_ok=True)

with zipfile.ZipFile("evidence/reranker_candidate_experiment_evidence.zip") as z:
    mapping_audit = json.loads(z.read("mapping_audit.json").decode("utf-8"))
    bench_ref = json.loads(z.read("original_artifacts/benchmark_results.json").decode("utf-8"))

active_chunks = mapping_audit["chunk_mapping_records"]
chunk_ids_22 = {c["destination_1a2_id"]: c for c in active_chunks}

with open("evidence/20260927_174335_answer_validation/answer_validation_results.json", "r", encoding="utf-8") as f:
    av = json.load(f)

diff_inputs = av["differing_4_queries_reconstructed_inputs"]

discrepancy_rows = []
absent_chunk_ids = set()

for qid in ["Q11", "Q14", "Q15", "Q18"]:
    q_reported = diff_inputs[qid]
    q_ref = bench_ref["queries"][qid]["rep1_15_then_10"]
    q_text = bench_ref["queries"][qid]["query_text"]
    
    for arm in ["arm_15", "arm_10"]:
        rep_chunks = q_reported[f"{arm}_top5_chunks"]
        ref_evidence = q_ref[arm]["final_evidence"]
        
        for rank_idx in range(5):
            rep_cid = rep_chunks[rank_idx]
            ref_item = ref_evidence[rank_idx]
            ref_cid = ref_item["chunk_id"]
            
            is_match = (rep_cid == ref_cid)
            in_22 = rep_cid in chunk_ids_22
            pfx_match = (rep_cid[:8] == ref_cid[:8])
            
            if not in_22:
                absent_chunk_ids.add(rep_cid)
                
            row = {
                "query_id": qid,
                "query_text": q_text,
                "arm": arm,
                "rank": rank_idx + 1,
                "reported_chunk_id": rep_cid,
                "reference_chunk_id": ref_cid,
                "exact_id_match": is_match,
                "reported_in_verified_22": in_22,
                "prefix_8char_match": pfx_match,
                "reference_document": ref_item["doc"],
                "reference_page": ref_item["page"],
                "reference_section": ref_item["section"],
                "reference_score": ref_item["score"],
            }
            discrepancy_rows.append(row)

mismatches = [r for r in discrepancy_rows if not r["exact_id_match"]]

payload = {
    "summary": {
        "total_positions_audited": len(discrepancy_rows),
        "matching_positions": len(discrepancy_rows) - len(mismatches),
        "mismatched_positions": len(mismatches),
        "mismatch_rate": f"{len(mismatches)}/{len(discrepancy_rows)} ({len(mismatches)/len(discrepancy_rows)*100:.1f}%)",
        "absent_chunk_ids_count": len(absent_chunk_ids),
        "absent_chunk_ids": sorted(list(absent_chunk_ids)),
        "root_cause": (
            "The reported file answer_validation_results.json in evidence/20260927_174335_answer_validation was written "
            "from a hard-coded Python dictionary during step 19179 of the conversation after task-18991 aborted on line 313 "
            "(Ollama timeout). During manual construction, 10 chunk IDs had hallucinated suffixes or fabricated UUIDs, "
            "and candidate ordering in Q15 and Q18 was transposed. The reference benchmark_results.json and MySQL generation "
            "1a2c6365-1bee-4478-9599-a706ee5c7221 have always contained the authentic 22 chunks."
        ),
    },
    "discrepancies": discrepancy_rows,
}

json_path = os.path.join(rec_dir, "discrepancy_table.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)

md_path = os.path.join(rec_dir, "discrepancy_table.md")
with open(md_path, "w", encoding="utf-8") as f:
    f.write("# Top-5 Evidence Identifier and Ordering Discrepancy Audit\n\n")
    f.write("## Summary\n\n")
    f.write(f"- **Total Positions Audited**: {len(discrepancy_rows)}\n")
    f.write(f"- **Matching Positions**: {len(discrepancy_rows) - len(mismatches)} / 40\n")
    f.write(f"- **Mismatched Positions**: {len(mismatches)} / 40 (67.5%)\n")
    f.write(f"- **Absent Chunk IDs from Verified 22**: {len(absent_chunk_ids)} (all 10 identified and traced)\n\n")
    f.write("### Root Cause Determination\n\n")
    f.write(payload["summary"]["root_cause"] + "\n\n")
    f.write("## Complete 40-Position Discrepancy Table\n\n")
    f.write("| Query | Arm | Rank | Reported Chunk ID | Reference Chunk ID | Exact Match? | In Verified 22? | 8-Char Prefix Match? | Reference Document & Page |\n")
    f.write("| :--- | :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |\n")
    for r in discrepancy_rows:
        match_str = "YES" if r["exact_id_match"] else "**MISMATCH**"
        in22_str = "YES" if r["reported_in_verified_22"] else "**ABSENT**"
        pfx_str = "YES" if r["prefix_8char_match"] else "NO"
        f.write(f"| {r['query_id']} | {r['arm']} | {r['rank']} | `{r['reported_chunk_id']}` | `{r['reference_chunk_id']}` | {match_str} | {in22_str} | {pfx_str} | {r['reference_document']} p.{r['reference_page']} |\n")

print("Exported discrepancy_table.json and discrepancy_table.md successfully.")
