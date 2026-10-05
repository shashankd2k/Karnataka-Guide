import json
import hashlib
import os

path = r"evidence/20260927_recovery_answer_validation/live_generation_validation_results.jsonl"
size = os.path.getsize(path)
sha256 = hashlib.sha256(open(path, "rb").read()).hexdigest()
print(f"File: {path} ({size} bytes, SHA-256: {sha256})")

with open(path, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

print(f"Total valid non-empty lines: {len(lines)}")
for i, l in enumerate(lines, 1):
    rec = json.loads(l)
    print(f"Record {i}:")
    print(f"  Request Index: {rec.get('request_index')}")
    print(f"  Timestamp:     {rec.get('timestamp')}")
    print(f"  Query ID:      {rec.get('query_id')} ({rec.get('arm')})")
    print(f"  Query Text:    '{rec.get('query_text')}'")
    print(f"  Elapsed ms:    {rec.get('elapsed_ms')}")
    print(f"  Error:         {rec.get('error')}")
    print(f"  Done Reason:   {rec.get('telemetry', {}).get('done_reason')}")
    print(f"  Tokens Eval:   {rec.get('telemetry', {}).get('eval_count')}")
    print(f"  Raw Answer:    '{rec.get('raw_response')}'")
    print(f"  Citations:     {rec.get('citations_emitted')}")
    print()
