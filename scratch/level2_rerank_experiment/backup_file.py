import os
import shutil
import hashlib
import datetime
import json

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def backup_file(rel_path):
    src = os.path.abspath(rel_path)
    if not os.path.exists(src):
        print(f"Error: {src} does not exist.")
        return None
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = os.path.abspath(os.path.join("backups", timestamp))
    dest = os.path.join(backup_root, rel_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(src, dest)
    
    src_hash = get_sha256(src)
    dest_hash = get_sha256(dest)
    assert src_hash == dest_hash, "Hash mismatch after copy!"
    
    manifest_path = os.path.join(backup_root, "manifest.json")
    record = {
        "timestamp": timestamp,
        "relative_path": rel_path.replace("\\", "/"),
        "source_absolute": src,
        "backup_absolute": dest,
        "sha256": src_hash
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
        
    print(f"SUCCESS: Backed up {rel_path}")
    print(f"Destination: {dest}")
    print(f"SHA-256: {src_hash}")
    return record

if __name__ == "__main__":
    backup_file("docs/BENCHMARKS.md")
    # Also verify production config file hash
    print("\nVerifying production config hash (read-only):")
    config_hash = get_sha256("backend/app/core/config.py")
    print(f"backend/app/core/config.py SHA-256: {config_hash}")
