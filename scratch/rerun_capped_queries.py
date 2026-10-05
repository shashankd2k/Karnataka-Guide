import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import statistics
from typing import Dict, List, Any

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROMPTS_FILE = "scratch/production_prompts_30.json"
OUTPUT_RESULTS_FILE = "scratch/production_output_results.json"
DIAG_512_FILE = "scratch/diagnostic_512_results.json"

TARGET_IDS = ["P08", "P10", "P21", "P22", "P24", "P28"]

TERMINAL_PUNCTUATION_REGEX = re.compile(r'[\.\!\?।]["\']?\s*$')

def check_sentence_completion(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    if re.search(r'\[\d+\]\s*[\.\!\?।]?\s*$', cleaned):
        return True
    return bool(TERMINAL_PUNCTUATION_REGEX.search(cleaned))

def call_ollama(system_prompt: str, user_prompt: str, num_predict: int = 512, num_ctx: int = 1536, port: int = 11434) -> Dict[str, Any]:
    options = {
        "num_ctx": num_ctx,
        "num_predict": num_predict,
        "temperature": 0.1,
    }
    payload = {
        "model": "phi3:mini",
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": options
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    res["wall_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return res

def run_capped_test(num_predict: int = 512, target_ids: List[str] = TARGET_IDS) -> Dict[str, Any]:
    with open(PROMPTS_FILE, "r", encoding="utf-8-sig") as f:
        prompts = json.load(f)
    
    p_map = {p["id"]: p for p in prompts}
    results = {}

    print(f"\n--- Running Diagnostic Test with num_predict={num_predict} for {target_ids} ---")
    
    for qid in target_ids:
        p = p_map[qid]
        q_text = p["query"]
        sys_prompt = p.get("system_prompt", "")
        user_prompt = p.get("user_prompt", "")

        print(f"\n[QUERY {qid}] \"{q_text}\"")
        num_ctx = 2048 if num_predict > 512 else 1536
        resp = call_ollama(sys_prompt, user_prompt, num_predict=num_predict, num_ctx=num_ctx)
        
        raw_text = resp.get("response", "").strip()
        eval_count = resp.get("eval_count", 0)
        prompt_eval_count = resp.get("prompt_eval_count", 0)
        load_ms = round(resp.get("load_duration", 0) / 1e6, 2)
        peval_ms = round(resp.get("prompt_eval_duration", 0) / 1e6, 2)
        eval_ms = round(resp.get("eval_duration", 0) / 1e6, 2)
        total_ms = round(resp.get("total_duration", 0) / 1e6, 2)
        gen_speed = round(eval_count / (eval_ms / 1000), 2) if eval_ms > 0 else 0.0
        done_reason = resp.get("done_reason", "stop")

        reached_cap = (eval_count >= num_predict)
        complete = check_sentence_completion(raw_text)
        truncated = (reached_cap and not complete) or (not complete)

        natural_completion = "YES" if not reached_cap and complete else "UNKNOWN"
        possible_truncation = "YES" if reached_cap else ("YES" if not complete else "NO")

        record = {
            "query_id": qid,
            "query": q_text,
            "grounded": True,
            "input_tokens": prompt_eval_count,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "num_thread": 0,
            "keep_alive": "30m",
            "response_text": raw_text,
            "eval_count": eval_count,
            "prompt_eval_count": prompt_eval_count,
            "load_duration_ms": load_ms,
            "prompt_eval_duration_ms": peval_ms,
            "eval_duration_ms": eval_ms,
            "total_duration_ms": total_ms,
            "generation_tokens_per_sec": gen_speed,
            "reached_cap": reached_cap,
            "sentence_complete": complete,
            "is_truncated": truncated,
            "natural_completion": natural_completion,
            "possible_truncation": possible_truncation,
            "finish_reason": done_reason,
            "status": "MEASURED"
        }
        results[qid] = record
        print(f"  -> Tokens: {eval_count} / {num_predict} | Complete: {complete} | Natural: {natural_completion} | Truncated: {truncated} | Speed: {gen_speed} tok/s")

    return results

def main():
    print("=" * 85)
    print("FINAL TARGETED P0 CHECK: NATURAL OUTPUT MEASUREMENT FOR 6 CAPPED QUERIES")
    print("=" * 85)

    # 1. Run with num_predict=512
    res_512 = run_capped_test(num_predict=512, target_ids=TARGET_IDS)

    # 2. Check for escalation: did any query reach 512?
    still_capped = [qid for qid, r in res_512.items() if r["reached_cap"]]
    
    if still_capped:
        print(f"\n[ESCALATION REQUIRED] {len(still_capped)} queries reached 512 cap: {still_capped}")
        res_768 = run_capped_test(num_predict=768, target_ids=still_capped)
        for qid, r in res_768.items():
            res_512[qid] = r
    else:
        print("\n[NO ESCALATION REQUIRED] All 6 queries naturally terminated before 512 cap!")

    # Save diagnostic results
    with open(DIAG_512_FILE, "w", encoding="utf-8") as f:
        json.dump(res_512, f, indent=2, ensure_ascii=False)
    print(f"\nDiagnostic results saved to {DIAG_512_FILE}")

    # 3. Load full 30-query production output results and update the 6 queries
    with open(OUTPUT_RESULTS_FILE, "r", encoding="utf-8-sig") as f:
        prod_data = json.load(f)

    for qid in TARGET_IDS:
        new_rec = res_512[qid]
        # Keep schema aligned
        prod_data["results"][qid] = {
            "query_id": qid,
            "query": new_rec["query"],
            "grounded": True,
            "input_tokens": new_rec["input_tokens"],
            "num_ctx": new_rec["num_ctx"],
            "num_predict": new_rec["num_predict"],
            "num_thread": 0,
            "keep_alive": "30m",
            "response_text": new_rec["response_text"],
            "eval_count": new_rec["eval_count"],
            "prompt_eval_count": new_rec["prompt_eval_count"],
            "load_duration_ms": new_rec["load_duration_ms"],
            "prompt_eval_duration_ms": new_rec["prompt_eval_duration_ms"],
            "eval_duration_ms": new_rec["eval_duration_ms"],
            "total_duration_ms": new_rec["total_duration_ms"],
            "generation_tokens_per_sec": new_rec["generation_tokens_per_sec"],
            "reached_num_predict": new_rec["reached_cap"],
            "sentence_complete": new_rec["sentence_complete"],
            "is_truncated": new_rec["is_truncated"],
            "truncation_flag": "POSSIBLE_TRUNCATION" if new_rec["reached_cap"] else "NONE",
            "finish_reason": new_rec["finish_reason"],
            "status": "MEASURED"
        }

    with open(OUTPUT_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(prod_data, f, indent=2, ensure_ascii=False)
    print(f"Updated {OUTPUT_RESULTS_FILE} with naturally completed answers for {TARGET_IDS}")

    # 4. Recompute statistics
    all_results = prod_data["results"].values()
    grounded_llm = [r for r in all_results if r.get("grounded") is True]
    fallbacks = [r for r in all_results if r.get("grounded") is False]

    eval_counts = sorted([r["eval_count"] for r in grounded_llm])
    n = len(eval_counts)
    p50 = round(statistics.median(eval_counts), 1)
    p90 = round(eval_counts[int(0.90 * (n - 1))], 1)
    p95 = round(eval_counts[int(0.95 * (n - 1))], 1)
    max_val = max(eval_counts)

    cap_hits = sum(1 for r in grounded_llm if r.get("reached_num_predict"))
    truncated_count = sum(1 for r in grounded_llm if r.get("is_truncated"))
    natural_complete = sum(1 for r in grounded_llm if r.get("sentence_complete") and not r.get("reached_num_predict"))

    print("\n" + "=" * 85)
    print("RECOMPUTED NATURAL OUTPUT TOKEN DISTRIBUTION (27 REAL LLM RESPONSES)")
    print("=" * 85)
    print(f"OUTPUT SAMPLE COUNT: {len(grounded_llm)}")
    print(f"OUTPUT P50: {p50}")
    print(f"OUTPUT P90: {p90}")
    print(f"OUTPUT P95: {p95}")
    print(f"OUTPUT MAX: {max_val}")
    print(f"ANSWERS STILL HITTING CAP: {cap_hits}")
    print(f"TRUNCATED ANSWERS: {truncated_count}")
    print(f"NATURALLY COMPLETED ANSWERS: {natural_complete}")
    print(f"FULL EVAL COUNTS: {eval_counts}")

    # Context safety calculation
    max_single_turn_input = 895
    max_5_turn_input = 798

    st_p95 = max_single_turn_input + p95
    st_max = max_single_turn_input + max_val
    t5_p95 = max_5_turn_input + p95
    t5_max = max_5_turn_input + max_val

    hr_st_1536 = 1536 - st_max
    hr_5t_1536 = 1536 - t5_max

    print("\n" + "=" * 85)
    print("FINAL CONTEXT SAFETY CALCULATION")
    print("=" * 85)
    print(f"MAX SINGLE-TURN INPUT: {max_single_turn_input}")
    print(f"MAX 5-TURN INPUT: {max_5_turn_input}")
    print(f"SINGLE-TURN + OUTPUT P95: {st_p95}")
    print(f"SINGLE-TURN + OUTPUT MAX: {st_max}")
    print(f"5-TURN + OUTPUT P95: {t5_p95}")
    print(f"5-TURN + OUTPUT MAX: {t5_max}")
    print(f"1536 WORST-CASE SINGLE-TURN HEADROOM: {hr_st_1536} tokens")
    print(f"1536 WORST-CASE 5-TURN HEADROOM: {hr_5t_1536} tokens")

if __name__ == "__main__":
    main()
