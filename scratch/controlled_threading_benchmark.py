import json
import random
import statistics
import subprocess
import sys
import time
from typing import Any, Dict, List

# Standardized prompt for controlled threading and keep-alive benchmarks
THREADING_PROMPT = "Describe the Hoysala architecture of Belur in three concise sentences."


def get_docker_memory():
    try:
        res = subprocess.run(
            ["docker", "exec", "karnatakaguide-backend-1", "cat", "/proc/meminfo"],
            capture_output=True, text=True, timeout=5, check=True
        )
        mem = {}
        for line in res.stdout.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                p = v.strip().split()
                mem[k.strip()] = int(p[0]) if p and p[0].isdigit() else 0
        return {
            "wsl_avail_mb": round(mem.get("MemAvailable", 0) / 1024.0, 1),
            "swap_used_mb": round((mem.get("SwapTotal", 0) - mem.get("SwapFree", 0)) / 1024.0, 1)
        }
    except Exception as e:
        return {"wsl_avail_mb": 0.0, "swap_used_mb": 0.0}

def get_ollama_process_info():
    try:
        res = subprocess.run(
            ["docker", "exec", "karnatakaguide-ollama-1", "ps", "-eo", "pid,comm,rss"],
            capture_output=True, text=True, timeout=5, check=True
        )
        pid = "unknown"
        rss_kb = 0
        for line in res.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 3 and ("ollama" in parts[1] or "llama" in parts[1]):
                pid = parts[0]
                rss_kb += int(parts[2]) if parts[2].isdigit() else 0
        return {"pid": pid, "rss_mb": round(rss_kb / 1024.0, 1)}
    except Exception:
        return {"pid": "unknown", "rss_mb": 0.0}

def send_ollama_request(
    num_thread: int,
    timeout_sec: int = 180,
    prompt: str = THREADING_PROMPT,
    keep_alive: str = "10m",
    num_predict: int = 64
) -> Dict[str, Any]:
    options = {
        "num_ctx": 1024,
        "num_predict": num_predict,
        "temperature": 0.1
    }
    if num_thread > 0:
        options["num_thread"] = num_thread

    payload = {
        "model": "phi3:mini",
        "prompt": prompt,
        "stream": False,
        "keep_alive": keep_alive,
        "options": options
    }

    payload_str = json.dumps(payload)
    script = f"""import urllib.request, json, time
payload = {repr(payload_str)}.encode('utf-8')
req = urllib.request.Request('http://ollama:11434/api/generate', data=payload, headers={{'Content-Type': 'application/json'}})
t0 = time.perf_counter()
with urllib.request.urlopen(req, timeout={timeout_sec}) as resp:
    raw = resp.read().decode()
    t1 = time.perf_counter()
data = json.loads(raw)
data['client_total_ms'] = (t1 - t0) * 1000
print(json.dumps(data))
"""
    res = subprocess.run(
        ["docker", "exec", "-i", "karnatakaguide-backend-1", "python"],
        input=script, capture_output=True, text=True, timeout=timeout_sec + 40
    )
    if res.returncode != 0:
        raise RuntimeError(f"docker exec failed (code {res.returncode}):\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
    for line in res.stdout.splitlines():
        if line.startswith("{") and "done" in line:
            return json.loads(line)
    raise RuntimeError(f"Failed to parse ollama output: {res.stdout} {res.stderr}")

def main():
    print("=== CONTROLLED CPU THREADING VERIFICATION (Intel Core i3-1115G4) ===")
    print("Testing settings [4, 2, 0, 3, 1] with individual runner pre-warming and warm confirmation...")

    # Thread matrix: 0=auto, 1, 2 (physical), 3, 4 (logical)
    # Tested in order [2, 0, 1, 3, 4]
    settings_order = [2, 0, 1, 3, 4]
    results_by_thread = {t: [] for t in [0, 1, 2, 3, 4]}

    for t in settings_order:
        label = "default/auto" if t == 0 else f"{t}_threads"
        print(f"\n=======================================================")
        print(f"THREAD SETTING: num_thread = {label}")
        print(f"=======================================================")
        
        try:
            # Step 1: Warm up the runner for this specific thread setting
            print(f"Warming runner for {label} (timeout 240s)...", end=" ", flush=True)
            warm_data = send_ollama_request(num_thread=t, timeout_sec=240)
            warm_load_ms = round(warm_data.get("load_duration", 0) / 1e6, 2)
            print(f"Done! load_duration={warm_load_ms:.2f} ms")

            # Step 2: Confirm load_duration is negligible (< 100ms) before counting runs
            if warm_load_ms > 100:
                print(f"Confirming warm residency for {label} (<100ms)...", end=" ", flush=True)
                confirm_data = send_ollama_request(num_thread=t, timeout_sec=120)
                confirm_load_ms = round(confirm_data.get("load_duration", 0) / 1e6, 2)
                print(f"Confirmed! load_duration={confirm_load_ms:.2f} ms")

            # Step 3: Execute 3 measured warm runs on the resident runner
            print(f"Executing 3 measured warm runs for {label}...")
            for run_idx in range(1, 4):
                print(f"  Run {run_idx}/3 ({label})...", end=" ", flush=True)
                mem = get_docker_memory()
                proc = get_ollama_process_info()
                
                data = send_ollama_request(num_thread=t, timeout_sec=120)
                
                load_dur_ms = round(data.get("load_duration", 0) / 1e6, 2)
                prompt_eval_count = data.get("prompt_eval_count", 0)
                prompt_eval_ms = round(data.get("prompt_eval_duration", 0) / 1e6, 2)
                eval_count = data.get("eval_count", 0)
                eval_ms = round(data.get("eval_duration", 0) / 1e6, 2)
                total_dur_ms = round(data.get("total_duration", 0) / 1e6, 2)
                client_total_ms = round(data.get("client_total_ms", 0), 2)
                
                prompt_tok_sec = round((prompt_eval_count / (prompt_eval_ms / 1000.0)), 2) if prompt_eval_ms > 0 else 0.0
                gen_tok_sec = round((eval_count / (eval_ms / 1000.0)), 2) if eval_ms > 0 else 0.0
                warm_ttft_ms = round(load_dur_ms + prompt_eval_ms, 2)

                run_record = {
                    "run_idx": run_idx,
                    "num_thread": t,
                    "label": label,
                    "load_duration_ms": load_dur_ms,
                    "prompt_eval_duration_ms": prompt_eval_ms,
                    "prompt_eval_count": prompt_eval_count,
                    "prompt_tokens_per_sec": prompt_tok_sec,
                    "eval_duration_ms": eval_ms,
                    "eval_count": eval_count,
                    "generation_tokens_per_sec": gen_tok_sec,
                    "warm_ttft_ms": warm_ttft_ms,
                    "total_duration_ms": total_dur_ms,
                    "client_total_ms": client_total_ms,
                    "runner_pid": proc["pid"],
                    "ollama_rss_mb": proc["rss_mb"],
                    "wsl_avail_mb": mem["wsl_avail_mb"],
                    "swap_used_mb": mem["swap_used_mb"],
                }
                results_by_thread[t].append(run_record)
                print(f"Done! Warm TTFT={warm_ttft_ms}ms, PromptEval={prompt_tok_sec}tok/s, GenSpeed={gen_tok_sec}tok/s, LoadDur={load_dur_ms}ms (PID: {proc['pid']})")
        except Exception as exc:
            print(f"FAILED for {label}: {exc}")
            subprocess.run(["docker", "compose", "restart", "ollama"], check=False)
            time.sleep(5)



    # Compute summary statistics
    summary = {}
    print("\n=== CONTROLLED THREADING SUMMARY (MEDIAN WARM PERFORMANCE) ===")
    print(f"{'Thread Setting':<18} | {'Median TTFT (ms)':<16} | {'Median Prompt tok/s':<20} | {'Median Gen tok/s':<16} | {'Median Total (ms)':<18}")
    print("-" * 96)

    for t in [0, 1, 2, 3, 4]:
        label = "default/auto" if t == 0 else f"{t}_threads"
        runs = results_by_thread[t]
        
        if runs:
            med_ttft = statistics.median([r["warm_ttft_ms"] for r in runs])
            med_prompt_speed = statistics.median([r["prompt_tokens_per_sec"] for r in runs])
            med_gen_speed = statistics.median([r["generation_tokens_per_sec"] for r in runs])
            med_total = statistics.median([r["total_duration_ms"] for r in runs])
            med_load = statistics.median([r["load_duration_ms"] for r in runs])
        else:
            med_ttft = -1.0
            med_prompt_speed = 0.0
            med_gen_speed = 0.0
            med_total = -1.0
            med_load = -1.0

        summary[label] = {
            "num_thread": t,
            "median_warm_ttft_ms": round(med_ttft, 2),
            "median_prompt_tokens_per_sec": round(med_prompt_speed, 2),
            "median_gen_tokens_per_sec": round(med_gen_speed, 2),
            "median_total_duration_ms": round(med_total, 2),
            "median_load_duration_ms": round(med_load, 2),
            "runs": runs
        }
        print(f"{label:<18} | {med_ttft:<16.2f} | {med_prompt_speed:<20.2f} | {med_gen_speed:<16.2f} | {med_total:<18.2f}")

    with open("scratch/controlled_threading_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("\nSaved controlled threading results to scratch/controlled_threading_results.json")

    # Item 8: Controlled Keep-Alive Result Consistency Check
    print("\n=== CONTROLLED KEEP-ALIVE CONSISTENCY CHECK (5m vs 10m vs -1) ===")
    print("Testing under identical real production prompt and identical num_ctx=1024...")
    keep_alive_settings = ["5m", "10m", "-1"]
    ka_results = {}
    print(f"{'Setting':<8} | {'Load Dur (ms)':<14} | {'Warm TTFT (ms)':<16} | {'Prompt tok/s':<14} | {'Gen tok/s':<12} | {'Ollama RSS':<12} | {'WSL Avail':<12} | {'Swap Used':<12}")
    print("-" * 105)
    for ka in keep_alive_settings:
        mem = get_docker_memory()
        proc = get_ollama_process_info()
        data = send_ollama_request(num_thread=0, prompt=THREADING_PROMPT, keep_alive=ka, timeout_sec=120)
        
        load_dur_ms = round(data.get("load_duration", 0) / 1e6, 2)
        prompt_eval_count = data.get("prompt_eval_count", 0)
        prompt_eval_ms = round(data.get("prompt_eval_duration", 0) / 1e6, 2)
        eval_count = data.get("eval_count", 0)
        eval_ms = round(data.get("eval_duration", 0) / 1e6, 2)
        total_dur_ms = round(data.get("total_duration", 0) / 1e6, 2)
        
        prompt_tok_sec = round((prompt_eval_count / (prompt_eval_ms / 1000.0)), 2) if prompt_eval_ms > 0 else 0.0
        gen_tok_sec = round((eval_count / (eval_ms / 1000.0)), 2) if eval_ms > 0 else 0.0
        warm_ttft_ms = round(load_dur_ms + prompt_eval_ms, 2)

        record = {
            "keep_alive": ka,
            "load_duration_ms": load_dur_ms,
            "prompt_eval_duration_ms": prompt_eval_ms,
            "prompt_tokens_per_sec": prompt_tok_sec,
            "eval_duration_ms": eval_ms,
            "eval_count": eval_count,
            "generation_tokens_per_sec": gen_tok_sec,
            "warm_ttft_ms": warm_ttft_ms,
            "total_duration_ms": total_dur_ms,
            "runner_pid": proc["pid"],
            "ollama_rss_mb": proc["rss_mb"],
            "wsl_avail_mb": mem["wsl_avail_mb"],
            "swap_used_mb": mem["swap_used_mb"]
        }
        ka_results[ka] = record
        print(f"{ka:<8} | {load_dur_ms:<14.2f} | {warm_ttft_ms:<16.2f} | {prompt_tok_sec:<14.2f} | {gen_tok_sec:<12.2f} | {proc['rss_mb']:<10.1f}MB | {mem['wsl_avail_mb']:<10.1f}MB | {mem['swap_used_mb']:<10.1f}MB")

    with open("scratch/controlled_keepalive_results.json", "w", encoding="utf-8") as f:
        json.dump(ka_results, f, indent=2)
    print("\nSaved controlled keep-alive results to scratch/controlled_keepalive_results.json")

if __name__ == "__main__":
    main()

