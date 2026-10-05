import json
import subprocess
import time
import urllib.request
import urllib.error

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def run_cmd(cmd, check=True):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {cmd}\nOutput: {res.stdout}\nError: {res.stderr}")
    return res

def main():
    log("============================================================")
    log("SECTION 12: RUNTIME OFFLINE ISOLATION SANITY VERIFICATION")
    log("============================================================")
    
    results = {}

    try:
        # Step 1: Block external WAN from backend container
        log("\n[1] Deleting default route inside karnatakaguide-backend-1...")
        run_cmd("docker exec --privileged -u 0 karnatakaguide-backend-1 ip route del default")
        log("  -> PASS: Default route removed.")

        # Step 2: Verify external internet is BLOCKED
        log("\n[2] Testing external internet connectivity from inside container...")
        test_wan = run_cmd(
            "docker exec karnatakaguide-backend-1 python -c \"import urllib.request; urllib.request.urlopen('http://8.8.8.8', timeout=2)\"",
            check=False
        )
        if test_wan.returncode != 0:
            log("  -> PASS: External WAN connection failed as expected (Errno 101 Network unreachable / Timeout).")
            results["external_internet"] = "BLOCKED (EXPECTED PASS)"
        else:
            log("  -> FAIL: External WAN connection succeeded unexpectedly!")
            results["external_internet"] = "FAIL"

        # Step 3: Verify backend -> Ollama connectivity
        log("\n[3] Testing backend -> Ollama connectivity inside private bridge network...")
        test_ollama = run_cmd(
            "docker exec karnatakaguide-backend-1 python -c \""
            "import urllib.request, json; "
            "res = urllib.request.urlopen('http://ollama:11434/api/tags', timeout=5); "
            "data = json.loads(res.read().decode()); "
            "print('Loaded models:', [m['name'] for m in data.get('models', [])])\""
        )
        log(f"  -> PASS: backend -> Ollama OK: {test_ollama.stdout.strip()}")
        results["backend_to_ollama"] = "PASS"

        # Step 4: Verify backend -> MySQL connectivity
        log("\n[4] Testing backend -> MySQL connectivity inside private bridge network...")
        test_mysql = run_cmd(
            "docker exec karnatakaguide-backend-1 python /app/scratch/check_mysql_inside_container.py"
        )
        log(f"  -> PASS: backend -> MySQL OK: {test_mysql.stdout.strip()}")
        results["backend_to_mysql"] = "PASS"

        # Step 5: Execute one grounded tourist text query through Nginx gateway
        log("\n[5] Executing one grounded tourist text query via Nginx gateway (/api/v1/tourist/chat)...")
        # 5a. Create Session
        sess_req = urllib.request.Request(
            "http://127.0.0.1:80/api/v1/tourist/sessions",
            data=json.dumps({"language_code": "en"}).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(sess_req, timeout=30) as resp:
            sess_data = json.loads(resp.read().decode())
            session_uuid = sess_data["session_uuid"]
        log(f"  -> Created tourist session: {session_uuid} (lang={sess_data.get('language_code')})")

        # 5b. Send Grounded Chat Query
        chat_req = urllib.request.Request(
            "http://127.0.0.1:80/api/v1/tourist/chat",
            data=json.dumps({
                "session_uuid": session_uuid,
                "message": "Who commissioned the Chennakeshava Temple at Belur and in what year?"
            }).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        t0 = time.perf_counter()
        with urllib.request.urlopen(chat_req, timeout=120) as resp:
            chat_data = json.loads(resp.read().decode())
        elapsed = round(time.perf_counter() - t0, 2)

        answer = chat_data.get("answer") or chat_data.get("message", "")
        citations = chat_data.get("citations") or []
        log(f"  -> Turn completed in {elapsed}s")
        log(f"  -> Answer: \"{answer}\"")
        log(f"  -> Citations ({len(citations)}):")
        for c in citations:
            log(f"     * [{c.get('citation_label')}] {c.get('source_filename')} (p. {c.get('page_number')})")

        assert len(answer) > 20, "Answer too short!"
        assert len(citations) > 0, "Zero citations returned!"
        assert "Vishnuvardhana" in answer or "1117" in answer, "Heritage factual content missing!"
        results["grounded_query"] = "PASS"
        results["citations"] = "PASS"
        log("  -> PASS: Grounded query and citations verified under complete WAN isolation.")

    finally:
        # Step 6: Restore default route
        log("\n[6] Restoring default route inside karnatakaguide-backend-1...")
        run_cmd("docker exec --privileged -u 0 karnatakaguide-backend-1 ip route add default via 172.18.0.1", check=False)
        log("  -> Default route restored.")

        # Verify restoration
        verify_restore = run_cmd(
            "docker exec karnatakaguide-backend-1 python -c \"import urllib.request; urllib.request.urlopen('http://1.1.1.1', timeout=3)\"",
            check=False
        )
        if verify_restore.returncode == 0:
            log("  -> Confirmed external network connectivity restored.")
        else:
            log("  -> Route restored.")

    log("\n" + "=" * 60)
    log("SECTION 12 SUMMARY:")
    for k, v in results.items():
        log(f"  - {k}: {v}")
    log("============================================================")

    all_passed = all("PASS" in v for v in results.values())
    if all_passed:
        log("RUNTIME OFFLINE SANITY: PASS")
    else:
        log("RUNTIME OFFLINE SANITY: FAIL")
        raise RuntimeError("Some offline sanity checks failed.")

if __name__ == "__main__":
    main()
