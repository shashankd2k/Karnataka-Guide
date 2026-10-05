# Karnataka Tourist Guide Platform — Deployment Guide

This guide provides the complete operational manual for deploying the Karnataka Tourist Guide Platform using Docker and Docker Compose on Linux, Windows (WSL2), generic VPS, AWS, Azure, and GCP.

---

## 1. System Requirements

| Specification | Development / Constrained Minimum | Recommended Production (Cloud / VPS) |
| :--- | :--- | :--- |
| **Operating System** | Linux (Ubuntu 22.04 / Debian 12) or Windows 10/11 with WSL2 | Linux (Ubuntu 22.04+ / Debian 12 / Amazon Linux 2023) |
| **CPU** | 4 Cores (x86_64) | 4 to 8 Cores (x86_64) |
| **RAM** | 8 GB Physical RAM (Requires swap) | 16 GB Physical RAM |
| **Storage** | 50 GB SSD (Model weights + OS + DB) | 50–100 GB NVMe / SSD |
| **Docker Engine** | Version 24.0+ with Compose v2 | Version 24.0+ with Compose v2 |

---

## 2. Container Topology

The deployment architecture consists of 4 long-running services and 1 one-shot initialization service:

```
[Browser / Tourist / Admin]
           │ HTTP :80
           ▼
   ┌───────────────┐
   │   frontend    │ (Nginx 1.27 Alpine: Static SPA + Reverse Proxy + Unbuffered SSE)
   └───────┬───────┘
           │ /api/v1/*
           ▼
   ┌───────────────┐
   │    backend    │ (FastAPI Python 3.12-slim: Non-root 'appuser', CPU AI Models)
   └───────┬───────┘
           ├─── Async DB :3306 ──► [ mysql: MySQL 8.0 Server ]
           └─── HTTP Inference :11434 ──► [ ollama: Ollama phi3:mini ]
                                              ▲
                                              │ (Initial model check / pull)
                                   [ ollama-pull: One-shot Init ]
```

### Persistent Volumes
- `mysql_data`: MySQL 8.0 database files (`/var/lib/mysql`).
- `chroma_data`: Embedded Chroma vector database (`/app/storage/chroma`).
- `pdf_storage`: Administrative uploaded source PDFs (`/app/storage/documents`).
- `piper_models`: Piper English ONNX voice model assets (`/app/storage/models/voices`).
- `huggingface_cache`: Shared model cache for SentenceTransformers, CrossEncoder, Whisper, NLLB-200, MMS-TTS (`/home/appuser/.cache/huggingface`).
- `ollama_data`: `phi3:mini` GGUF weights (`/root/.ollama`).

---

## 3. Initial Configuration

1. **Clone the Repository:**
   ```bash
   git clone <repository_url>
   cd "Karnataka Guide"
   ```

2. **Generate Environment Configuration:**
   ```bash
   cp .env.example .env
   ```

3. **Configure Secrets in `.env`:**
   * Generate a secure random key of at least 32 characters for `JWT_SECRET_KEY`:
     ```bash
     openssl rand -hex 32
     ```
   * Set strong passwords for `MYSQL_ROOT_PASSWORD`, `DB_PASSWORD`, and `BOOTSTRAP_ADMIN_PASSWORD`.
   * Set `APP_PROFILE=standalone` (or `cloud`).
   * For initial setup, leave `HF_HUB_OFFLINE=0` and `TRANSFORMERS_OFFLINE=0` to allow initial weight acquisition.

---

## 4. Deployment Lifecycle

### Stage A: Clean Installation Validation (Fresh Stack)
To verify that a completely clean stack installs, migrates, and starts properly:

1. **Launch with Isolated Clean Project Name:**
   ```bash
   docker compose -p karnataka-clean up -d --build
   ```
2. **Monitor Initialization:**
   ```bash
   docker compose -p karnataka-clean logs -f
   ```
   * `mysql` initializes and passes healthcheck.
   * `ollama` starts and `ollama-pull` verifies or pulls `phi3:mini` and exits with code 0.
   * `backend` runs Alembic migrations (`alembic upgrade head`), bootstraps the super admin, and reaches `/ready`.
   * `frontend` starts Nginx and responds on port 80.
3. **Populate and Verify Model Caches:**
   ```bash
   docker compose -p karnataka-clean exec backend python deployment/preflight_models.py --initialize
   docker compose -p karnataka-clean exec backend python deployment/preflight_models.py --verify-offline
   ```
4. **Tear Down Clean Test (Preserving Host Development State):**
   ```bash
   docker compose -p karnataka-clean down -v
   ```

---

### Stage B: State-Preserving Deployment (Existing Project Migration)
To migrate existing relational data, active knowledge generations, and documents into the containerized stack:

1. **Export Host State:**
   * Create logical MySQL dump from existing dev MySQL instance (e.g. port 3307):
     ```bash
     mysqldump -h 127.0.0.1 -P 3307 -u root karnataka_guide > backups/migration_mysql.sql
     ```
   * Archive Chroma and PDF directories:
     ```bash
     tar -czf backups/migration_chroma.tar.gz -C backend/storage/chroma .
     tar -czf backups/migration_pdf.tar.gz -C backend/storage/documents .
     ```

2. **Start Docker MySQL Service:**
   ```bash
   docker compose up -d mysql
   ```

3. **Restore MySQL Logical Dump:**
   ```bash
   docker compose exec -T mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} karnataka_guide < backups/migration_mysql.sql
   ```

4. **Restore Chroma and PDF Named Volumes:**
   ```bash
   # Restore PDF storage
   docker run --rm -v karnataka-guide_pdf_storage:/data -v $(pwd)/backups:/backup alpine \
       sh -c "rm -rf /data/* && tar -xzf /backup/migration_pdf.tar.gz -C /data"

   # Restore Chroma vector storage
   docker run --rm -v karnataka-guide_chroma_data:/data -v $(pwd)/backups:/backup alpine \
       sh -c "rm -rf /data/* && tar -xzf /backup/migration_chroma.tar.gz -C /data"
   ```

5. **Start Remaining Services:**
   ```bash
   docker compose up -d --build
   ```

6. **Initialize and Verify Model Volumes:**
   ```bash
   docker compose exec backend python deployment/preflight_models.py --initialize
   docker compose exec backend python deployment/preflight_models.py --verify-offline
   ```

7. **Verify Active Generation Invariant:**
   * Active generation ID `1a2c6365-1bee-4478-9599-a706ee5c7221` remains `is_active = true`.
   * Temporary generation `24a31cd8-3680-494c-95f0-22c57c516ac1` remains `is_active = false`.

---

## 5. Offline Standalone Execution

Once persistent model caches (`huggingface_cache`, `piper_models`, `ollama_data`) have been populated:

1. Update `.env`:
   ```dotenv
   HF_HUB_OFFLINE=1
   TRANSFORMERS_OFFLINE=1
   ```
2. Restart backend:
   ```bash
   docker compose restart backend
   ```
3. Run offline preflight verification:
   ```bash
   docker compose exec backend python deployment/preflight_models.py --verify-offline
   ```
   *The entire platform now functions 100% offline with zero external WAN connectivity.*

---

## 6. Verification and Health Probes

### Subsystem Health
- **Public API Health:** `curl http://localhost/api/v1/health`
- **Internal Backend Readiness:** `docker compose exec backend curl -f http://127.0.0.1:8000/ready`
- **Internal Backend Liveness:** `docker compose exec backend curl -f http://127.0.0.1:8000/live`

### Incremental SSE Streaming
- Send query to `POST /api/v1/tourist/chat/stream`.
- Unbuffered tokens stream incrementally before `citations` and `done`.

### Two-Step Voice Flow
1. Audio transcription and chat:
   ```bash
   curl -X POST http://localhost/api/v1/tourist/chat/voice \
     -F "session_uuid=<session_uuid>" \
     -F "file=@sample.wav"
   ```
   Returns JSON with `chat.message_id`.
2. Speech synthesis:
   ```bash
   curl -X POST http://localhost/api/v1/tourist/voice/synthesize \
     -H "Content-Type: application/json" \
     -d '{"session_uuid":"<session_uuid>","assistant_message_id":"<message_id>"}' \
     --output speech.wav
   ```

---

## 7. Portable Backup & Disaster Recovery

### Backup Commands
```bash
# 1. MySQL Dump
docker compose exec -T mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} karnataka_guide > backups/backup_$(date +%Y%m%d).sql

# 2. PDF Document Volume Backup
docker run --rm -v karnataka-guide_pdf_storage:/data:ro -v $(pwd)/backups:/backup alpine \
    tar -czf /backup/pdf_backup_$(date +%Y%m%d).tar.gz -C /data .

# 3. ChromaDB Consistent Snapshot (Quiesce backend writes)
docker compose stop backend
docker run --rm -v karnataka-guide_chroma_data:/data:ro -v $(pwd)/backups:/backup alpine \
    tar -czf /backup/chroma_backup_$(date +%Y%m%d).tar.gz -C /data .
docker compose start backend
```

---

## 8. Troubleshooting & Known Considerations

- **8 GB Host Memory Ceiling:** On memory-constrained hosts (8 GB RAM), run a single Uvicorn worker and ensure swap is enabled. In Windows WSL2, consider setting `.wslconfig` (`memory=6GB`, `swap=4GB`) if memory pressure occurs.
- **Nginx 413 Payload Too Large:** Nginx `client_max_body_size` is configured to `55M` to allow 50 MiB PDFs with multipart headers. Do not reduce this setting.
- **Ollama Restart:** Ollama weights persist in `ollama_data`. On restart, `ollama show phi3:mini` confirms local availability without contacting external registries.
