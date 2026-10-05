import urllib.request
import json
import time

payload = json.dumps({
    "model": "phi3:mini",
    "prompt": "Hello",
    "keep_alive": "10m",
    "stream": False,
    "options": {
        "num_ctx": 1024,
        "num_predict": 10
    }
}).encode()

req = urllib.request.Request(
    "http://127.0.0.1:11434/api/generate",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)

# Also warm docker ollama via container
print("Sending warm request to Docker Ollama...")
t0 = time.perf_counter()
import subprocess
res = subprocess.run(
    ["docker", "exec", "karnatakaguide-ollama-1", "curl", "-s", "-X", "POST", "http://localhost:11434/api/generate", "-d",
     json.dumps({"model": "phi3:mini", "prompt": "Hi", "keep_alive": "10m", "stream": False, "options": {"num_ctx": 1024, "num_predict": 5}})],
    capture_output=True, text=True, timeout=180
)
t1 = time.perf_counter()
print(f"Docker Ollama warmed in {t1-t0:.2f}s!")
subprocess.run(["docker", "exec", "karnatakaguide-ollama-1", "ollama", "ps"])
