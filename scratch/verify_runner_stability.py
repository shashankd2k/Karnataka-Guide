import json
import time
import urllib.request
import os

BASE_URL = "http://ollama:11434"

payload_template = {
    "model": "phi3:mini",
    "prompt": "Tourist Question: Tell me about Belur temple.",
    "system": "You are the official AI Smart Tourist Guide for Karnataka, India. Answer in 2 concise sentences.",
    "stream": False,
    "keep_alive": "10m",
    "options": {
        "num_ctx": 1536,
        "num_thread": 2,
        "num_predict": 128,
        "temperature": 0.1,
        "top_p": 0.9,
        "stop": ["\n\n", "###", "\nTourist Question:", "\nTourist:", "\nUser:", "\nAssistant:", "\nQuestion:"]
    }
}

def get_ollama_ps():
    req = urllib.request.Request(f"{BASE_URL}/api/ps")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("models", [])
            if models:
                m = models[0]
                return {
                    "name": m.get("name"),
                    "size": m.get("size"),
                    "expires_at": m.get("expires_at"),
                    "context": m.get("context"),
                }
    except Exception as e:
        return {"error": str(e)}
    return {}

def run_turn(turn_idx):
    req = urllib.request.Request(
        f"{BASE_URL}/api/generate",
        data=json.dumps(payload_template).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    wall_ms = (time.perf_counter() - t0) * 1000.0
    load_ms = res.get("load_duration", 0) / 1e6
    eval_count = res.get("eval_count", 0)
    pe_count = res.get("prompt_eval_count", 0)
    pe_dur_ms = res.get("prompt_eval_duration", 0) / 1e6
    eval_dur_ms = res.get("eval_duration", 0) / 1e6
    ps_info = get_ollama_ps()
    
    return {
        "turn": turn_idx,
        "wall_ms": round(wall_ms, 2),
        "load_duration_ms": round(load_ms, 2),
        "prompt_tokens": pe_count,
        "prompt_eval_dur_ms": round(pe_dur_ms, 2),
        "generated_tokens": eval_count,
        "eval_dur_ms": round(eval_dur_ms, 2),
        "ps_info": ps_info,
        "response": res.get("response", "").strip()[:80]
    }

def main():
    print("=== Level 1 Runner Stability Verification ===", flush=True)
    turns = []
    for i in range(1, 4):
        print(f"Executing Turn {i}...", flush=True)
        rec = run_turn(i)
        turns.append(rec)
        print(f"Turn {i}: wall={rec['wall_ms']:.1f}ms, load={rec['load_duration_ms']:.2f}ms, gen={rec['generated_tokens']} tok, ps={rec['ps_info']}", flush=True)
        time.sleep(1)
        
    warm_turns = turns[1:]
    all_warm_fast_load = all(t["load_duration_ms"] < 1000.0 for t in warm_turns)
    print("\n--- Runner Stability Verdict ---", flush=True)
    print(f"Turn 1 Load Duration: {turns[0]['load_duration_ms']} ms")
    for t in warm_turns:
        print(f"Turn {t['turn']} Load Duration: {t['load_duration_ms']} ms (Warm preservation: {t['load_duration_ms'] < 1000.0})")
    print(f"Stable Model Residency Preserved: {all_warm_fast_load}")
    verdict = "PASS" if all_warm_fast_load else "FAIL"
    print(f"RUNNER STABILITY: {verdict}", flush=True)
    
    res = {
        "status": verdict,
        "turns": turns,
        "stable_residency": all_warm_fast_load
    }
    out_file = "/app/scratch/runner_stability_results.json" if os.path.exists("/app/scratch") else "scratch/runner_stability_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

if __name__ == "__main__":
    main()
