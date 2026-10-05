import urllib.request, json, time

print("Warming Docker Ollama with tiny prompt 'Say OK'...")
t0 = time.time()
payload = {
    "model": "phi3:mini",
    "prompt": "Say OK",
    "stream": False,
    "keep_alive": "10m",
    "options": {"num_ctx": 1536, "num_thread": 2, "num_predict": 2}
}
req = urllib.request.Request("http://ollama:11434/api/generate", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=600) as resp:
    res = json.loads(resp.read().decode())
t1 = time.time()

print(f"Preload successful! Elapsed: {t1-t0:.2f}s | Load duration: {res.get('load_duration', 0)/1e6:.1f}ms | Response: {res.get('response', '').strip()}")
