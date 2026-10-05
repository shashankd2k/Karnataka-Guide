import urllib.request
import json
import time

payload = {
    "model": "phi3:mini",
    "prompt": "Say hello in one word",
    "stream": False,
    "options": {
        "num_ctx": 1536,
        "num_thread": 2,
        "num_predict": 10
    }
}
t0 = time.time()
req = urllib.request.Request(
    "http://ollama:11434/api/generate",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=60) as resp:
    res = json.loads(resp.read().decode("utf-8"))

dt = time.time() - t0
eval_count = res.get("eval_count", 0)
eval_dur = res.get("eval_duration", 0) / 1e9
pe_count = res.get("prompt_eval_count", 0)
pe_dur = res.get("prompt_eval_duration", 0) / 1e9
print(f"Total time: {dt:.2f}s")
print(f"Prompt tokens: {pe_count}, Prompt time: {pe_dur:.2f}s ({pe_count/pe_dur if pe_dur else 0:.2f} tok/s)")
print(f"Eval tokens: {eval_count}, Eval time: {eval_dur:.2f}s ({eval_count/eval_dur if eval_dur else 0:.2f} tok/s)")
print(f"Response: {res.get('response')}")
