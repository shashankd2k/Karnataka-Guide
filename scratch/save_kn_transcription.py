import json
import urllib.request
import uuid

boundary = uuid.uuid4().hex
body = bytearray()
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="language"\r\n\r\nkn\r\n'.encode())
body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode())
with open('backend/scratch/test_mms_kannada_query.wav', 'rb') as f:
    body.extend(f.read())
body.extend(f'\r\n--{boundary}--\r\n'.encode())

req = urllib.request.Request(
    'http://127.0.0.1/api/v1/tourist/voice/transcribe',
    data=bytes(body),
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
with urllib.request.urlopen(req, timeout=60) as r:
    res = json.loads(r.read().decode())

with open('scratch/kn_transcription.txt', 'w', encoding='utf-8') as f:
    f.write(res.get('text', ''))

print('Saved text, length:', len(res.get('text', '')))
print('Success! First 20 chars unicode escapes:', res.get('text', '')[:20].encode('unicode_escape').decode())
