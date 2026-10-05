import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import statistics
from typing import Dict, List, Any, Optional

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROMPTS_FILE = "scratch/production_prompts_30.json"
RESULTS_FILE = "scratch/production_output_results.json"
TMP_RESULTS_FILE = "scratch/production_output_results.json.tmp"

TERMINAL_PUNCTUATION_REGEX = re.compile(r'[\.\!\?।]["\']?\s*$')

def check_sentence_completion(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    # If ends with bracketed citation like [1]. or [1] or [2]
    if re.search(r'\[\d+\]\s*[\.\!\?।]?\s*$', cleaned):
        return True
    return bool(TERMINAL_PUNCTUATION_REGEX.search(cleaned))

def call_ollama_with_retry(
    system_prompt: str,
    user_prompt: str,
    num_predict: int = 256,
    num_ctx: int = 1024,
    port: int = 11434,
    max_retries: int = 1
) -> Dict[str, Any]:
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
        "keep_alive": "10m",
        "options": options
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            t0 = time.perf_counter()
            with urllib.request.urlopen(req, timeout=180) as resp:
                res = json.loads(resp.read().decode("utf-8"))
            res["wall_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            return res
        except (urllib.error.URLError, TimeoutError, Exception) as e:
            last_err = e
            print(f"    [ATTEMPT {attempt+1} FAILED] {type(e).__name__}: {e}")
            if attempt < max_retries:
                time.sleep(2)
    
    return {"error": str(last_err), "status": "TIMEOUT" if isinstance(last_err, TimeoutError) else "ERROR"}

def save_atomic(data: Dict[str, Any], filepath: str, tmp_filepath: str):
    with open(tmp_filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_filepath, filepath)

def main():
    if not os.path.exists(PROMPTS_FILE):
        print(f"Error: {PROMPTS_FILE} not found!")
        return

    with open(PROMPTS_FILE, "r", encoding="utf-8-sig") as f:
        prompts = json.load(f)

    # Load existing results to ensure resume capability
    existing_data = {"results": {}}
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8-sig") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "results" in loaded:
                    existing_data = loaded
        except Exception as e:
            print(f"Warning: Could not parse existing results file ({e}), starting fresh.")

    results_dict = existing_data.setdefault("results", {})
    completed_ids = set(results_dict.keys())

    print("=" * 85)
    print("RESUMABLE REAL PRODUCTION-ANSWER OUTPUT-LENGTH BENCHMARK (30 QUERIES)")
    print(f"Total Queries in Spec: {len(prompts)}")
    print(f"Already Completed Queries: {len(completed_ids)} / {len(prompts)}")
    if completed_ids:
        print(f"Completed IDs: {sorted(completed_ids)}")
    print("=" * 85)

    for item in prompts:
        qid = item["id"]
        q_text = item["query"]
        is_grounded = item.get("is_grounded", True)
        sys_prompt = item.get("system_prompt", "")
        user_prompt = item.get("user_prompt", "")
        exact_fallback = item.get("fallback", "Information is not available in the knowledge base.")

        if qid in completed_ids:
            print(f"[SKIP] Query {qid} already completed.")
            continue

        print(f"\n[EXEC] Running Query {qid}: \"{q_text}\" (grounded={is_grounded})...")

        if not is_grounded:
            # Ungrounded queries short-circuit at conversation layer to exact fallback
            record = {
                "query_id": qid,
                "query": q_text,
                "grounded": False,
                "input_tokens": 0,
                "num_ctx": 1024,
                "num_predict": 256,
                "num_thread": 0,
                "keep_alive": "10m",
                "response_text": exact_fallback,
                "eval_count": 0,
                "prompt_eval_count": 0,
                "load_duration_ms": 0.0,
                "prompt_eval_duration_ms": 0.0,
                "eval_duration_ms": 0.0,
                "total_duration_ms": 0.0,
                "generation_tokens_per_sec": 0.0,
                "reached_num_predict": False,
                "sentence_complete": True,
                "is_truncated": False,
                "truncation_flag": "NONE",
                "finish_reason": "ungrounded_fallback",
                "status": "FALLBACK_SHORT_CIRCUIT"
            }
            results_dict[qid] = record
            save_atomic(existing_data, RESULTS_FILE, TMP_RESULTS_FILE)
            print(f"--> COMPLETED {len(results_dict)} / 30 [FALLBACK] Short-circuit to exact fallback")
            continue

        # Grounded query -> call Ollama
        resp = call_ollama_with_retry(sys_prompt, user_prompt, num_predict=256, num_ctx=1024)

        if "error" in resp:
            err_msg = resp.get("error", "Unknown error")
            err_status = resp.get("status", "ERROR")
            print(f"--> [FAILED] Query {qid}: {err_status} - {err_msg}")
            record = {
                "query_id": qid,
                "query": q_text,
                "grounded": True,
                "input_tokens": 0,
                "num_ctx": 1024,
                "num_predict": 256,
                "num_thread": 0,
                "keep_alive": "10m",
                "response_text": "",
                "eval_count": 0,
                "prompt_eval_count": 0,
                "load_duration_ms": 0.0,
                "prompt_eval_duration_ms": 0.0,
                "eval_duration_ms": 0.0,
                "total_duration_ms": 0.0,
                "generation_tokens_per_sec": 0.0,
                "reached_num_predict": False,
                "sentence_complete": False,
                "is_truncated": False,
                "truncation_flag": "ERROR",
                "finish_reason": "error",
                "error": err_msg,
                "status": err_status
            }
        else:
            raw_text = resp.get("response", "").strip()
            eval_count = resp.get("eval_count", 0)
            prompt_eval_count = resp.get("prompt_eval_count", 0)
            load_ms = round(resp.get("load_duration", 0) / 1e6, 2)
            peval_ms = round(resp.get("prompt_eval_duration", 0) / 1e6, 2)
            eval_ms = round(resp.get("eval_duration", 0) / 1e6, 2)
            total_ms = round(resp.get("total_duration", 0) / 1e6, 2)
            gen_speed = round(eval_count / (eval_ms / 1000), 2) if eval_ms > 0 else 0.0
            done_reason = resp.get("done_reason", "stop")

            reached_cap = (eval_count >= 256)
            complete = check_sentence_completion(raw_text)
            truncated = (reached_cap and not complete) or (not complete)
            trunc_flag = "POSSIBLE_TRUNCATION" if reached_cap else "NONE"

            record = {
                "query_id": qid,
                "query": q_text,
                "grounded": True,
                "input_tokens": prompt_eval_count,
                "num_ctx": 1024,
                "num_predict": 256,
                "num_thread": 0,
                "keep_alive": "10m",
                "response_text": raw_text,
                "eval_count": eval_count,
                "prompt_eval_count": prompt_eval_count,
                "load_duration_ms": load_ms,
                "prompt_eval_duration_ms": peval_ms,
                "eval_duration_ms": eval_ms,
                "total_duration_ms": total_ms,
                "generation_tokens_per_sec": gen_speed,
                "reached_num_predict": reached_cap,
                "sentence_complete": complete,
                "is_truncated": truncated,
                "truncation_flag": trunc_flag,
                "finish_reason": done_reason,
                "status": "MEASURED"
            }
            print(f"--> Output: {eval_count} tokens | Speed: {gen_speed} tok/s | In: {prompt_eval_count} | Complete: {complete} | Cap: {reached_cap}")

        results_dict[qid] = record
        save_atomic(existing_data, RESULTS_FILE, TMP_RESULTS_FILE)
        print(f"--> COMPLETED {len(results_dict)} / 30 (Saved to {RESULTS_FILE})")

    # Final statistical summary
    all_results = list(results_dict.values())
    llm_measured = [r for r in all_results if r.get("status") == "MEASURED" and r.get("grounded") is True]
    fallbacks = [r for r in all_results if r.get("grounded") is False or r.get("status") == "FALLBACK_SHORT_CIRCUIT"]
    timeouts = [r for r in all_results if r.get("status") == "TIMEOUT"]
    errors = [r for r in all_results if r.get("status") == "ERROR"]

    eval_counts = [r["eval_count"] for r in llm_measured]
    input_counts = [r["prompt_eval_count"] for r in llm_measured]

    def calc_percentiles(vals: List[int]) -> Dict[str, Any]:
        if not vals:
            return {"p50": 0, "p90": 0, "p95": 0, "max": 0, "mean": 0}
        s = sorted(vals)
        n = len(s)
        p50 = round(statistics.median(s), 1)
        p90 = round(s[int(0.90 * (n - 1))], 1)
        p95 = round(s[int(0.95 * (n - 1))], 1)
        return {"p50": p50, "p90": p90, "p95": p95, "max": max(s), "mean": round(statistics.mean(s), 1)}

    out_stats = calc_percentiles(eval_counts)
    in_stats = calc_percentiles(input_counts)

    cap_hits = sum(1 for r in llm_measured if r.get("reached_num_predict"))
    truncated_count = sum(1 for r in llm_measured if r.get("is_truncated"))
    natural_complete = sum(1 for r in llm_measured if r.get("sentence_complete") and not r.get("reached_num_predict"))

    print("\n" + "=" * 85)
    print("PRODUCTION OUTPUT BENCHMARK FINAL SUMMARY (ALL 30 QUERIES)")
    print("=" * 85)
    print(f"TOTAL QUERIES: {len(all_results)}")
    print(f"VALID LLM SAMPLES: {len(llm_measured)}")
    print(f"UNGROUNDED FALLBACKS: {len(fallbacks)}")
    print(f"TIMEOUTS: {len(timeouts)}")
    print(f"ERRORS: {len(errors)}")
    print(f"OUTPUT P50: {out_stats['p50']}")
    print(f"OUTPUT P90: {out_stats['p90']}")
    print(f"OUTPUT P95: {out_stats['p95']}")
    print(f"OUTPUT MAX: {out_stats['max']}")
    print(f"ANSWERS HITTING DIAGNOSTIC CAP (256): {cap_hits}")
    print(f"TRUNCATED ANSWERS: {truncated_count}")
    print(f"NATURALLY COMPLETED ANSWERS: {natural_complete}")
    print(f"INPUT TOKENS P50: {in_stats['p50']} | P90: {in_stats['p90']} | P95: {in_stats['p95']} | MAX: {in_stats['max']}")

if __name__ == "__main__":
    main()
