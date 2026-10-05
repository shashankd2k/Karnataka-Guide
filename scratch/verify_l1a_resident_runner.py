import json
import os
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

BASE_URL = "http://127.0.0.1:80"
AUDIO_PATH = Path("backend/scratch/test_piper_english_target.wav")

def get_wsl_memory():
    try:
        res = subprocess.run(["wsl", "-e", "cat", "/proc/meminfo"], capture_output=True, text=True, timeout=10)
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
            "wsl_mem_avail_mb": round(mem_avail / 1024.0, 1),
            "wsl_swap_used_mb": round(swap_used / 1024.0, 1),
        }
    except Exception as e:
        return {"error": str(e), "wsl_mem_avail_mb": 0.0, "wsl_swap_used_mb": 0.0}

def get_container_process_rss(container_name: str):
    try:
        res = subprocess.run(
            ["docker", "exec", container_name, "ps", "-eo", "pid,comm,rss,vsz,%cpu,%mem"],
            capture_output=True, text=True, timeout=15, check=True
        )
        processes = []
        total_rss = 0
        for line in res.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 6:
                pid, comm, rss, vsz, cpu, mem = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
                rss_kb = int(rss) if rss.isdigit() else 0
                total_rss += rss_kb
                processes.append({
                    "pid": pid,
                    "comm": comm,
                    "rss_kb": rss_kb,
                    "rss_mb": round(rss_kb / 1024.0, 2),
                })
        return {
            "total_rss_mb": round(total_rss / 1024.0, 2),
            "processes": processes,
        }
    except Exception as e:
        return {"error": str(e), "total_rss_mb": 0.0, "processes": []}

def get_ollama_runner_info():
    proc_info = get_container_process_rss("karnatakaguide-ollama-1")
    runner_pid = None
    runner_rss_mb = 0.0
    for p in proc_info.get("processes", []):
        if "llama" in p["comm"].lower() or "runner" in p["comm"].lower():
            runner_pid = p["pid"]
            runner_rss_mb = p["rss_mb"]
            break
    if not runner_pid:
        for p in proc_info.get("processes", []):
            if p["pid"] != "1" and p["rss_mb"] > 100.0:
                runner_pid = p["pid"]
                runner_rss_mb = p["rss_mb"]
                break

    try:
        log_res = subprocess.run(
            ["docker", "logs", "--tail", "25", "karnatakaguide-ollama-1"],
            capture_output=True, text=True, timeout=10
        )
        recent_logs = log_res.stdout + log_res.stderr
        reload_detected = "loading model" in recent_logs.lower() or "new model" in recent_logs.lower()
    except Exception:
        reload_detected = False

    return {
        "runner_pid": runner_pid,
        "runner_rss_mb": runner_rss_mb,
        "server_total_rss_mb": proc_info.get("total_rss_mb", 0.0),
        "recent_reload_detected": reload_detected,
    }

def create_session(lang="en"):
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/sessions",
        data=json.dumps({"language_code": lang}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())["session_uuid"]

def test_text_chat(session_uuid, query):
    t0 = time.perf_counter()
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/chat",
        data=json.dumps({"session_uuid": session_uuid, "message": query}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode())
    dur_ms = (time.perf_counter() - t0) * 1000.0
    return data, dur_ms

def test_stream_chat(session_uuid, query):
    t0 = time.perf_counter()
    first_token_ms = None
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/chat/stream",
        data=json.dumps({"session_uuid": session_uuid, "message": query}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    tokens = []
    current_event = None
    with urllib.request.urlopen(req, timeout=300) as resp:
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue
            if line_str.startswith("event:"):
                current_event = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("data:"):
                raw = line_str.split(":", 1)[1].strip()
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = {}
                if current_event == "token":
                    if first_token_ms is None:
                        first_token_ms = (time.perf_counter() - t0) * 1000.0
                    tokens.append(payload.get("text", ""))
                elif current_event in ("done", "error"):
                    break
    dur_ms = (time.perf_counter() - t0) * 1000.0
    ttft_ms = first_token_ms if first_token_ms is not None else dur_ms
    return {"message": "".join(tokens), "tokens": len(tokens)}, dur_ms, ttft_ms

def test_voice_chat(session_uuid, audio_file):
    with open(audio_file, "rb") as f:
        audio_bytes = f.read()

    boundary = f"----WebKitBoundary{uuid.uuid4().hex}"
    body = bytearray()
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"session_uuid\"\r\n\r\n{session_uuid}\r\n".encode())
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"language\"\r\n\r\nen\r\n".encode())
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"query.wav\"\r\nContent-Type: audio/wav\r\n\r\n".encode())
    body.extend(audio_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    t0 = time.perf_counter()
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/chat/voice",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode())
    dur_ms = (time.perf_counter() - t0) * 1000.0
    return data, dur_ms

def get_last_ollama_log_details():
    try:
        log_res = subprocess.run(
            ["docker", "logs", "--tail", "40", "karnatakaguide-ollama-1"],
            capture_output=True, text=True, timeout=10
        )
        logs = log_res.stdout + log_res.stderr
        # Check slot prompt info
        n_ctx = None
        for line in logs.splitlines():
            if "n_ctx_slot" in line:
                n_ctx = line.strip()
        return {"last_ctx_slot_log": n_ctx}
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=== Level 1-A: num_ctx=1536 Runner Stability & Residency Audit ===")
    
    # 0. Initial state
    init_runner = get_ollama_runner_info()
    init_mem = get_wsl_memory()
    active_pid = init_runner["runner_pid"]
    print(f"Initial Runner PID: {active_pid} (RSS: {init_runner['runner_rss_mb']} MB, Server Total: {init_runner['server_total_rss_mb']} MB)")
    print(f"Initial WSL Mem Available: {init_mem['wsl_mem_avail_mb']} MB, Swap: {init_mem['wsl_swap_used_mb']} MB")
    
    session_id = create_session("en")
    print(f"Created Session UUID: {session_id}")
    results = {}
    
    # 1. Text Chat
    print("\n--- 1. Testing Text Chat (POST /api/v1/tourist/chat) ---")
    txt_data, txt_dur = test_text_chat(session_id, "Who commissioned the Chennakeshava Temple at Belur and when?")
    r1 = get_ollama_runner_info()
    m1 = get_wsl_memory()
    results["text_chat"] = {
        "status": "PASS" if txt_data.get("message") else "FAIL",
        "duration_ms": round(txt_dur, 2),
        "answer_snippet": txt_data.get("message", "")[:80],
        "runner_pid": r1["runner_pid"],
        "pid_preserved": (r1["runner_pid"] == active_pid),
        "ollama_rss_mb": r1["runner_rss_mb"],
        "server_total_rss_mb": r1["server_total_rss_mb"],
        "wsl_avail_mb": m1["wsl_mem_avail_mb"],
        "swap_mb": m1["wsl_swap_used_mb"],
    }
    print(f"Text Chat Complete in {round(txt_dur/1000.0, 2)}s | Runner PID: {r1['runner_pid']} (Preserved: {r1['runner_pid'] == active_pid})")
    
    # 2. Stream Chat
    print("\n--- 2. Testing Stream Chat (POST /api/v1/tourist/chat/stream) ---")
    st_data, st_dur, st_ttft = test_stream_chat(session_id, "What are the major architectural features of the Chennakeshava temple?")
    r2 = get_ollama_runner_info()
    m2 = get_wsl_memory()
    results["stream_chat"] = {
        "status": "PASS" if st_data.get("tokens", 0) > 0 else "FAIL",
        "duration_ms": round(st_dur, 2),
        "ttft_ms": round(st_ttft, 2),
        "tokens_count": st_data.get("tokens", 0),
        "runner_pid": r2["runner_pid"],
        "pid_preserved": (r2["runner_pid"] == active_pid),
        "ollama_rss_mb": r2["runner_rss_mb"],
        "server_total_rss_mb": r2["server_total_rss_mb"],
        "wsl_avail_mb": m2["wsl_mem_avail_mb"],
        "swap_mb": m2["wsl_swap_used_mb"],
    }
    print(f"Stream Chat Complete in {round(st_dur/1000.0, 2)}s (TTFT: {round(st_ttft, 2)} ms) | Runner PID: {r2['runner_pid']} (Preserved: {r2['runner_pid'] == active_pid})")

    # 3. Voice Chat
    print("\n--- 3. Testing Voice Chat (POST /api/v1/tourist/chat/voice) ---")
    if AUDIO_PATH.exists():
        v_data, v_dur = test_voice_chat(session_id, AUDIO_PATH)
        r3 = get_ollama_runner_info()
        m3 = get_wsl_memory()
        results["voice_chat"] = {
            "status": "PASS" if v_data.get("chat", {}).get("message") else "FAIL",
            "duration_ms": round(v_dur, 2),
            "transcript": v_data.get("transcription", {}).get("text", ""),
            "answer_snippet": v_data.get("chat", {}).get("message", "")[:80],
            "runner_pid": r3["runner_pid"],
            "pid_preserved": (r3["runner_pid"] == active_pid),
            "ollama_rss_mb": r3["runner_rss_mb"],
            "server_total_rss_mb": r3["server_total_rss_mb"],
            "wsl_avail_mb": m3["wsl_mem_avail_mb"],
            "swap_mb": m3["wsl_swap_used_mb"],
        }
        print(f"Voice Chat Complete in {round(v_dur/1000.0, 2)}s | Runner PID: {r3['runner_pid']} (Preserved: {r3['runner_pid'] == active_pid})")
    else:
        print(f"Warning: {AUDIO_PATH} not found!")

    # Context confirmation from logs
    log_info = get_last_ollama_log_details()
    
    # Summary Check
    all_pids = [active_pid, results["text_chat"]["runner_pid"], results["stream_chat"]["runner_pid"]]
    if "voice_chat" in results:
        all_pids.append(results["voice_chat"]["runner_pid"])
    single_runner = len(set(all_pids)) == 1
    
    print("\n=======================================================")
    print(f"RUNNER RESIDENCY VERIFICATION: {'SUCCESS' if single_runner else 'FAILED'}")
    print(f"All PIDs matched: {all_pids} -> Constant PID: {active_pid}")
    print(f"Ollama runner slot confirmation: {log_info.get('last_ctx_slot_log')}")
    print("=======================================================")
    
    out_payload = {
        "single_runner_preserved": single_runner,
        "constant_runner_pid": active_pid,
        "log_info": log_info,
        "results": results
    }
    with open("scratch/l1a_residency_results.json", "w") as f:
        json.dump(out_payload, f, indent=2)
    print("Saved to scratch/l1a_residency_results.json")

if __name__ == "__main__":
    main()
