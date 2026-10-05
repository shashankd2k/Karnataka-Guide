import io
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.request
import uuid
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_URL = "http://127.0.0.1"
RESULTS_FILE = "scratch/level1_benchmark_results.json"
ENGLISH_WAV_PATH = Path("backend/scratch/test_piper_english_target.wav")
KANNADA_WAV_PATH = Path("backend/scratch/test_mms_kannada_target.wav")

def now_ns() -> int:
    return time.perf_counter_ns()

def ns_to_ms(ns: int) -> float:
    return ns / 1_000_000.0

def compute_stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "median": 0.0, "p90": 0.0, "p95": 0.0, "min": 0.0, "max": 0.0, "std": 0.0, "count": 0}
    sorted_v = sorted(values)
    n = len(sorted_v)
    mean = statistics.mean(sorted_v)
    median = statistics.median(sorted_v)
    min_v = sorted_v[0]
    max_v = sorted_v[-1]
    stdev = statistics.stdev(sorted_v) if n > 1 else 0.0

    def percentile(p):
        if n == 1:
            return sorted_v[0]
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_v[int(k)]
        return sorted_v[int(f)] * (c - k) + sorted_v[int(c)] * (k - f)

    return {
        "mean": round(mean, 2),
        "median": round(median, 2),
        "p90": round(percentile(0.90), 2),
        "p95": round(percentile(0.95), 2),
        "min": round(min_v, 2),
        "max": round(max_v, 2),
        "std": round(stdev, 2),
        "count": n,
    }

def get_docker_telemetry() -> Dict[str, Any]:
    try:
        res = subprocess.run(
            ["docker", "exec", "karnatakaguide-backend-1", "cat", "/proc/meminfo"],
            capture_output=True, text=True, timeout=15, check=True
        )
        meminfo = {}
        for line in res.stdout.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                parts = v.strip().split()
                meminfo[k.strip()] = int(parts[0]) if parts and parts[0].isdigit() else v.strip()

        mem_avail = meminfo.get("MemAvailable", 0)
        swap_total = meminfo.get("SwapTotal", 0)
        swap_free = meminfo.get("SwapFree", 0)
        swap_used = swap_total - swap_free

        # Ollama container stats
        res_ps = subprocess.run(
            ["docker", "exec", "karnatakaguide-ollama-1", "ps", "-eo", "pid,comm,rss"],
            capture_output=True, text=True, timeout=15
        )
        ollama_rss_kb = 0
        for line in res_ps.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 3 and parts[2].isdigit():
                ollama_rss_kb += int(parts[2])

        return {
            "wsl_avail_mem_mb": round(mem_avail / 1024.0, 1),
            "wsl_swap_used_mb": round(swap_used / 1024.0, 1),
            "ollama_rss_mb": round(ollama_rss_kb / 1024.0, 1),
        }
    except Exception as e:
        return {"error": str(e), "wsl_avail_mem_mb": 0.0, "wsl_swap_used_mb": 0.0, "ollama_rss_mb": 0.0}

def save_atomic(filepath: str, data: dict):
    tmp_path = filepath + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, filepath)

def load_results() -> dict:
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def unload_ollama_model():
    """Unload model from Ollama runner memory to force clean cold load."""
    payload = json.dumps({"model": "phi3:mini", "keep_alive": 0}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception:
        # Fallback to docker exec inside ollama container
        try:
            subprocess.run([
                "docker", "exec", "karnatakaguide-backend-1",
                "curl", "-s", "-X", "POST", "http://ollama:11434/api/generate",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({"model": "phi3:mini", "keep_alive": 0})
            ], timeout=10)
        except Exception:
            pass
    time.sleep(2)

def run_text_chat_stream(query: str, language: str = "en", session_uuid: Optional[str] = None) -> dict:
    if not session_uuid:
        sess_req = urllib.request.Request(
            f"{BASE_URL}/api/v1/tourist/sessions",
            data=json.dumps({"language_code": language}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(sess_req, timeout=120) as s_res:
            s_data = json.loads(s_res.read().decode())
            session_uuid = s_data["session_uuid"]

    payload = json.dumps({"session_uuid": session_uuid, "message": query}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/chat/stream",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t_start = now_ns()
    ttft_ms = 0.0
    tokens = []
    citations = []
    first_token_ts = None
    current_event = None

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for line in resp:
                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue
                if line_str.startswith("event:"):
                    current_event = line_str.split(":", 1)[1].strip()
                elif line_str.startswith("data:"):
                    raw_data = line_str.split(":", 1)[1].strip()
                    try:
                        data = json.loads(raw_data)
                    except Exception:
                        data = {}

                    if current_event == "token":
                        if first_token_ts is None:
                            first_token_ts = now_ns()
                            ttft_ms = ns_to_ms(first_token_ts - t_start)
                        tokens.append(data.get("text", ""))
                    elif current_event == "citations":
                        citations = data.get("citations", [])
                    elif current_event == "done":
                        break
                    elif current_event == "error":
                        break
    except Exception as exc:
        telem = get_docker_telemetry()
        t_end = now_ns()
        total_latency_ms = ns_to_ms(t_end - t_start)
        return {
            "status": "TIMEOUT_BOUND" if total_latency_ms >= 290000.0 else "FAIL",
            "error": str(exc),
            "ttft_ms": round(ttft_ms or total_latency_ms, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "tokens_generated": len(tokens),
            "tokens_per_second": 0.0,
            "citations_count": len(citations),
            "answer_snippet": "TIMEOUT_BOUND (Exceeded 300s Gateway Timeout)",
            "telemetry": telem,
            "session_uuid": session_uuid
        }

    t_end = now_ns()
    total_latency_ms = ns_to_ms(t_end - t_start)
    answer = "".join(tokens)
    gen_duration_sec = (total_latency_ms - ttft_ms) / 1000.0 if total_latency_ms > ttft_ms else total_latency_ms / 1000.0
    tps = round(len(tokens) / gen_duration_sec, 2) if gen_duration_sec > 0 else 0.0
    telem = get_docker_telemetry()

    return {
        "status": "PASS" if len(tokens) > 0 else "FAIL",
        "ttft_ms": round(ttft_ms, 2),
        "total_latency_ms": round(total_latency_ms, 2),
        "tokens_generated": len(tokens),
        "tokens_per_second": tps,
        "citations_count": len(citations),
        "answer_snippet": answer[:120],
        "telemetry": telem,
        "session_uuid": session_uuid
    }

def run_voice_turn(audio_path: Path, language: str = "en") -> dict:
    if not audio_path.exists():
        return {"status": "FAIL", "error": f"Audio file not found: {audio_path}"}

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    # Create session
    sess_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/sessions",
        data=json.dumps({"language_code": language}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(sess_req, timeout=30) as s_res:
        s_data = json.loads(s_res.read().decode())
        session_uuid = s_data["session_uuid"]

    # Step 1: Upload voice chat
    audio_upload_start_ts = now_ns()
    boundary = f"----WebKitBoundary{uuid.uuid4().hex}"
    body = bytearray()
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"session_uuid\"\r\n\r\n{session_uuid}\r\n".encode())
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"language\"\r\n\r\n{language}\r\n".encode())
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"query.wav\"\r\nContent-Type: audio/wav\r\n\r\n".encode())
    body.extend(audio_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    chat_voice_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/chat/voice",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(chat_voice_req, timeout=300) as c_res:
            voice_chat_raw = c_res.read().decode()
            voice_chat_response_recv_ts = now_ns()
    except Exception as exc:
        return {
            "status": "TIMEOUT_BOUND",
            "error": str(exc),
            "chat_voice_turn_ms": 300000.0,
            "tts_synthesis_ms": 0.0,
            "server_time_to_audio_available_ms": 300000.0,
            "note": "Exceeded 300s Gateway Timeout"
        }

    voice_chat_data = json.loads(voice_chat_raw)
    trans_obj = voice_chat_data.get("transcription", {})
    transcript = trans_obj.get("text", "") if isinstance(trans_obj, dict) else str(trans_obj)
    message_id = voice_chat_data.get("chat", {}).get("message_id", "")
    answer_text = voice_chat_data.get("chat", {}).get("answer", "") or voice_chat_data.get("chat", {}).get("message", "")

    chat_voice_turn_ms = ns_to_ms(voice_chat_response_recv_ts - audio_upload_start_ts)

    # Step 2: Synthesis
    tts_request_start_ts = now_ns()
    synth_payload = json.dumps({
        "session_uuid": session_uuid,
        "assistant_message_id": message_id,
    }).encode()

    synth_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/voice/synthesize",
        data=synth_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(synth_req, timeout=300) as s_res:
            out_audio_bytes = s_res.read()
            tts_response_complete_ts = now_ns()
    except Exception as exc:
        return {
            "status": "TIMEOUT_BOUND",
            "error": str(exc),
            "chat_voice_turn_ms": round(chat_voice_turn_ms, 2),
            "tts_synthesis_ms": 300000.0,
            "server_time_to_audio_available_ms": 300000.0,
            "note": "TTS Synthesis timed out"
        }

    tts_synthesis_ms = ns_to_ms(tts_response_complete_ts - tts_request_start_ts)
    server_time_avail_ms = ns_to_ms(tts_response_complete_ts - audio_upload_start_ts)

    audio_dur = 0.0
    try:
        with wave.open(io.BytesIO(out_audio_bytes), "rb") as wf:
            sample_rate = wf.getframerate()
            nframes = wf.getnframes()
            audio_dur = round(nframes / float(sample_rate), 2)
    except Exception:
        pass

    telem = get_docker_telemetry()
    return {
        "status": "PASS",
        "transcript": transcript,
        "answer_snippet": answer_text[:120],
        "chat_voice_turn_ms": round(chat_voice_turn_ms, 2),
        "tts_synthesis_ms": round(tts_synthesis_ms, 2),
        "server_time_to_audio_available_ms": round(server_time_avail_ms, 2),
        "audio_bytes_len": len(out_audio_bytes),
        "audio_duration_seconds": audio_dur,
        "telemetry": telem,
    }

def main():
    print("=" * 70, flush=True)
    print("PHASE 18 LEVEL 1 COMBINED BENCHMARK (TEXT & VOICE)", flush=True)
    print("=" * 70, flush=True)

    results = load_results()
    total_steps = 18  # 1 EN cold, 5 EN warm, 1 KN cold, 5 KN warm, 1 EN voice cold, 3 EN voice warm, 1 KN voice cold, 1 KN voice warm

    # 1. English Text Cold
    if "en_text_cold" not in results:
        print("\n[Step 1/18] Running English Text Cold...", flush=True)
        unload_ollama_model()
        res = run_text_chat_stream("Who commissioned the Chennakeshava Temple at Belur?", language="en")
        results["en_text_cold"] = res
        save_atomic(RESULTS_FILE, results)
        print(f"COMPLETED 1 / {total_steps} | EN Text Cold: TTFT={res['ttft_ms']}ms, Total={res['total_latency_ms']}ms, TPS={res['tokens_per_second']}", flush=True)
    else:
        print(f"Skipping already completed en_text_cold", flush=True)

    # 2. English Text Warm (5 runs)
    if "en_text_warm_runs" not in results:
        results["en_text_warm_runs"] = []

    en_warm_runs = results["en_text_warm_runs"]
    en_sess_id = en_warm_runs[0].get("session_uuid") if en_warm_runs else None
    for i in range(len(en_warm_runs), 5):
        step_idx = 2 + i
        print(f"\n[Step {step_idx}/{total_steps}] Running English Text Warm Run {i+1}...", flush=True)
        res = run_text_chat_stream("Who commissioned the Chennakeshava Temple at Belur?", language="en", session_uuid=en_sess_id)
        if not en_sess_id:
            en_sess_id = res.get("session_uuid")
        en_warm_runs.append(res)
        results["en_text_warm_runs"] = en_warm_runs
        results["en_text_warm_stats"] = {
            "ttft_ms": compute_stats([r["ttft_ms"] for r in en_warm_runs]),
            "total_latency_ms": compute_stats([r["total_latency_ms"] for r in en_warm_runs]),
            "tokens_per_second": compute_stats([r["tokens_per_second"] for r in en_warm_runs]),
        }
        save_atomic(RESULTS_FILE, results)
        print(f"COMPLETED {step_idx} / {total_steps} | EN Text Warm #{i+1}: TTFT={res['ttft_ms']}ms, Total={res['total_latency_ms']}ms, TPS={res['tokens_per_second']}", flush=True)
        time.sleep(1)

    # 3. Kannada Text Cold
    if "kn_text_cold" not in results:
        print("\n[Step 7/18] Running Kannada Text Cold...", flush=True)
        unload_ollama_model()
        res = run_text_chat_stream("ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ನಿರ್ಮಿಸಿದರು?", language="kn")
        results["kn_text_cold"] = res
        save_atomic(RESULTS_FILE, results)
        print(f"COMPLETED 7 / {total_steps} | KN Text Cold: TTFT={res['ttft_ms']}ms, Total={res['total_latency_ms']}ms, TPS={res['tokens_per_second']}", flush=True)
    else:
        print(f"Skipping already completed kn_text_cold", flush=True)

    # 4. Kannada Text Warm (5 runs)
    if "kn_text_warm_runs" not in results:
        results["kn_text_warm_runs"] = []

    kn_warm_runs = results["kn_text_warm_runs"]
    kn_sess_id = kn_warm_runs[0].get("session_uuid") if kn_warm_runs else None
    for i in range(len(kn_warm_runs), 5):
        step_idx = 8 + i
        print(f"\n[Step {step_idx}/{total_steps}] Running Kannada Text Warm Run {i+1}...", flush=True)
        res = run_text_chat_stream("ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ನಿರ್ಮಿಸಿದರು?", language="kn", session_uuid=kn_sess_id)
        if not kn_sess_id:
            kn_sess_id = res.get("session_uuid")
        kn_warm_runs.append(res)
        results["kn_text_warm_runs"] = kn_warm_runs
        results["kn_text_warm_stats"] = {
            "ttft_ms": compute_stats([r["ttft_ms"] for r in kn_warm_runs]),
            "total_latency_ms": compute_stats([r["total_latency_ms"] for r in kn_warm_runs]),
            "tokens_per_second": compute_stats([r["tokens_per_second"] for r in kn_warm_runs]),
        }
        save_atomic(RESULTS_FILE, results)
        print(f"COMPLETED {step_idx} / {total_steps} | KN Text Warm #{i+1}: TTFT={res['ttft_ms']}ms, Total={res['total_latency_ms']}ms, TPS={res['tokens_per_second']}", flush=True)
        time.sleep(1)

    # 5. English Voice Cold
    if "en_voice_cold" not in results:
        print("\n[Step 13/18] Running English Voice Cold...", flush=True)
        unload_ollama_model()
        res = run_voice_turn(ENGLISH_WAV_PATH, language="en")
        results["en_voice_cold"] = res
        save_atomic(RESULTS_FILE, results)
        print(f"COMPLETED 13 / {total_steps} | EN Voice Cold: Turn={res['chat_voice_turn_ms']}ms, TTS={res['tts_synthesis_ms']}ms, ServerAudio={res['server_time_to_audio_available_ms']}ms", flush=True)
    else:
        print(f"Skipping already completed en_voice_cold", flush=True)

    # 6. English Voice Warm (3 runs)
    if "en_voice_warm_runs" not in results:
        results["en_voice_warm_runs"] = []

    en_voice_warm_runs = results["en_voice_warm_runs"]
    for i in range(len(en_voice_warm_runs), 3):
        step_idx = 14 + i
        print(f"\n[Step {step_idx}/{total_steps}] Running English Voice Warm Run {i+1}...", flush=True)
        res = run_voice_turn(ENGLISH_WAV_PATH, language="en")
        en_voice_warm_runs.append(res)
        results["en_voice_warm_runs"] = en_voice_warm_runs
        results["en_voice_warm_stats"] = {
            "chat_voice_turn_ms": compute_stats([r["chat_voice_turn_ms"] for r in en_voice_warm_runs]),
            "tts_synthesis_ms": compute_stats([r["tts_synthesis_ms"] for r in en_voice_warm_runs]),
            "server_time_to_audio_available_ms": compute_stats([r["server_time_to_audio_available_ms"] for r in en_voice_warm_runs]),
        }
        save_atomic(RESULTS_FILE, results)
        print(f"COMPLETED {step_idx} / {total_steps} | EN Voice Warm #{i+1}: Turn={res['chat_voice_turn_ms']}ms, TTS={res['tts_synthesis_ms']}ms, ServerAudio={res['server_time_to_audio_available_ms']}ms", flush=True)
        time.sleep(1)

    # 7. Kannada Voice Cold
    if "kn_voice_cold" not in results:
        print("\n[Step 17/18] Running Kannada Voice Cold...", flush=True)
        unload_ollama_model()
        res = run_voice_turn(KANNADA_WAV_PATH, language="kn")
        results["kn_voice_cold"] = res
        save_atomic(RESULTS_FILE, results)
        print(f"COMPLETED 17 / {total_steps} | KN Voice Cold: Status={res['status']}, ServerAudio={res['server_time_to_audio_available_ms']}ms", flush=True)
    else:
        print(f"Skipping already completed kn_voice_cold", flush=True)

    # 8. Kannada Voice Warm
    if "kn_voice_warm" not in results:
        print("\n[Step 18/18] Running Kannada Voice Warm...", flush=True)
        res = run_voice_turn(KANNADA_WAV_PATH, language="kn")
        results["kn_voice_warm"] = res
        save_atomic(RESULTS_FILE, results)
        print(f"COMPLETED 18 / {total_steps} | KN Voice Warm: Status={res['status']}, ServerAudio={res['server_time_to_audio_available_ms']}ms", flush=True)
    else:
        print(f"Skipping already completed kn_voice_warm", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("PHASE 18 LEVEL 1 COMBINED BENCHMARK COMPLETE", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    main()
