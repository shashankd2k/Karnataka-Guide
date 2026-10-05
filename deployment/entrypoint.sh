#!/bin/sh
set -e

echo "=== Starting Karnataka Tourist Guide Backend ==="

# 1. Wait for MySQL to become reachable
echo "Waiting for MySQL database at ${DB_HOST:-mysql}:${DB_PORT:-3306}..."
python3 - <<'EOF'
import os
import socket
import sys
import time

host = os.environ.get("DB_HOST", "mysql")
port = int(os.environ.get("DB_PORT", "3306"))
timeout = 60
start = time.time()

while time.time() - start < timeout:
    try:
        with socket.create_connection((host, port), timeout=2.0):
            print(f"Database reachable at {host}:{port}")
            sys.exit(0)
    except OSError:
        time.sleep(1.0)

print(f"ERROR: Timed out waiting for database at {host}:{port}", file=sys.stderr)
sys.exit(1)
EOF

# 2. Execute Alembic migrations to head
echo "Applying database migrations (alembic upgrade head)..."
alembic upgrade head

# 3. Explicit and idempotent Super Admin bootstrap
echo "Running Super Admin bootstrap..."
python3 -m app.infrastructure.db.bootstrap_admin || true

# 4. Start Uvicorn single-worker application
echo "Starting Uvicorn server on 0.0.0.0:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 65
