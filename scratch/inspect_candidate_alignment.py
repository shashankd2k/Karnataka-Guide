import json

recon = json.load(open("evidence/20260927_recovery_answer_validation/reconstructed_production_inputs_all24.json", encoding="utf-8"))
bench = json.load(open("scratch/level2_rerank_experiment/benchmark_results.json", encoding="utf-8"))

for qid in ["Q11", "Q14", "Q15", "Q18"]:
    cits = recon["queries"][qid]["arm_15"]["authoritative_citations"]
    bench_ev = bench["queries"][qid]["rep1_15_then_10"]["arm_15"]["final_evidence"]
    print(f"=== {qid} ===")
    for i, (c, b) in enumerate(zip(cits, bench_ev[:len(cits)])):
        print(f"  [{i+1}] cid={c['chunk_id']} p.{c['page_number']} sec={c['section_header']} | orig_doc={b['doc']} (recon_doc={c['source_filename']})")
