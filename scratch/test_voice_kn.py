import json
import urllib.request
import uuid
from pathlib import Path

base_url = "http://127.0.0.1"
audio_path = Path("backend/scratch/test_mms_kannada_target.wav")

sess_req = urllib.request.Request(
    f"{base_url}/api/v1/tourist/sessions",
    data=json.dumps({"language_code": "kn"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(sess_req, timeout=30) as s_res:
    session_uuid = json.loads(s_res.read().decode())["session_uuid"]

boundary = f"----WebKitBoundary{uuid.uuid4().hex}"
body = bytearray()
body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"session_uuid\"\r\n\r\n{session_uuid}\r\n".encode())
body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"language\"\r\n\r\nkn\r\n".encode())
body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"query.wav\"\r\nContent-Type: audio/wav\r\n\r\n".encode())
with open(audio_path, "rb") as f:
    body.extend(f.read())
body.extend(f"\r\n--{boundary}--\r\n".encode())

chat_voice_req = urllib.request.Request(
    f"{base_url}/api/v1/tourist/chat/voice",
    data=bytes(body),
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST",
)

with urllib.request.urlopen(chat_voice_req, timeout=300) as c_res:
    data = json.loads(c_res.read().decode())
    print("Voice chat successful!")
    print("Message ID:", data.get("chat", {}).get("message_id"))
    msg_id = data.get("chat", {}).get("message_id")

synth_payload = json.dumps({
    "session_uuid": session_uuid,
    "assistant_message_id": msg_id,
}).encode()

synth_req = urllib.request.Request(
    f"{base_url}/api/v1/tourist/voice/synthesize",
    data=synth_payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(synth_req, timeout=300) as s_res:
    audio_bytes = s_res.read()
    print("Synthesis successful! Audio bytes:", len(audio_bytes))
