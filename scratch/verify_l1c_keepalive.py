import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:80"

def get_wsl_mem():
    try:
        res = subprocess.run(["wsl", "-e", "cat", "/proc/meminfo"], capture_output=True, text=True, timeout=5)
        mem_avail = 0
        swap_used = 0
        for line in res.stdout.splitlines():
            if line.startswith("MemAvailable:"):
                mem_avail = int(line.split()[1])
            elif line.startswith("SwapTotal:"):
                st = int(line.split()[1])
            elif line.startswith("SwapFree:"):
                sf = int(line.split()[1])
                swap_used = st - sf
        return {
            "avail_mb": round(mem_avail / 1024.0, 1),
            "swap_mb": round(swap_used / 1024.0, 1),
        }
    except Exception:
        return {"avail_mb": 0.0, "swap_mb": 0.0}

def get_ollama_runner_pid():
    try:
        res = subprocess.run(
            ["docker", "exec", "karnatakaguide-ollama-1", "ps", "-eo", "pid,comm,rss"],
            capture_output=True, text=True, timeout=10
        )
        for line in res.stdout.splitlines():
            if "llama" in line or "runner" in line:
                parts = line.split()
                if len(parts) >= 3:
                    return parts[0], round(int(parts[2]) / 1024.0, 1)
        return None, 0.0
    except Exception:
        return None, 0.0

def run_prompt_direct(prompt_text):
    payload = {
        "model": "phi3:mini",
        "prompt": prompt_text,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "num_ctx": 1536,
            "num_thread": 2,
            "num_predict": 32,
            "temperature": 0.1
        }
    }
    t0 = time.perf_counter()
    curl_cmd = [
        "docker", "exec", "-i", "karnatakaguide-backend-1",
        "curl", "-s", "-X", "POST", "http://ollama:11434/api/generate",
        "-H", "Content-Type: application/json",
        "-d", "@-"
    ]
    res = subprocess.run(curl_cmd, input=json.dumps(payload), capture_output=True, text=True, timeout=120)
    dur_ms = (time.perf_counter() - t0) * 1000.0
    try:
        data = json.loads(res.stdout)
    except Exception as e:
        data = {"error": str(e), "raw": res.stdout[:100]}
    return data, dur_ms

def main():
    print("=== L1-C: Controlled Keep-Alive Consecutive Turn Verification ===")
    turns = [
        ("Turn 1", "Who built Belur temple?"),
        ("Turn 2", "What stone was used at Belur?"),
        ("Turn 3", "Who commissioned Halebidu temple?"),
    ]
    
    results = []
    initial_pid, initial_rss = get_ollama_runner_pid()
    print(f"Initial Runner PID: {initial_pid} (RSS: {initial_rss} MB)")
    
    for label, query in turns:
        print(f"\n--- Running {label}: {query} ---")
        mem = get_wsl_mem()
        data, wall_ms = run_prompt_direct(query)
        curr_pid, curr_rss = get_ollama_runner_pid()
        
        load_ms = round(data.get("load_duration", 0) / 1e6, 2)
        peval_ms = round(data.get("prompt_eval_duration", 0) / 1e6, 2)
        eval_ms = round(data.get("eval_duration", 0) / 1e6, 2)
        eval_cnt = data.get("eval_count", 0)
        ttft_ms = round(load_ms + peval_ms, 2)
        tps = round(eval_cnt / (eval_ms / 1000.0), 2) if eval_ms > 0 else 0.0
        
        res_info = {
            "turn": label,
            "query": query,
            "runner_pid": curr_pid,
            "pid_preserved": (curr_pid == initial_pid),
            "load_duration_ms": load_ms,
            "prompt_eval_ms": peval_ms,
            "eval_ms": eval_ms,
            "eval_count": eval_cnt,
            "ttft_ms": ttft_ms,
            "tokens_per_sec": tps,
            "wall_latency_ms": round(wall_ms, 2),
            "ollama_rss_mb": curr_rss,
            "wsl_avail_ram_mb": mem["avail_mb"],
            "swap_mb": mem["swap_mb"],
            "answer": data.get("response", "").strip()[:60],
        }
        results.append(res_info)
        print(f"{label} Complete: Load={load_ms}ms, TTFT={ttft_ms}ms, Gen={eval_cnt} tok ({tps} tok/s), Runner PID={curr_pid}")
        time.sleep(2)  # small pause between turns within 10m window
    
    all_pids = [r["runner_pid"] for r in results]
    zero_reload = all(r["load_duration_ms"] < 500.0 for r in results)
    pid_stable = len(set(all_pids)) == 1 and all_pids[0] == initial_pid
    
    print("\n=======================================================")
    print(f"KEEP-ALIVE VERIFICATION: {'SUCCESS' if (pid_stable and zero_reload) else 'FAILED'}")
    print(f"PIDs: {all_pids} | PID Stable: {pid_stable} | Zero Reload: {zero_reload}")
    print("=======================================================")
    
    with open("scratch/l1c_keepalive_results.json", "w") as f:
        json.dump({
            "status": "PASS" if (pid_stable and zero_reload) else "FAIL",
            "initial_pid": initial_pid,
            "pid_stable": pid_stable,
            "zero_reload": zero_reload,
            "results": results
        }, f, indent=2)
    print("Saved results to scratch/l1c_keepalive_results.json")

if __name__ == "__main__":
    main()
