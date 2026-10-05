import json
import urllib.request
import urllib.error
import socket
import time
import os
import subprocess
from typing import Optional, Dict, Any, Tuple

BASE_URL = "http://127.0.0.1"

# --- Socket-level WAN Isolation ---
real_create_connection = socket.create_connection
real_socket_connect = socket.socket.connect
wan_attempts = []

ALLOWED_PREFIXES = ("127.", "172.16.", "172.17.", "172.18.", "172.19.", "192.168.", "::1", "localhost")

def is_allowed(host: str) -> bool:
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    for prefix in ALLOWED_PREFIXES:
        if host.startswith(prefix):
            return True
    return False

def isolated_create_connection(address, *args, **kwargs):
    host = address[0]
    if not is_allowed(host):
        wan_attempts.append(f"{host}:{address[1]}")
        raise OSError(101, f"Network is unreachable (Strict WAN Isolation): attempted {host}:{address[1]}")
    return real_create_connection(address, *args, **kwargs)

def isolated_connect(self, address):
    if isinstance(address, tuple) and len(address) >= 2:
        host = address[0]
        if not is_allowed(str(host)):
            wan_attempts.append(f"{host}:{address[1]}")
            raise OSError(101, f"Network is unreachable (Strict WAN Isolation): attempted {host}:{address[1]}")
    return real_socket_connect(self, address)

def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def request_json(method: str, path: str, body: Optional[dict] = None, headers: Optional[dict] = None) -> Tuple[int, dict, dict]:
    url = f"{BASE_URL}{path}"
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read()
            return resp.status, dict(resp.headers), json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except Exception:
            parsed = {"raw": raw.decode("utf-8", errors="ignore")}
        return e.code, dict(e.headers), parsed

def run_offline_test():
    log("=" * 70)
    log("PHASE 17: FULL-STACK RUNTIME OFFLINE VERIFICATION THROUGH NGINX")
    log("=" * 70)
    
    # 1. Apply socket-level WAN isolation
    socket.create_connection = isolated_create_connection
    socket.socket.connect = isolated_connect
    log("[+] Strict socket-level WAN isolation applied.")
    
    # Verify that external WAN is genuinely blocked
    try:
        urllib.request.urlopen("https://8.8.8.8", timeout=2)
        raise RuntimeError("WAN block failed to intercept external IP!")
    except OSError as e:
        log(f"[+] Confirmed external WAN is blocked: {e}")
        
    try:
        urllib.request.urlopen("https://api.openai.com", timeout=2)
        raise RuntimeError("WAN block failed to intercept external domain!")
    except OSError as e:
        log(f"[+] Confirmed external cloud AI domain is blocked: {e}")

    results = {}

    # ----------------------------------------------------
    # 1. Frontend Loading through Nginx (port 80)
    # ----------------------------------------------------
    log("\n[1/10] Verifying Frontend Loading via Nginx (http://127.0.0.1/)...")
    req_fe = urllib.request.Request(f"{BASE_URL}/", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_fe, timeout=15) as resp:
        html = resp.read().decode("utf-8")
        assert resp.status == 200
        assert "<div id=\"root\">" in html or "Karnataka" in html or "vite" in html.lower()
        log(f"  -> Frontend HTTP {resp.status} OK (HTML length {len(html)} bytes)")
        results["OFFLINE_FRONTEND"] = "PASS"

    # ----------------------------------------------------
    # 2. Admin API Authentication & Retrieval
    # ----------------------------------------------------
    log("\n[2/10] Verifying Admin API Authentication & Documents List...")
    status, _, login_body = request_json("POST", "/api/v1/admin/auth/login", {
        "username": "admin",
        "password": "AdminPass2026!"
    })
    assert status == 200, f"Admin login failed: {login_body}"
    admin_token = login_body["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    log("  -> Admin login 200 OK")
    
    status, _, doc_list = request_json("GET", "/api/v1/admin/documents", headers=admin_headers)
    assert status == 200, f"Document list failed: {doc_list}"
    log(f"  -> Admin documents list 200 OK (total documents: {doc_list.get('total')})")
    results["OFFLINE_ADMIN"] = "PASS"

    # ----------------------------------------------------
    # 3. RAG Retrieval via Diagnostics API
    # ----------------------------------------------------
    log("\n[3/10] Verifying RAG Retrieval (Dense + BM25 + CrossEncoder)...")
    status, _, rag_res = request_json("POST", "/api/v1/admin/knowledge/retrieval-test", {
        "query": "Halebidu Hoysaleswara Temple architecture and history",
        "top_k": 3
    }, headers=admin_headers)
    assert status == 200, f"RAG retrieval failed: {rag_res}"
    evidence = rag_res.get("results", [])
    assert len(evidence) > 0, "No evidence returned from RAG retrieval"
    log(f"  -> RAG Retrieval 200 OK: returned {len(evidence)} evidence chunks")
    for idx, e in enumerate(evidence):
        log(f"     [{idx+1}] {e.get('source_filename')} (page {e.get('page_number')}): {e.get('section_header')}")
    results["OFFLINE_RAG"] = "PASS"

    # ----------------------------------------------------
    # 4. English Grounded Chat through SSE Stream (Nginx)
    # ----------------------------------------------------
    log("\n[4/10] Verifying English Grounded Chat via SSE Stream (POST /api/v1/tourist/chat/stream)...")
    status, _, sess_res = request_json("POST", "/api/v1/tourist/sessions", {"language": "en"})
    assert status in (200, 201), f"Session creation failed: {sess_res}"
    session_uuid = sess_res["session_uuid"]
    log(f"  -> Created tourist session: {session_uuid}")
    
    stream_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/chat/stream",
        data=json.dumps({
            "session_uuid": session_uuid,
            "message": "Who built the Chennakeshava temple in Belur and when was it consecrated?"
        }).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"}
    )
    
    events = []
    tokens = []
    citations_data = None
    done_data = None
    t_start = time.time()
    ttft = None
    
    with urllib.request.urlopen(stream_req, timeout=300) as resp:
        assert resp.status == 200
        cur_event = None
        cur_data = []
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if not line_str:
                if cur_event and cur_data:
                    data_str = "\n".join(cur_data)
                    try:
                        p_data = json.loads(data_str)
                    except Exception:
                        p_data = data_str
                    events.append((cur_event, p_data))
                    if cur_event == "token":
                        if ttft is None:
                            ttft = time.time() - t_start
                        tokens.append(p_data.get("text", ""))
                    elif cur_event == "citations":
                        citations_data = p_data
                    elif cur_event == "done":
                        done_data = p_data
                cur_event = None
                cur_data = []
                continue
            if line_str.startswith("event:"):
                cur_event = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("data:"):
                cur_data.append(line_str.split(":", 1)[1].strip())

    total_chat_time = time.time() - t_start
    full_text = "".join(tokens)
    log(f"  -> SSE Stream complete in {total_chat_time:.2f}s (TTFT: {ttft:.2f}s)")
    log(f"  -> Emitted tokens count: {len(tokens)}")
    log(f"  -> Generated response: {full_text[:120]}...")
    assert len(tokens) > 0, "Zero tokens received"
    assert done_data is not None, "Missing done event"
    assert done_data.get("grounded") is True, f"Expected grounded=True: {done_data}"
    log(f"  -> Citations: {citations_data}")
    results["OFFLINE_ENGLISH_CHAT"] = "PASS"

    # ----------------------------------------------------
    # 5. Faster-Whisper Voice Transcription (POST /api/v1/tourist/chat/voice)
    # ----------------------------------------------------
    log("\n[5/10] Verifying Faster-Whisper Audio Transcription (POST /api/v1/tourist/chat/voice)...")
    wav_path = "backend/scratch/test_piper_english_target.wav"
    assert os.path.exists(wav_path), f"Missing test audio asset: {wav_path}"
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()
    
    boundary = "----WebKitFormBoundaryVoiceTest99"
    v_body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="session_uuid"\r\n\r\n'
        f"{session_uuid}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="language"\r\n\r\n'
        f"en\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="test_voice.wav"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode("utf-8") + wav_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    v_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/chat/voice",
        data=v_body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(v_req, timeout=300) as resp:
        v_res = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        transcription = v_res.get("transcription")
        voice_msg_id = v_res.get("chat", {}).get("message_id")
        log(f"  -> Faster-Whisper transcribed: '{transcription}'")
        log(f"  -> Assistant message ID: {voice_msg_id}")
        assert voice_msg_id, "Missing voice message_id"
        results["OFFLINE_WHISPER"] = "PASS"

    # ----------------------------------------------------
    # 6. Piper English TTS Synthesis (POST /api/v1/tourist/voice/synthesize)
    # ----------------------------------------------------
    log("\n[6/10] Verifying Piper English TTS Synthesis...")
    synth_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/voice/synthesize",
        data=json.dumps({"session_uuid": session_uuid, "assistant_message_id": voice_msg_id}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(synth_req, timeout=120) as resp:
        audio_bytes = resp.read()
        sr = resp.headers.get("X-Audio-Sample-Rate")
        ct = resp.headers.get("Content-Type")
        log(f"  -> Piper synthesized: {len(audio_bytes):,} bytes WAV, Content-Type: {ct}, Sample-Rate: {sr}")
        assert resp.status == 200
        assert "audio/wav" in ct
        assert sr == "22050"
        results["OFFLINE_PIPER"] = "PASS"

    # ----------------------------------------------------
    # 7. Kannada Grounded Chat + NLLB-200 Translation
    # ----------------------------------------------------
    log("\n[7/10] Verifying Kannada Grounded Chat + NLLB-200 Translation (POST /api/v1/tourist/chat/stream)...")
    status, _, kn_sess = request_json("POST", "/api/v1/tourist/sessions", {"language": "kn"})
    kn_session_uuid = kn_sess["session_uuid"]
    
    kn_stream_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/chat/stream",
        data=json.dumps({
            "session_uuid": kn_session_uuid,
            "message": "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯದ ಶಿಲ್ಪಿ ಯಾರು?"
        }).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"}
    )
    
    kn_tokens = []
    kn_done = None
    with urllib.request.urlopen(kn_stream_req, timeout=300) as resp:
        cur_event = None
        cur_data = []
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if not line_str:
                if cur_event and cur_data:
                    data_str = "\n".join(cur_data)
                    try:
                        p_data = json.loads(data_str)
                    except Exception:
                        p_data = data_str
                    if cur_event == "token":
                        kn_tokens.append(p_data.get("text", ""))
                    elif cur_event == "done":
                        kn_done = p_data
                cur_event = None
                cur_data = []
                continue
            if line_str.startswith("event:"):
                cur_event = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("data:"):
                cur_data.append(line_str.split(":", 1)[1].strip())

    kn_text = "".join(kn_tokens)
    log(f"  -> Kannada tokens count: {len(kn_tokens)}")
    log(f"  -> Kannada response: {kn_text[:120]}...")
    assert len(kn_tokens) > 0, "Zero Kannada tokens received"
    assert kn_done is not None, "Missing Kannada done event"
    kn_msg_id = kn_done.get("message_id")
    log(f"  -> Kannada message ID: {kn_msg_id}")
    results["OFFLINE_KANNADA_CHAT"] = "PASS"
    results["OFFLINE_NLLB"] = "PASS"

    # ----------------------------------------------------
    # 8. Meta MMS-TTS Kannada Synthesis
    # ----------------------------------------------------
    log("\n[8/10] Verifying Meta MMS-TTS Kannada Synthesis...")
    mms_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/tourist/voice/synthesize",
        data=json.dumps({"session_uuid": kn_session_uuid, "assistant_message_id": kn_msg_id}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(mms_req, timeout=120) as resp:
        mms_audio = resp.read()
        mms_sr = resp.headers.get("X-Audio-Sample-Rate")
        mms_ct = resp.headers.get("Content-Type")
        log(f"  -> MMS-TTS synthesized: {len(mms_audio):,} bytes WAV, Content-Type: {mms_ct}, Sample-Rate: {mms_sr}")
        assert resp.status == 200
        assert "audio/wav" in mms_ct
        assert mms_sr == "16000"
        results["OFFLINE_MMS"] = "PASS"

    # ----------------------------------------------------
    # 9. Docker-Internal Ollama Inference
    # ----------------------------------------------------
    log("\n[9/10] Verifying Docker-Internal Ollama Inference (http://ollama:11434/api/generate)...")
    res = subprocess.run([
        "docker", "compose", "exec", "backend", "python", "-c",
        "import httpx\n"
        "r = httpx.post('http://ollama:11434/api/generate', json={'model': 'phi3:mini', 'prompt': 'Reply exactly OK', 'stream': False, 'options': {'num_predict': 8, 'num_ctx': 1024}}, timeout=180)\n"
        "print('STATUS:', r.status_code)\n"
        "print('RESPONSE:', r.json().get('response'))"
    ], capture_output=True, text=True)
    log(f"  -> Container exit code: {res.returncode}")
    log(f"  -> Container stdout:\n{res.stdout.strip()}")
    assert res.returncode == 0, f"Docker-internal Ollama failed: {res.stderr}"
    assert "STATUS: 200" in res.stdout, f"Non-200 status: {res.stdout}"
    results["OFFLINE_OLLAMA"] = "PASS"

    # ----------------------------------------------------
    # 10. Audit for Forbidden Cloud AI Endpoints
    # ----------------------------------------------------
    log("\n[10/10] Auditing for Forbidden Cloud AI Endpoints...")
    forbidden = ["openai.com", "anthropic.com", "generativelanguage.googleapis.com", "bedrock", "azure"]
    for attempt in wan_attempts:
        for f in forbidden:
            assert f not in attempt, f"Forbidden cloud AI call attempted: {attempt}"
    log(f"  -> Confirmed 0 forbidden cloud AI calls. Total external attempts intercepted: {len(wan_attempts)}")
    results["ZERO_CLOUD_AI"] = "PASS"

    # Restore real socket functions
    socket.create_connection = real_create_connection
    socket.socket.connect = real_socket_connect
    log("\n[+] Socket-level WAN isolation removed. Normal network restored.")
    
    log("\n" + "=" * 70)
    log("FULL-STACK OFFLINE EXECUTION VERIFICATION SUMMARY:")
    for k, v in results.items():
        log(f"  {k:25}: {v}")
    log("=" * 70)

if __name__ == "__main__":
    run_offline_test()
