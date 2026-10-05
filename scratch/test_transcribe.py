import urllib.request
import uuid
import json

for path in ['backend/scratch/test_mms_kannada_target.wav', 'backend/scratch/temp_kannada_voice_test.wav']:
    try:
        with open(path, 'rb') as f:
            data = f.read()
        boundary = uuid.uuid4().hex
        body = bytearray()
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="language"\r\n\r\nkn\r\n'.encode())
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode())
        body.extend(data)
        body.extend(f'\r\n--{boundary}--\r\n'.encode())
        req = urllib.request.Request(
            'http://127.0.0.1/api/v1/tourist/voice/transcribe',
            data=bytes(body),
            headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
        )
        with urllib.request.urlopen(req, timeout=120) as res:
            res_data = json.loads(res.read().decode())
            print(f"{path}: text len={len(res_data.get('text', ''))}")
            print(f"  preview: {res_data.get('text', '')[:120]}")
    except Exception as e:
        print(f"{path} -> ERROR: {e}")
