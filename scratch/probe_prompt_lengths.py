import urllib.request
import json
import time

lengths = [50, 200, 400, 600, 800]
text_chunk = "Karnataka has magnificent Hoysala temples in Belur and Halebidu with intricate stone carvings. "

for target_len in lengths:
    # construct prompt of approximate length
    repeat_count = max(1, target_len // 12)
    prompt = text_chunk * repeat_count + "\nQuestion: Briefly summarize in 10 words."
    
    payload = {
        "model": "phi3:mini",
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "num_ctx": 1536,
            "num_thread": 2,
            "num_predict": 15,
            "temperature": 0.1,
            "top_p": 0.9,
        }
    }
    req = urllib.request.Request(
        "http://ollama:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            res = json.loads(resp.read().decode("utf-8"))
        dt = time.time() - t0
        pe_count = res.get("prompt_eval_count", 0)
        pe_dur = res.get("prompt_eval_duration", 0) / 1e9
        eval_count = res.get("eval_count", 0)
        eval_dur = res.get("eval_duration", 0) / 1e9
        pe_speed = pe_count / pe_dur if pe_dur > 0 else 0
        gen_speed = eval_count / eval_dur if eval_dur > 0 else 0
        print(f"Target {target_len} tok -> Prompt: {pe_count} tok in {pe_dur:.2f}s ({pe_speed:.1f} tok/s) | Eval: {eval_count} tok in {eval_dur:.2f}s ({gen_speed:.2f} tok/s) | Total: {dt:.2f}s", flush=True)
    except Exception as e:
        print(f"Target {target_len} tok -> FAILED: {e} after {time.time()-t0:.2f}s", flush=True)
