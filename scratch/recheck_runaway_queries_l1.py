import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

PROMPTS_FILE = "/app/scratch/production_prompts_30.json" if os.path.exists("/app/scratch/production_prompts_30.json") else "scratch/production_prompts_30.json"
TARGET_IDS = ["P10", "P08", "P21", "P22", "P24", "P28", "P07"]
SCRATCH_DIR = "/app/scratch" if os.path.exists("/app/scratch") else "scratch"
ALL_RESULTS_FILE = os.path.join(SCRATCH_DIR, "l1e_runaway_results.json")

TERMINAL_PUNCTUATION_REGEX = re.compile(r'[\.\!\?।]["\']?\s*$')

def check_sentence_completion(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    if re.search(r'\[\d+\]\s*[\.\!\?।]?\s*$', cleaned):
        return True
    return bool(TERMINAL_PUNCTUATION_REGEX.search(cleaned))

def detect_runaway(text: str) -> bool:
    lower = text.lower()
    runaway_markers = [
        "tourist:", "user:", "assistant:", "guide:", "visitor:",
        "tourist question:", "question:", "tourist query:"
    ]
    for m in runaway_markers:
        if m in lower:
            return True
    return False

def count_sentences(text: str) -> int:
    cleaned = text.strip()
    sentences = [s.strip() for s in re.split(r'[\.\!\?।]+', cleaned) if s.strip()]
    return len(sentences)

def call_ollama(system_prompt: str, user_prompt: str, base_url: str = "http://ollama:11434") -> dict:
    payload = {
        "model": "phi3:mini",
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "num_ctx": 1536,
            "num_thread": 2,
            "num_predict": 128,
            "temperature": 0.1,
            "top_p": 0.9,
            "stop": ["\n\n", "###", "\nTourist Question:", "\nTourist:", "\nUser:", "\nAssistant:", "\nQuestion:"],
        }
    }
    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    res["wall_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
    return res

def save_atomic(filepath: str, data: dict):
    tmp_path = filepath + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, filepath)

def main():
    print("=== Level 1-E: Runaway Queries Recheck with Tightened Prompt ===", flush=True)
    from app.application.rag.prompt_builder import SYSTEM_POLICY_ENGLISH, SYSTEM_POLICY_KANNADA
    
    with open(PROMPTS_FILE, "r", encoding="utf-8-sig") as f:
        prompts = json.load(f)
    p_map = {p["id"]: p for p in prompts}
    
    results = {}
    if os.path.exists(ALL_RESULTS_FILE):
        try:
            with open(ALL_RESULTS_FILE, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception:
            results = {}

    # Also check individual result files
    for qid in TARGET_IDS:
        single_file = os.path.join(SCRATCH_DIR, f"result_{qid}.json")
        if qid not in results and os.path.exists(single_file):
            try:
                with open(single_file, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
                if sdata.get("status") == "PASS":
                    results[qid] = sdata
            except Exception:
                pass
    
    total = len(TARGET_IDS)
    completed_count = sum(1 for qid in TARGET_IDS if results.get(qid, {}).get("status") == "PASS")
    print(f"Initial State: {completed_count}/{total} already completed and passing.", flush=True)
    
    for idx, qid in enumerate(TARGET_IDS, start=1):
        if results.get(qid, {}).get("status") == "PASS":
            print(f"Skipping already passed {qid} ({idx}/{total})", flush=True)
            continue
            
        p_data = p_map[qid]
        query_text = p_data.get("query_en") or p_data.get("query", "")
        lang = p_data.get("language", "en")
        user_prompt = p_data["user_prompt"]
        
        system_policy = SYSTEM_POLICY_KANNADA if lang == "kn" else SYSTEM_POLICY_ENGLISH
        
        print(f"\nEvaluating {qid} [{lang}] ({query_text[:50]}...)...", flush=True)
        res = call_ollama(system_policy, user_prompt)
        
        answer = res.get("response", "").strip()
        eval_count = res.get("eval_count", 0)
        eval_duration_ms = res.get("eval_duration", 0) / 1e6
        prompt_eval_count = res.get("prompt_eval_count", 0)
        prompt_eval_duration_ms = res.get("prompt_eval_duration", 0) / 1e6
        load_duration_ms = res.get("load_duration", 0) / 1e6
        wall_ms = res.get("wall_ms", 0.0)
        
        gen_tok_per_sec = round(eval_count / (eval_duration_ms / 1000.0), 2) if eval_duration_ms > 0 else 0.0
        pe_tok_per_sec = round(prompt_eval_count / (prompt_eval_duration_ms / 1000.0), 2) if prompt_eval_duration_ms > 0 else 0.0
        
        sentence_complete = check_sentence_completion(answer)
        runaway_detected = detect_runaway(answer)
        truncated = (eval_count >= 128)
        sentence_count = count_sentences(answer)
        
        status = "PASS" if (not runaway_detected and sentence_complete and not truncated) else "FAIL"
        
        res_entry = {
            "qid": qid,
            "status": status,
            "generated_tokens": eval_count,
            "prompt_tokens": prompt_eval_count,
            "prompt_eval_dur_ms": round(prompt_eval_duration_ms, 2),
            "pe_tok_s": pe_tok_per_sec,
            "eval_dur_ms": round(eval_duration_ms, 2),
            "gen_tok_s": gen_tok_per_sec,
            "load_dur_ms": round(load_duration_ms, 2),
            "wall_ms": wall_ms,
            "sentence_complete": sentence_complete,
            "runaway_detected": runaway_detected,
            "truncated": truncated,
            "sentence_count": sentence_count,
            "answer": answer,
        }
        
        results[qid] = res_entry
        
        # Persist individually and globally
        single_file = os.path.join(SCRATCH_DIR, f"result_{qid}.json")
        save_atomic(single_file, res_entry)
        save_atomic(ALL_RESULTS_FILE, results)
        
        completed_count = sum(1 for q in TARGET_IDS if results.get(q, {}).get("status") == "PASS")
        print(f"COMPLETED {completed_count} / {total} | {qid}: {status} | Tokens: {eval_count} ({gen_tok_per_sec} tok/s) | Complete: {sentence_complete} | Runaway: {runaway_detected}", flush=True)
        print(f"Answer snippet: {answer[:120]}...", flush=True)

    print("\n=======================================================", flush=True)
    print("SUMMARY OF RUNAWAY RECHECK:", flush=True)
    print("Query | Status | Tokens | Gen Speed | Sentence Complete | Runaway Detected | Truncated", flush=True)
    print("-" * 85, flush=True)
    for qid in TARGET_IDS:
        r = results.get(qid, {})
        if r:
            print(f"{qid:<5} | {r.get('status',''):<6} | {r.get('generated_tokens', 0):<6} | {r.get('gen_tok_s', 0.0):<9} | {str(r.get('sentence_complete','')):<17} | {str(r.get('runaway_detected','')):<16} | {str(r.get('truncated','')):<9}", flush=True)
    print("=======================================================", flush=True)

if __name__ == "__main__":
    main()
