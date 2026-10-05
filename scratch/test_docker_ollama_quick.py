import urllib.request, json, time

t0 = time.time()
payload = {
    "model": "phi3:mini",
    "prompt": "Who commissioned Belur Chennakeshava Temple?",
    "stream": False,
    "options": {"num_predict": 10}
}
req = urllib.request.Request("http://ollama:11434/api/generate", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=60) as resp:
    res = json.loads(resp.read().decode())
t1 = time.time()

load_ms = res.get("load_duration", 0) / 1e6
peval_ms = res.get("prompt_eval_duration", 0) / 1e6
eval_ms = res.get("eval_duration", 0) / 1e6
eval_cnt = res.get("eval_count", 0)
eval_tps = eval_cnt / (eval_ms / 1000.0) if eval_ms > 0 else 0

print(f"Total time: {t1-t0:.2f}s | Load: {load_ms:.1f}ms | PEval: {peval_ms:.1f}ms | Gen: {eval_tps:.2f} tok/s | Eval count: {eval_cnt}")
