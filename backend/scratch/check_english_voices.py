import json
import urllib.request

req = urllib.request.Request(
    'https://huggingface.co/rhasspy/piper-voices/raw/main/voices.json',
    headers={'User-Agent': 'Mozilla/5.0'}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

check_keys = [
    'en_US-lessac-medium',
    'en_US-lessac-low',
    'en_US-amy-medium',
    'en_US-danny-low',
    'en_GB-alan-medium',
    'en_US-hfc_female-medium',
    'en_US-ryan-medium',
]

for k in check_keys:
    if k in data:
        v = data[k]
        files = {fname: round(finfo['size_bytes'] / (1024 * 1024), 2) for fname, finfo in v.get('files', {}).items()}
        print(f"{k}: name={v.get('name')} quality={v.get('quality')} files_MB={files}")
