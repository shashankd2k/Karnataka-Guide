import urllib.request, json, time, statistics, sys

THREADING_PROMPT = "Describe the Hoysala architecture of Belur in three concise sentences."

def query_ollama(thread, keep_alive="10m", prompt=THREADING_PROMPT, num_predict=64):
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
        "keep_alive": keep_alive,
        "options": options
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=180) as resp:
        res = json.loads(resp.read().decode())
    t1 = time.perf_counter()
    res["client_total_ms"] = (t1 - t0) * 1000
    return res

def main():
    settings = [4, 2, 0, 3, 1]
    all_results = {}
    print("=== CONTROLLED THREADING BENCHMARK (NATIVE WINDOWS OLLAMA) ===")
    
    for t in settings:
        label = "default/auto" if t == 0 else f"{t}_threads"
        print(f"\n--- Testing {label} ---")
        print(f"Warming {label}...", end=" ", flush=True)
        w = query_ollama(t)
        load_ms = w.get("load_duration", 0) / 1e6
        print(f"Done (load: {load_ms:.2f} ms)")
        
        runs = []
        for i in range(1, 4):
            print(f"  Run {i}/3 ({label})...", end=" ", flush=True)
            res = query_ollama(t)
            load_dur_ms = round(res.get("load_duration", 0) / 1e6, 2)
            peval_cnt = res.get("prompt_eval_count", 0)
            peval_dur_ms = round(res.get("prompt_eval_duration", 0) / 1e6, 2)
            eval_cnt = res.get("eval_count", 0)
            eval_dur_ms = round(res.get("eval_duration", 0) / 1e6, 2)
            total_dur_ms = round(res.get("total_duration", 0) / 1e6, 2)
            client_total_ms = round(res.get("client_total_ms", 0), 2)
            
            peval_tps = round((peval_cnt / (peval_dur_ms / 1000.0)), 2) if peval_dur_ms > 0 else 0.0
            eval_tps = round((eval_cnt / (eval_dur_ms / 1000.0)), 2) if eval_dur_ms > 0 else 0.0
            warm_ttft_ms = round(load_dur_ms + peval_dur_ms, 2)
            
            run_data = {
                "run_idx": i,
                "num_thread": t,
                "label": label,
                "load_duration_ms": load_dur_ms,
                "prompt_eval_duration_ms": peval_dur_ms,
                "prompt_eval_count": peval_cnt,
                "prompt_tokens_per_sec": peval_tps,
                "eval_duration_ms": eval_dur_ms,
                "eval_count": eval_cnt,
                "generation_tokens_per_sec": eval_tps,
                "warm_ttft_ms": warm_ttft_ms,
                "total_duration_ms": total_dur_ms,
                "client_total_ms": client_total_ms,
            }
            runs.append(run_data)
            print(f"TTFT={warm_ttft_ms}ms, PromptEval={peval_tps}tok/s, GenSpeed={eval_tps}tok/s, LoadDur={load_dur_ms}ms")
            
        all_results[label] = {
            "num_thread": t,
            "median_warm_ttft_ms": round(statistics.median([r["warm_ttft_ms"] for r in runs]), 2),
            "median_prompt_tokens_per_sec": round(statistics.median([r["prompt_tokens_per_sec"] for r in runs]), 2),
            "median_gen_tokens_per_sec": round(statistics.median([r["generation_tokens_per_sec"] for r in runs]), 2),
            "median_total_duration_ms": round(statistics.median([r["total_duration_ms"] for r in runs]), 2),
            "median_load_duration_ms": round(statistics.median([r["load_duration_ms"] for r in runs]), 2),
            "runs": runs,
        }

    print("\n" + "="*90)
    print("CONTROLLED THREADING SUMMARY (MEDIAN WARM PERFORMANCE)")
    print("="*90)
    for t in [0, 1, 2, 3, 4]:
        label = "default/auto" if t == 0 else f"{t}_threads"
        s = all_results[label]
        print(f"{label:<16} | TTFT: {s['median_warm_ttft_ms']:8.2f} ms | PEval: {s['median_prompt_tokens_per_sec']:6.2f} tok/s | Gen: {s['median_gen_tokens_per_sec']:6.2f} tok/s | Total: {s['median_total_duration_ms']:8.2f} ms")

    with open("scratch/controlled_threading_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "="*90)
    print("CONTROLLED KEEP-ALIVE CONSISTENCY CHECK (5m vs 10m vs -1)")
    print("="*90)
    ka_results = {}
    for ka in ["5m", "10m", "-1"]:
        print(f"Testing keep_alive={ka}...", end=" ", flush=True)
        res = query_ollama(thread=0, keep_alive=ka, prompt=THREADING_PROMPT, num_predict=64)
        load_dur_ms = round(res.get("load_duration", 0) / 1e6, 2)
        peval_cnt = res.get("prompt_eval_count", 0)
        peval_dur_ms = round(res.get("prompt_eval_duration", 0) / 1e6, 2)
        eval_cnt = res.get("eval_count", 0)
        eval_dur_ms = round(res.get("eval_duration", 0) / 1e6, 2)
        total_dur_ms = round(res.get("total_duration", 0) / 1e6, 2)
        peval_tps = round((peval_cnt / (peval_dur_ms / 1000.0)), 2) if peval_dur_ms > 0 else 0.0
        eval_tps = round((eval_cnt / (eval_dur_ms / 1000.0)), 2) if eval_dur_ms > 0 else 0.0
        warm_ttft_ms = round(load_dur_ms + peval_dur_ms, 2)
        ka_results[ka] = {
            "keep_alive": ka,
            "load_duration_ms": load_dur_ms,
            "prompt_eval_duration_ms": peval_dur_ms,
            "prompt_tokens_per_sec": peval_tps,
            "eval_duration_ms": eval_dur_ms,
            "eval_count": eval_cnt,
            "generation_tokens_per_sec": eval_tps,
            "warm_ttft_ms": warm_ttft_ms,
            "total_duration_ms": total_dur_ms,
        }
        print(f"Warm TTFT={warm_ttft_ms}ms, PromptEval={peval_tps}tok/s, GenSpeed={eval_tps}tok/s, LoadDur={load_dur_ms}ms")

    with open("scratch/controlled_keepalive_results.json", "w", encoding="utf-8") as f:
        json.dump(ka_results, f, indent=2)
    print("Benchmark complete & saved!")

if __name__ == "__main__":
    main()
