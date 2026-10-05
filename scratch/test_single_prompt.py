import urllib.request, json, time

t0 = time.time()
payload = {
    "model": "phi3:mini",
    "prompt": "=== EVIDENCE START ===\n[1] (Source: Belur_Halebidu_Hoysala_Guide.pdf, Page 2)\nBelur Chennakeshava Temple was commissioned by King Vishnuvardhana in 1117 CE to celebrate his victory over the Cholas at Talakadu.\n=== EVIDENCE END ===\n\nTourist Question: Who commissioned the Chennakeshava Temple at Belur and when?",
    "system": "You are the official AI Smart Tourist Guide for Karnataka, India. Keep responses concise (2-4 sentences), factual, and cite sources as [1].",
    "stream": False,
    "options": {"num_ctx": 1536, "num_predict": 128, "num_thread": 2, "temperature": 0.1}
}
req = urllib.request.Request("http://ollama:11434/api/generate", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=300) as resp:
    res = json.loads(resp.read().decode())
t1 = time.time()

eval_cnt = res.get("eval_count", 0)
peval_cnt = res.get("prompt_eval_count", 0)
peval_ms = res.get("prompt_eval_duration", 0) / 1e6
eval_ms = res.get("eval_duration", 0) / 1e6
load_ms = res.get("load_duration", 0) / 1e6

print(f"Wall: {t1-t0:.2f}s | Load: {load_ms:.1f}ms | PEval: {peval_ms:.1f}ms ({peval_cnt} tok) | Gen: {eval_ms:.1f}ms ({eval_cnt} tok) | Gen speed: {eval_cnt/(eval_ms/1000.0) if eval_ms>0 else 0:.2f} tok/s")
print("Response:", res.get("response", "").strip())
