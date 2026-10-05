import ast
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    with open('backend/scratch/run_full_real_benchmark.py', 'r', encoding='utf-8') as f:
        code = f.read()

    tree = ast.parse(code)
    queries = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'benchmark_queries':
                    val_code = ast.unparse(node.value)
                    queries = eval(val_code)

    print(f"Total queries found: {len(queries)}")
    for q in queries:
        print(f"[{q['id']}] ({q['category']}): {q['query']}")
        print(f"    Expected Chunks: {q['expected_chunks']}")
        print(f"    Description: {q['expected_desc']}")

    out_path = 'scratch/level2_rerank_experiment/canonical_24_queries.json'
    with open(out_path, 'w', encoding='utf-8') as out_f:
        json.dump(queries, out_f, indent=2)
    print(f"\nSaved canonical fixture queries to {out_path}")

if __name__ == '__main__':
    main()
