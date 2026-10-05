import json
import sys
sys.stdout.reconfigure(encoding="utf-8")

with open(r"D:\Karnataka Guide\evidence\20260927_recovery_answer_validation\reconstructed_production_inputs_all24.json", "r", encoding="utf-8") as f:
    d = json.load(f)

for qid in ["Q15", "Q18"]:
    q = d["queries"][qid]["arm_15"]
    q_text = d["queries"][qid]["query_text"]
    print(f"=== {qid} Query: '{q_text}' ===")
    print("User Prompt:")
    print(q["user_prompt"])
    print("\nAuthoritative Citations:")
    for c in q["authoritative_citations"]:
        print(f"  {c['citation_label']}: {c['source_filename']} p.{c['page_number']} - Section: {c.get('section_header')}")
    print("\n" + "=" * 60 + "\n")
