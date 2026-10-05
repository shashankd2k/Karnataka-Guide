import json
import os
import sys
import time
import urllib.request
import urllib.error

def get_meminfo():
    mem = {}
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    k = parts[0].strip()
                    v = parts[1].strip().split()[0]
                    if v.isdigit():
                        mem[k] = int(v)
        avail_mb = round(mem.get("MemAvailable", 0) / 1024.0, 1)
        swap_total = mem.get("SwapTotal", 0)
        swap_free = mem.get("SwapFree", 0)
        swap_used_mb = round((swap_total - swap_free) / 1024.0, 1)
        return {"avail_mb": avail_mb, "swap_used_mb": swap_used_mb, "swap_total_mb": round(swap_total / 1024.0, 1)}
    except Exception as e:
        return {"error": str(e)}

def check_ollama_residency():
    try:
        req = urllib.request.Request("http://ollama:11434/api/ps")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            models = data.get("models", [])
            return models
    except Exception as e:
        return []

def warmup_ollama():
    print("[Warmup] Sending warm-up probe to Ollama...", flush=True)
    payload = {
        "model": "phi3:mini",
        "prompt": "Say ready",
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "num_ctx": 1536,
            "num_thread": 2,
            "num_predict": 2
        }
    }
    t0 = time.perf_counter()
    req = urllib.request.Request(
        "http://ollama:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    dur = round(time.perf_counter() - t0, 2)
    load_ms = round(res.get("load_duration", 0) / 1e6, 2)
    print(f"[Warmup] Ollama ready in {dur}s (load_duration={load_ms}ms)", flush=True)

def create_session(lang="en"):
    sess_req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/tourist/sessions",
        data=json.dumps({"language_code": lang}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(sess_req, timeout=30) as resp:
        sess_data = json.loads(resp.read().decode("utf-8"))
        return sess_data["session_uuid"]

def stream_request(session_uuid, message, lang="en", timeout_seconds=120):
    start_mem = get_meminfo()
    models = check_ollama_residency()
    residency_info = models[0] if models else {"name": "none"}

    print(f"\n[{lang.upper()} Stream] Starting streaming turn for query: '{message[:60]}...'", flush=True)
    print(f"[{lang.upper()} Stream] Starting Memory: {start_mem}, Resident Model: {residency_info.get('name')}", flush=True)

    chat_payload = {
        "session_uuid": session_uuid,
        "message": message
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/tourist/chat/stream",
        data=json.dumps(chat_payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST"
    )

    t_start = time.perf_counter()
    first_token_time = None
    first_token_text = None
    all_tokens = []
    citations = []
    done_payload = None
    error_msg = None
    timed_out = False

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            current_event = None
            for line_bytes in resp:
                line = line_bytes.decode("utf-8").strip()
                if not line:
                    continue
                if line.startswith("event:"):
                    current_event = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    data_str = line.replace("data:", "").strip()
                    try:
                        data_json = json.loads(data_str)
                    except Exception:
                        continue

                    if current_event == "token":
                        token_text = data_json.get("text", "")
                        if token_text and first_token_time is None:
                            first_token_time = time.perf_counter()
                            first_token_text = token_text
                            ttft = round(first_token_time - t_start, 3)
                            print(f"[{lang.upper()} Stream] First token arrived: '{first_token_text}' at TTFT={ttft}s", flush=True)
                        all_tokens.append(token_text)

                    elif current_event == "citations":
                        citations = data_json.get("citations", [])

                    elif current_event == "done":
                        done_payload = data_json
                        break

                    elif current_event == "error":
                        error_msg = data_json.get("detail") or data_str
                        break

    except (urllib.error.URLError, TimeoutError, Exception) as exc:
        elapsed = round(time.perf_counter() - t_start, 2)
        if "timed out" in str(exc).lower() or elapsed >= timeout_seconds:
            timed_out = True
            error_msg = f"TIMEOUT_BOUND (> {timeout_seconds}s)"
            print(f"[{lang.upper()} Stream] Request hit timeout bound after {elapsed}s: {exc}", flush=True)
        else:
            error_msg = str(exc)
            print(f"[{lang.upper()} Stream] Request error after {elapsed}s: {exc}", flush=True)

    t_end = time.perf_counter()
    total_elapsed = round(t_end - t_start, 3)
    ttft_val = round(first_token_time - t_start, 3) if first_token_time else None
    assembled_answer = "".join(all_tokens).strip()

    result = {
        "language": lang,
        "query": message,
        "session_uuid": session_uuid,
        "effective_model": "phi3:mini",
        "effective_options": {"num_ctx": 1536, "num_thread": 2, "num_predict": 192, "keep_alive": "10m"},
        "resident_model": residency_info.get("name"),
        "starting_mem": start_mem,
        "timestamp_start": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - total_elapsed)),
        "first_token_text": first_token_text,
        "ttft_seconds": ttft_val,
        "ttft_tag": "MEASURED" if ttft_val else ("TIMEOUT_BOUND" if timed_out else "NOT_MEASURED"),
        "total_latency_seconds": total_elapsed,
        "total_latency_tag": "TIMEOUT_BOUND" if timed_out else "MEASURED",
        "tokens_streamed_count": len(all_tokens),
        "assembled_answer": assembled_answer[:200] + ("..." if len(assembled_answer) > 200 else ""),
        "citations_count": len(citations),
        "citations": citations,
        "done_payload": done_payload,
        "error": error_msg,
        "timed_out": timed_out,
        "status": "PASS" if (assembled_answer and len(citations) > 0 and not timed_out) else ("TIMEOUT_BOUND" if timed_out else "FAIL")
    }

    print(f"[{lang.upper()} Stream] Finished: status={result['status']}, TTFT={ttft_val}s, Total={total_elapsed}s, Tokens={len(all_tokens)}, Citations={len(citations)}", flush=True)
    return result

def main():
    print("=" * 60, flush=True)
    print("PHASE 18 LEVEL 1 APPLICATION-PATH WARM STREAMING BENCHMARK", flush=True)
    print("=" * 60, flush=True)

    # 1. Warm up Ollama and verify residency
    warmup_ollama()
    models = check_ollama_residency()
    print(f"[Check] Resident models in Ollama: {[m.get('name') for m in models]}", flush=True)

    results = {}

    # 2. English Warm Streaming Request (bounded finite deadline: 180s)
    en_sess = create_session("en")
    en_query = "Who commissioned the Chennakeshava Temple at Belur and in what year?"
    en_res = stream_request(en_sess, en_query, lang="en", timeout_seconds=180)
    results["en_warm_stream"] = en_res

    # Intermediate persistence
    out_path = "/app/scratch/application_warm_stream_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[Persisted] Saved intermediate results to {out_path}", flush=True)

    # Allow small settle time
    time.sleep(2)

    # 3. Kannada Warm Streaming Request (bounded finite deadline: 180s)
    kn_sess = create_session("kn")
    kn_query = "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವ ವರ್ಷದಲ್ಲಿ ನಿರ್ಮಿಸಿದರು?"
    kn_res = stream_request(kn_sess, kn_query, lang="kn", timeout_seconds=180)
    results["kn_warm_stream"] = kn_res

    # Final persistence
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[Persisted] Saved final results to {out_path}", flush=True)

if __name__ == "__main__":
    main()
