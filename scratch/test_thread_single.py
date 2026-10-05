import urllib.request, json, time, sys

def query(thread, target_url='http://ollama:11434/api/generate'):
    payload = {
        'model': 'phi3:mini',
        'prompt': 'Who commissioned the Chennakeshava Temple at Belur in 1117 CE?',
        'stream': False,
        'keep_alive': '10m',
        'options': {
            'num_ctx': 1024,
            'num_predict': 32,
            'temperature': 0.1,
        }
    }
    if thread > 0:
        payload['options']['num_thread'] = thread
    
    data = json.dumps(payload).encode()
    req = urllib.request.Request(target_url, data=data, headers={'Content-Type': 'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        res = json.loads(resp.read().decode())
    t1 = time.time()
    load_ms = res.get('load_duration', 0) / 1e6
    peval_cnt = res.get('prompt_eval_count', 0)
    peval_dur_ms = res.get('prompt_eval_duration', 0) / 1e6
    eval_cnt = res.get('eval_count', 0)
    eval_dur_ms = res.get('eval_duration', 0) / 1e6
    peval_tps = (peval_cnt / (peval_dur_ms / 1000.0)) if peval_dur_ms > 0 else 0
    eval_tps = (eval_cnt / (eval_dur_ms / 1000.0)) if eval_dur_ms > 0 else 0
    print(f'Thread {thread}: Total={t1-t0:.2f}s | Load={load_ms:.2f}ms | PEval={peval_dur_ms:.2f}ms ({peval_tps:.2f} tok/s) | Gen={eval_dur_ms:.2f}ms ({eval_tps:.2f} tok/s)')
    return res

if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:11434/api/generate'
    print(f'Testing on {url}:')
    for t in [2, 2, 4, 4]:
        query(t, url)
