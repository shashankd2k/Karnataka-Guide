import sys
import os
import json
import time
import urllib.request
import re

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

from app.application.rag.prompt_builder import SYSTEM_POLICY_ENGLISH, SYSTEM_POLICY_KANNADA

PROMPTS_FILE = "/app/scratch/production_prompts_30.json" if os.path.exists("/app/scratch/production_prompts_30.json") else "scratch/production_prompts_30.json"
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

def run_query(qid: str):
    with open(PROMPTS_FILE, "r", encoding="utf-8-sig") as f:
        prompts = {p["id"]: p for p in json.load(f)}
    
    if qid not in prompts:
        print(f"ERROR: Query ID {qid} not found in {PROMPTS_FILE}")
        return None
    
    p = prompts[qid]
    lang = p.get("language", "en")
    user_prompt = p["user_prompt"]
    system_prompt = SYSTEM_POLICY_KANNADA if lang == "kn" else SYSTEM_POLICY_ENGLISH
    
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
    
    print(f"\n--- Testing {qid} [{lang}] ---", flush=True)
    print(f"Query: {p.get('query', '')[:60]}...", flush=True)
    req = urllib.request.Request(
        "http://ollama:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    wall_ms = round((time.time() - t0) * 1000.0, 2)
    
    answer = res.get("response", "").strip()
    eval_count = res.get("eval_count", 0)
    eval_dur_ms = res.get("eval_duration", 0) / 1e6
    pe_count = res.get("prompt_eval_count", 0)
    pe_dur_ms = res.get("prompt_eval_duration", 0) / 1e6
    load_dur_ms = res.get("load_duration", 0) / 1e6
    
    gen_tok_per_sec = round(eval_count / (eval_dur_ms / 1000.0), 2) if eval_dur_ms > 0 else 0.0
    pe_tok_per_sec = round(pe_count / (pe_dur_ms / 1000.0), 2) if pe_dur_ms > 0 else 0.0
    
    sentence_complete = check_sentence_completion(answer)
    runaway_detected = detect_runaway(answer)
    truncated = (eval_count >= 128)
    sentence_count = count_sentences(answer)
    status = "PASS" if (not runaway_detected and sentence_complete and not truncated) else "FAIL"
    
    out = {
        "qid": qid,
        "status": status,
        "generated_tokens": eval_count,
        "prompt_tokens": pe_count,
        "prompt_eval_dur_ms": pe_dur_ms,
        "pe_tok_s": pe_tok_per_sec,
        "eval_dur_ms": eval_dur_ms,
        "gen_tok_s": gen_tok_per_sec,
        "load_dur_ms": load_dur_ms,
        "wall_ms": wall_ms,
        "sentence_complete": sentence_complete,
        "runaway_detected": runaway_detected,
        "truncated": truncated,
        "sentence_count": sentence_count,
        "answer": answer
    }
    
    print(f"Status: {status}", flush=True)
    print(f"Prompt Eval: {pe_count} tok in {pe_dur_ms:.1f}ms ({pe_tok_per_sec} tok/s)", flush=True)
    print(f"Generation: {eval_count} tok in {eval_dur_ms:.1f}ms ({gen_tok_per_sec} tok/s)", flush=True)
    print(f"Wall Latency: {wall_ms:.1f}ms (Load: {load_dur_ms:.1f}ms)", flush=True)
    print(f"Sentence Complete: {sentence_complete} | Runaway: {runaway_detected} | Truncated: {truncated}", flush=True)
    print(f"Answer: {answer}", flush=True)
    return out

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "P10"
    res = run_query(target)
    if res:
        out_file = f"/app/scratch/result_{target}.json" if os.path.exists("/app/scratch") else f"scratch/result_{target}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
