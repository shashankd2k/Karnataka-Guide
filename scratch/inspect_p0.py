import json
import os

paths = [
    "scratch/p0_results.json",
    "tests/benchmarks/p0_results.json",
    "backend/tests/benchmarks/p0_results.json"
]

for p in paths:
    if os.path.exists(p):
        print(f"=== {p} ({os.path.getsize(p)} bytes) ===")
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for k, v in data.items():
                    if isinstance(v, dict):
                        print(f"  {k}: {list(v.keys())}")
                    elif isinstance(v, list):
                        print(f"  {k}: list of {len(v)} items")
                    else:
                        print(f"  {k}: {v}")
            except Exception as e:
                print(f"  Error reading json: {e}")
    else:
        print(f"=== {p} DOES NOT EXIST ===")
