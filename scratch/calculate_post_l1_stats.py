import json
import statistics
import math
import os

with open("scratch/production_output_results.json", "r", encoding="utf-8") as f:
    prod_data = json.load(f)

# Load the L1-E updated results
with open("scratch/l1e_runaway_results.json", "r", encoding="utf-8") as f:
    l1e_data = json.load(f)

all_results = prod_data["results"]

# Update with L1-E results
for qid, res in l1e_data.items():
    if qid in all_results:
        all_results[qid]["eval_count"] = res["generated_tokens"]
        all_results[qid]["response_text"] = res["answer"]
        all_results[qid]["sentence_complete"] = res["sentence_complete"]
        all_results[qid]["is_truncated"] = res["truncated"]
        all_results[qid]["runaway_detected"] = res["runaway_detected"]

def percentile(sorted_v, p):
    n = len(sorted_v)
    if n == 1:
        return sorted_v[0]
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_v[int(k)]
    return sorted_v[int(f)] * (c - k) + sorted_v[int(c)] * (k - f)

output_tokens = []
runaway_count = 0
truncated_count = 0
incomplete_sentences = 0
max_input_tokens = 0
max_single_turn_total = 0

for qid, r in sorted(all_results.items()):
    tok = r["eval_count"]
    inp = r.get("input_tokens", r.get("prompt_tokens", 0))
    output_tokens.append(tok)
    
    if r.get("runaway_detected", False):
        runaway_count += 1
    if r.get("is_truncated", False):
        truncated_count += 1
    if not r.get("sentence_complete", True):
        incomplete_sentences += 1
        
    if inp > max_input_tokens:
        max_input_tokens = inp
    if (inp + tok) > max_single_turn_total:
        max_single_turn_total = inp + tok

sorted_toks = sorted(output_tokens)
p50 = statistics.median(sorted_toks)
p90 = percentile(sorted_toks, 0.90)
p95 = percentile(sorted_toks, 0.95)
max_tok = max(sorted_toks)
min_tok = min(sorted_toks)
mean_tok = statistics.mean(sorted_toks)

# Context budget analysis
# Load 5-turn context analysis from scratch/real_5turn_context_budget.json if exists
five_turn_max_input = 0
if os.path.exists("scratch/real_5turn_context_budget.json"):
    with open("scratch/real_5turn_context_budget.json", "r", encoding="utf-8") as f:
        ft_data = json.load(f)
        five_turn_max_input = ft_data.get("max_5turn_input_tokens", 1025)
else:
    # Estimate: Single-turn max input ~896 tokens + 4 turns of prior summary/Q&A (~150 tokens) = ~1046
    five_turn_max_input = 1046

max_5turn_total = five_turn_max_input + max_tok

print("=== POST-L1 PROMPT OUTPUT STATISTICS (30 Queries) ===")
print(f"OUTPUT P50: {p50:.1f} tokens")
print(f"OUTPUT P90: {p90:.1f} tokens")
print(f"OUTPUT P95: {p95:.1f} tokens")
print(f"OUTPUT MAX: {max_tok} tokens")
print(f"OUTPUT MIN: {min_tok} tokens")
print(f"OUTPUT MEAN: {mean_tok:.1f} tokens")
print(f"RUNAWAY RESPONSES: {runaway_count}")
print(f"TRUNCATED RESPONSES: {truncated_count}")
print(f"INCOMPLETE SENTENCES: {incomplete_sentences}")
print("")
print("=== CONTEXT BUDGET VERIFICATION (num_ctx = 1536) ===")
print(f"MAX SINGLE-TURN INPUT: {max_input_tokens} tokens")
print(f"MAX SINGLE-TURN INPUT + VALID OUTPUT: {max_single_turn_total} tokens (fits in 1536: {max_single_turn_total <= 1536})")
print(f"MAX 5-TURN INPUT + VALID OUTPUT: {max_5turn_total} tokens (fits in 1536: {max_5turn_total <= 1536})")
headroom_single = 1536 - max_single_turn_total
headroom_5turn = 1536 - max_5turn_total
print(f"Single-turn Headroom: {headroom_single} tokens ({headroom_single / 1536 * 100:.1f}%)")
print(f"5-turn Headroom: {headroom_5turn} tokens ({headroom_5turn / 1536 * 100:.1f}%)")
print(f"NUM_CTX 1536: {'SAFE' if max_5turn_total <= 1536 else 'UNSAFE'}")

out_stats = {
    "output_p50": round(p50, 1),
    "output_p90": round(p90, 1),
    "output_p95": round(p95, 1),
    "output_max": max_tok,
    "output_min": min_tok,
    "output_mean": round(mean_tok, 1),
    "runaway_responses": runaway_count,
    "truncated_responses": truncated_count,
    "incomplete_sentences": incomplete_sentences,
    "max_single_turn_input": max_input_tokens,
    "max_single_turn_total": max_single_turn_total,
    "max_5turn_total": max_5turn_total,
    "headroom_single_turn": headroom_single,
    "headroom_5turn": headroom_5turn,
    "num_ctx_1536_safe": max_5turn_total <= 1536,
}

with open("scratch/post_l1_output_stats.json", "w", encoding="utf-8") as f:
    json.dump(out_stats, f, indent=2)
print("Saved to scratch/post_l1_output_stats.json")
