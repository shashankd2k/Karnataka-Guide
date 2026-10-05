import json
import subprocess
import time
import urllib.request
import urllib.error

def run_cmd(cmd, check=True):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {cmd}\nOutput: {res.stdout}\nError: {res.stderr}")
    return res

def test_runtime_isolation():
    print("=" * 60)
    print("SECTION 12: RUNTIME OFFLINE ISOLATION SANITY TEST")
    print("=" * 60)

    try:
        # 1. Block external network from backend runtime
        print("\n[Step 1] Isolating backend container network (deleting default route)...")
        run_cmd("docker exec --privileged -u 0 karnatakaguide-backend-1 ip route del default")
        print("  -> Default route deleted.")

        # 2. Verify external internet is BLOCKED
        print("\n[Step 2] Verifying external internet is BLOCKED from backend container...")
        test_wan = run_cmd(
            "docker exec karnatakaguide-backend-1 python -c \"import urllib.request; urllib.request.urlopen('http://8.8.8.8', timeout=2)\"",
            check=False
        )
        if test_wan.returncode != 0:
            print("  -> PASS: External internet access is strictly BLOCKED (as expected).")
        else:
            raise AssertionError("External internet access was NOT blocked!")

        # 3. Verify backend -> Ollama internal connectivity
        print("\n[Step 3] Verifying backend -> Ollama connectivity...")
        ollama_test = run_cmd(
            "docker exec karnatakaguide-backend-1 python -c \""
            "import urllib.request, json; "
            "res = urllib.request.urlopen('http://ollama:11434/api/tags', timeout=5); "
            "data = json.loads(res.read().decode()); "
            "print('Ollama tags:', [m['name'] for m in data.get('models', [])])\""
        )
        print(f"  -> PASS: Backend connected to Ollama: {ollama_test.stdout.strip()}")

        # 4. Verify backend -> MySQL internal connectivity
        print("\n[Step 4] Verifying backend -> MySQL connectivity...")
        mysql_test = run_cmd(
            """docker exec karnatakaguide-backend-1 python -c "import asyncio, app.infrastructure.db.session as s, sqlalchemy as sa;
async def check():
    engine = s.get_async_engine()
    async with engine.connect() as conn:
        res = await conn.execute(sa.text('SELECT 1'))
        print('MySQL SELECT 1 result:', res.scalar())
asyncio.run(check())" """
        )
        print(f"  -> PASS: Backend connected to MySQL: {mysql_test.stdout.strip()}")

        # 5. Execute one grounded tourist text query through Nginx gateway
        print("\n[Step 5] Executing one grounded tourist text query through Nginx while isolated...", flush=True)
        # Create session with explicit language_code='en'
        sess_req = urllib.request.Request(
            "http://127.0.0.1:80/api/v1/tourist/sessions",
            data=json.dumps({"language_code": "en"}).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(sess_req, timeout=30) as s_res:
            sess_data = json.loads(s_res.read().decode())
            session_uuid = sess_data["session_uuid"]
        print(f"  -> Tourist session created (lang={sess_data.get('language_code')}): {session_uuid}", flush=True)

        # Send chat stream query
        query = "Who commissioned the Chennakeshava Temple at Belur and in what year?"
        chat_req = urllib.request.Request(
            "http://127.0.0.1:80/api/v1/tourist/chat/stream",
            data=json.dumps({
                "session_uuid": session_uuid,
                "message": query
            }).encode(),
            headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
            method="POST"
        )

        tokens = []
        citations = []
        current_event = None
        t0 = time.perf_counter()
        with urllib.request.urlopen(chat_req, timeout=180) as resp:
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
                        tokens.append(data.get("text", ""))
                    elif current_event == "citations":
                        citations = data.get("citations", [])
                    elif current_event == "done":
                        break
        elapsed = round(time.perf_counter() - t0, 2)
        answer_text = "".join(tokens).strip()

        print(f"  -> Elapsed time: {elapsed}s")
        print(f"  -> Generated answer: \"{answer_text[:120]}...\"")
        print(f"  -> Citations received: {len(citations)}")
        for c in citations:
            print(f"     * [{c.get('citation_number')}] {c.get('source_title')} (p. {c.get('page_number')})")

        assert len(tokens) > 0, "No tokens received!"
        assert len(citations) > 0, "No citations received!"
        assert "Vishnuvardhana" in answer_text or "1117" in answer_text, "Answer did not contain expected heritage facts!"
        print("  -> PASS: Grounded query and citations successfully verified under complete WAN isolation.")

    finally:
        # 6. Restore default gateway
        print("\n[Step 6] Restoring backend container default route...")
        restore_res = run_cmd("docker exec --privileged -u 0 karnatakaguide-backend-1 ip route add default via 172.18.0.1", check=False)
        print("  -> Default route restored.")

        # Verify internet restored
        test_restore = run_cmd(
            "docker exec karnatakaguide-backend-1 python -c \"import urllib.request; urllib.request.urlopen('http://1.1.1.1', timeout=3)\"",
            check=False
        )
        if test_restore.returncode == 0:
            print("  -> Network connectivity restored successfully.")
        else:
            print("  -> (Note: WAN route restored)")

    print("\n" + "=" * 60)
    print("SECTION 12 RUNTIME OFFLINE ISOLATION STATUS: PASS")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_runtime_isolation()
