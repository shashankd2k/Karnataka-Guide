import urllib.request
import json
import time
import os
import subprocess
import sys

SAMPLE_SYSTEM = (
    "You are the authoritative AI Tourist Guide for Karnataka, India. "
    "Provide direct, engaging, factual answers grounded exclusively in the provided evidence. "
    "Always cite sources as [1], [2]. If the evidence does not contain the answer, say: "
    "'I do not have verified information in the official heritage documentation.'"
)
SAMPLE_EVIDENCE = (
    "=== EVIDENCE START ===\n"
    "[1] Belur Chennakeshava Temple was commissioned by King Vishnuvardhana in 1117 CE to commemorate "
    "his victory over the Cholas at Talakad. The temple is built from soapstone (chloritic schist) and features "
    "42 exquisite bracket figures depicting celestial nymphs known as Madanikas. The main sanctum is dedicated "
    "to Lord Vijayanarayana, an aspect of Vishnu. "
    "[2] The complex took over 103 years to complete across three generations of Hoysala rulers. The exterior walls "
    "contain horizontal friezes of charging elephants, ferocious lions, swift cavalry, and intricate floral scrolls.\n"
    "=== EVIDENCE END ==="
)
FULL_PROD_PROMPT = f"{SAMPLE_EVIDENCE}\n\nUser Question: Who commissioned Belur Chennakeshava Temple and why?"

def get_meminfo():
    mem = {}
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    k = parts[0].strip()
                    v = parts[1].strip().split()[0]
                    mem[k] = int(v)
        avail_mb = round(mem.get("MemAvailable", 0) / 1024.0, 2)
        swap_total = mem.get("SwapTotal", 0)
        swap_free = mem.get("SwapFree", 0)
        swap_used_mb = round((swap_total - swap_free) / 1024.0, 2)
        return avail_mb, swap_used_mb
    except Exception:
        return 0.0, 0.0

def query_ollama(thread, prompt=FULL_PROD_PROMPT, system=SAMPLE_SYSTEM, num_predict=64, timeout=240):
    options = {
        "num_ctx": 1024,
        "num_predict": num_predict,
        "temperature": 0.1,
    }
    if thread > 0:
        options["num_thread"] = thread

    payload = {
        "model": "phi3:mini",
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": options
    }
    if system:
        payload["system"] = system

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "http://ollama:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        res = json.loads(resp.read().decode())
    t1 = time.perf_counter()
    res["client_wall_ms"] = (t1 - t0) * 1000
    return res

def run_docker_thread_benchmark():
    settings = [0, 2, 4]  # 0 is default/auto
    results = {}

    print("=" * 80, flush=True)
    print("CONTROLLED DOCKER OLLAMA THREAD BENCHMARK (default/auto, 2, 4)", flush=True)
    print("=" * 80, flush=True)

    for t in settings:
        label = "default/auto" if t == 0 else f"{t}_threads"
        print(f"\n[Setting: {label}] Warming runner and verifying residency...", flush=True)
        
        # 1. Warmup with tiny prompt ("Say OK") to load model without prompt eval timeout
        w_avail, w_swap = get_meminfo()
        t_warm_start = time.time()
        warmup_res = query_ollama(t, prompt="Say OK", system=None, num_predict=2, timeout=240)
        t_warm_dur = round(time.time() - t_warm_start, 2)
        warmup_load_ms = round(warmup_res.get("load_duration", 0) / 1e6, 2)
        print(f"  Warmup completed in {t_warm_dur}s. Runner load_duration: {warmup_load_ms:.2f} ms", flush=True)

        # 2. Measured warm iterations (at least 3) using FULL_PROD_PROMPT
        runs = []
        for i in range(1, 4):
            avail_before, swap_before = get_meminfo()
            res = query_ollama(t, prompt=FULL_PROD_PROMPT, system=SAMPLE_SYSTEM, num_predict=64, timeout=240)
            avail_after, swap_after = get_meminfo()

            load_ms = round(res.get("load_duration", 0) / 1e6, 2)
            peval_dur_ms = round(res.get("prompt_eval_duration", 0) / 1e6, 2)
            peval_cnt = res.get("prompt_eval_count", 0)
            eval_dur_ms = round(res.get("eval_duration", 0) / 1e6, 2)
            eval_cnt = res.get("eval_count", 0)
            total_dur_ms = round(res.get("total_duration", 0) / 1e6, 2)

            peval_tps = round((peval_cnt / (peval_dur_ms / 1000.0)), 2) if peval_dur_ms > 0 else 0.0
            eval_tps = round((eval_cnt / (eval_dur_ms / 1000.0)), 2) if eval_dur_ms > 0 else 0.0

            run_data = {
                "run_idx": i,
                "load_duration_ms": load_ms,
                "prompt_eval_duration_ms": peval_dur_ms,
                "prompt_eval_count": peval_cnt,
                "prompt_tokens_per_sec": peval_tps,
                "eval_duration_ms": eval_dur_ms,
                "eval_count": eval_cnt,
                "generation_tokens_per_sec": eval_tps,
                "total_duration_ms": total_dur_ms,
                "client_wall_ms": round(res["client_wall_ms"], 2),
                "wsl2_avail_mb": avail_after,
                "wsl2_swap_mb": swap_after,
            }
            runs.append(run_data)
            print(f"  Run {i}/3: PEval: {peval_tps:6.2f} tok/s ({peval_dur_ms:.1f}ms) | Gen: {eval_tps:5.2f} tok/s ({eval_dur_ms:.1f}ms) | Load: {load_ms:.1f}ms | Total: {total_dur_ms:.1f}ms | Swap: {swap_after} MB", flush=True)

        # Medians
        import statistics
        median_peval_tps = statistics.median([r["prompt_tokens_per_sec"] for r in runs])
        median_eval_tps = statistics.median([r["generation_tokens_per_sec"] for r in runs])
        median_peval_dur = statistics.median([r["prompt_eval_duration_ms"] for r in runs])
        median_eval_dur = statistics.median([r["eval_duration_ms"] for r in runs])
        median_total = statistics.median([r["total_duration_ms"] for r in runs])
        median_load = statistics.median([r["load_duration_ms"] for r in runs])
        median_avail = statistics.median([r["wsl2_avail_mb"] for r in runs])
        median_swap = statistics.median([r["wsl2_swap_mb"] for r in runs])

        results[label] = {
            "num_thread": t,
            "warmup_load_duration_ms": warmup_load_ms,
            "median_load_duration_ms": median_load,
            "median_prompt_eval_duration_ms": median_peval_dur,
            "median_prompt_tokens_per_sec": median_peval_tps,
            "median_eval_duration_ms": median_eval_dur,
            "median_gen_tokens_per_sec": median_eval_tps,
            "median_total_duration_ms": median_total,
            "median_wsl2_avail_mb": median_avail,
            "median_wsl2_swap_mb": median_swap,
            "runs": runs
        }

    print("\n" + "=" * 80, flush=True)
    print("DOCKER THREAD BENCHMARK SUMMARY (MEDIANS)", flush=True)
    print("=" * 80, flush=True)
    for label, s in results.items():
        print(f"{label:<14} | PEval: {s['median_prompt_tokens_per_sec']:6.2f} tok/s | Gen: {s['median_gen_tokens_per_sec']:5.2f} tok/s | Total: {s['median_total_duration_ms']:8.2f} ms | Swap: {s['median_wsl2_swap_mb']:6.1f} MB", flush=True)

    with open("/tmp/docker_thread_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved /tmp/docker_thread_results.json", flush=True)

if __name__ == "__main__":
    run_docker_thread_benchmark()
