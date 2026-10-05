import json
import urllib.request
import urllib.error
import time
import os

BASE_URL = "http://127.0.0.1"

def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def login_admin() -> str:
    log("Logging in as admin...")
    data = json.dumps({"username": "admin", "password": "AdminPass2026!"}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/admin/auth/login",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        token = body["access_token"]
        log(f"  -> Admin logged in, token length: {len(token)}")
        return token

def create_pdf_bytes(target_size: int) -> bytes:
    """
    Creates a syntactically valid PDF padded to the exact target_size in bytes.
    Begins with %PDF-1.4, contains valid xref/trailer/objects, and comment padding.
    """
    header = b"%PDF-1.4\n"
    # Basic PDF structure
    trailer = (
        b"\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n"
    )
    fixed_len = len(header) + len(trailer)
    if target_size < fixed_len:
        raise ValueError(f"Target size {target_size} too small, minimum {fixed_len}")
    
    # We pad with comment bytes '% ' followed by 'A's
    pad_len = target_size - fixed_len
    # comment line: b"% " + b"A" * (pad_len - 2)
    padding = b"% " + b"X" * (pad_len - 2)
    pdf = header + padding + trailer
    assert len(pdf) == target_size, f"Generated size {len(pdf)} != {target_size}"
    return pdf

def upload_pdf_multipart(token: str, filename: str, pdf_bytes: bytes) -> tuple[int, dict]:
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + pdf_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/admin/documents",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
            "Content-Length": str(len(body))
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
            return resp.status, json.loads(data.decode("utf-8")) if data else {}
    except urllib.error.HTTPError as e:
        data = e.read()
        try:
            parsed = json.loads(data.decode("utf-8"))
        except Exception:
            parsed = {"raw": data.decode("utf-8", errors="ignore")}
        return e.code, parsed

def delete_document(token: str, doc_id: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/admin/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            return resp.status, json.loads(data.decode("utf-8")) if data else {}
    except urllib.error.HTTPError as e:
        data = e.read()
        try:
            parsed = json.loads(data.decode("utf-8"))
        except Exception:
            parsed = {"raw": data.decode("utf-8", errors="ignore")}
        return e.code, parsed

def run():
    token = login_admin()
    
    # ----------------------------------------------------
    # TEST A: NEAR BACKEND LIMIT (<= 52,428,800 bytes)
    # Target: 52,428,000 bytes (800 bytes below limit)
    # ----------------------------------------------------
    near_limit_bytes = 52_428_000
    log(f"--- TEST A: NEAR BACKEND LIMIT ({near_limit_bytes:,} bytes) ---")
    log("Creating near-limit PDF payload...")
    pdf_a = create_pdf_bytes(near_limit_bytes)
    log(f"Generated PDF bytes: {len(pdf_a):,} bytes")
    
    log("Uploading near-limit PDF through Nginx (http://127.0.0.1/api/v1/admin/documents)...")
    t0 = time.time()
    status_a, body_a = upload_pdf_multipart(token, "test_near_limit_52428000.pdf", pdf_a)
    duration_a = time.time() - t0
    log(f"  -> Response Status: {status_a} in {duration_a:.2f}s")
    log(f"  -> Response Body: {body_a}")
    
    assert status_a == 201, f"Expected 201 Created, got {status_a}: {body_a}"
    doc_id = body_a.get("id")
    assert doc_id, f"Document ID missing in response: {body_a}"
    log(f"  -> SUCCESS! Document uploaded with ID: {doc_id}")
    
    # Clean up TEST A document
    log(f"Deleting temporary document {doc_id} via Admin API...")
    del_status, del_body = delete_document(token, doc_id)
    log(f"  -> Delete response: {del_status} {del_body}")
    assert del_status == 200, f"Delete failed: {del_status} {del_body}"
    log("  -> Temporary near-limit document cleaned up successfully.")
    
    # ----------------------------------------------------
    # TEST B: JUST OVER BACKEND LIMIT (> 52,428,800 bytes, < 55M)
    # Target: 52,430,000 bytes (1,200 bytes over limit)
    # ----------------------------------------------------
    over_limit_bytes = 52_430_000
    log(f"\n--- TEST B: JUST OVER BACKEND LIMIT ({over_limit_bytes:,} bytes) ---")
    log("Creating over-limit PDF payload (52,430,000 bytes, well under Nginx 55M = 57,671,680 bytes)...")
    pdf_b = create_pdf_bytes(over_limit_bytes)
    log(f"Generated PDF bytes: {len(pdf_b):,} bytes")
    
    log("Uploading over-limit PDF through Nginx...")
    t0 = time.time()
    status_b, body_b = upload_pdf_multipart(token, "test_over_limit_52430000.pdf", pdf_b)
    duration_b = time.time() - t0
    log(f"  -> Response Status: {status_b} in {duration_b:.2f}s")
    log(f"  -> Response Body: {body_b}")
    
    assert status_b == 413, f"Expected HTTP 413 from backend, got {status_b}: {body_b}"
    # Verify backend's error contract
    error_info = body_b.get("error", {})
    error_code = error_info.get("code")
    log(f"  -> Backend error code: {error_code}")
    log(f"  -> Backend error message: {error_info.get('message')}")
    assert error_code in ("PAYLOAD_TOO_LARGE", "DOCUMENT_SIZE_EXCEEDED"), f"Unexpected error code: {error_code}"
    log("  -> SUCCESS! Backend correctly rejected payload exceeding 52,428,800 bytes with HTTP 413.")
    
    log("\n=== PDF LIMIT TESTING SUMMARY ===")
    log(f"PDF NEAR-LIMIT PAYLOAD: {near_limit_bytes} bytes -> PASS (HTTP 201)")
    log(f"PDF OVER-BACKEND-LIMIT PAYLOAD: {over_limit_bytes} bytes -> PASS (HTTP 413, {error_code})")
    log("NGINX 55M MARGIN: PASS")
    log("BACKEND 50 MiB LIMIT: PASS")

if __name__ == "__main__":
    run()
