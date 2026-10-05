import subprocess
import json

p = {
    'model': 'phi3:mini',
    'prompt': 'Say OK',
    'stream': False,
    'options': {
        'num_ctx': 1024,
        'num_predict': 5
    }
}
res = subprocess.run(
    ['docker', 'exec', 'karnatakaguide-backend-1', 'curl', '-s', '-X', 'POST',
     'http://ollama:11434/api/generate', '-H', 'Content-Type: application/json',
     '-d', json.dumps(p)],
    capture_output=True, text=True
)
print('CODE:', res.returncode)
print('STDOUT:', res.stdout[:300])
print('STDERR:', res.stderr[:300])
