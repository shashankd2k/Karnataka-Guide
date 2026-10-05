# Complete 23-Phase Engineering Roadmap (Phases.md)

## Project Title
**AI-Powered Smart Tourist Guide Platform for Karnataka**

---

## Roadmap Overview

Development follows an immutable, sequential 23-phase engineering discipline. No phase may begin until the preceding phase is verified, tested, documented, and checkpointed.

```text
[PHASE 1: Requirements & Architecture] ➔ [PHASE 2: Backend Foundation] ➔ [PHASE 3: MySQL Persistence] ➔
[PHASE 4: Admin Auth & RBAC] ➔ [PHASE 5: PDF Document Management] ➔ [PHASE 6: Knowledge Base Pipeline] ➔
[PHASE 7: RAG Retrieval Optimization] ➔ [PHASE 8: Multilingual Engine] ➔ [PHASE 9: Ollama LLM Integration] ➔
[PHASE 10: Speech-To-Text (STT)] ➔ [PHASE 11: Translation Hardening] ➔ [PHASE 12: Text-To-Speech (TTS)] ➔
[PHASE 13: Unified Client Gateway] ➔ [PHASE 14: Tourist Web Experience] ➔ [PHASE 15: Admin Dashboard UI] ➔
[PHASE 16: End-to-End Integration] ➔ [PHASE 17: Docker & Cloud Deployment] ➔ [PHASE 18: Performance & Latency] ➔
[PHASE 19: Monitoring & Analytics] ➔ [PHASE 20: Security Hardening] ➔ [PHASE 21: Comprehensive Testing] ➔
[PHASE 22: Final Documentation] ➔ [PHASE 23: Production Readiness & Review]
```

---

## Phase Specifications (1 to 23)

### PHASE 1 — Requirements & Architecture Specification
- **Objective**: Establish complete product specification, system architecture, database design, UI/UX system, and engineering rules.
- **Scope**: Documentation and design artifacts only. Zero application code or database migrations.
- **Tasks**:
  1. Author `PRD.md` with complete persona, journey, functional, and non-functional requirements.
  2. Author `Architecture.md` with Clean Architecture layers, data pipelines, MySQL schemas, and API contracts.
  3. Author `Rules.md` defining lean coding standards, anti-bloat rules, and AI grounding policies.
  4. Author `Phases.md` detailing the 23-phase engineering roadmap.
  5. Author `Design.md` establishing the Karnataka Heritage visual system.
  6. Author `Memory.md` and supporting `docs/` trackers (`CHECKPOINTS.md`, `changelog.md`, `milestones.md`).
- **Files Expected**: `PRD.md`, `Architecture.md`, `Rules.md`, `Phases.md`, `Design.md`, `Memory.md`, `docs/CHECKPOINTS.md`, `docs/changelog.md`, `docs/milestones.md`.
- **Database Impact**: Schema design documented in `Architecture.md` (no execution).
- **API Impact**: Contract specifications defined (no execution).
- **UI Impact**: Design tokens and component guidelines specified in `Design.md`.
- **Tests Required**: Cross-document consistency verification.
- **Completion Criteria**: All 9 documentation artifacts exist, align perfectly, and pass cross-consistency review.
- **Exclusions**: Application code, migrations, model downloads.
- **Checkpoint**: `CHECKPOINT-P1`

---

### PHASE 2 — Backend Foundation & Core Infrastructure
- **Objective**: Construct the minimal, production-grade FastAPI application foundation.
- **Scope**: Application startup, configuration management, structured logging, typed exception hierarchy, health probes, correlation IDs, and test harness.
- **Tasks**:
  1. Initialize `backend/` project structure and Python virtual environment configuration.
  2. Implement `app/core/config.py` using `pydantic-settings` with `.env` loading and environment profile switching (`dev`, `standalone`, `cloud`).
  3. Implement `app/core/logging.py` using `structlog` for structured JSON output and request correlation tracking.
  4. Implement `app/core/errors.py` with custom domain exception handlers and standard error JSON envelopes.
  5. Implement `/api/v1/health` and `/api/v1/ready` probes.
  6. Configure Pytest test runner with `httpx.AsyncClient` test harness.
- **Files Expected**: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/logging.py`, `backend/app/core/errors.py`, `backend/app/api/v1/endpoints/health.py`, `backend/tests/test_health.py`.
- **Database Impact**: None.
- **API Impact**: `GET /api/v1/health`, `GET /api/v1/ready`.
- **UI Impact**: None.
- **Tests Required**: Unit tests for config loading, error serialization, and health endpoints.
- **Completion Criteria**: FastAPI launches cleanly, passes all health tests, and outputs structured correlation logs.
- **Exclusions**: Database connections, business logic, AI engines.
- **Checkpoint**: `CHECKPOINT-P2`

---

### PHASE 3 — MySQL Persistence Foundation & Alembic Migrations
- **Objective**: Implement async MySQL database connectivity, SQLAlchemy 2.x ORM models, and versioned Alembic migrations.
- **Scope**: Relational metadata schema implementation for all 16 system tables.
- **Tasks**:
  1. Configure `SQLAlchemy` async session factory with `asyncmy` driver.
  2. Define declarative base and all ORM models (`Admin`, `Document`, `KnowledgeGeneration`, `DocumentChunk`, `Embedding`, `ChatSession`, `ChatMessage`, `AuditLog`, `SystemLog`, `DeploymentHistory`, `HealthMetric`, `ModelRegistry`, `VoiceRegistry`, `TranslationRegistry`, `SystemSetting`).
  3. Set up Alembic migration environment and generate baseline migration `001_initial_schema.py`.
  4. Implement database health probe verifying connection pool latency.
- **Files Expected**: `backend/app/infrastructure/db/session.py`, `backend/app/infrastructure/db/models/*.py`, `backend/alembic/`, `backend/alembic.ini`, `backend/tests/test_db.py`.
- **Database Impact**: Baseline migration executed against MySQL 8.0 with foreign keys and indexes.
- **API Impact**: Health probe updated with live DB ping.
- **UI Impact**: None.
- **Tests Required**: DB connection, migration upgrade/downgrade cycle, model CRUD unit tests.
- **Completion Criteria**: All 16 tables created with verified indexes and reversible migrations.
- **Exclusions**: Authentication endpoints, file storage logic.
- **Checkpoint**: `CHECKPOINT-P3`

---

### PHASE 4 — Admin Authentication & RBAC
- **Objective**: Implement secure administrative authentication, Argon2id password hashing, rotating JWT tokens, and role-based access control.
- **Scope**: Admin authentication APIs and RBAC middleware. Tourist experience remains 100% unauthenticated.
- **Tasks**:
  1. Implement `Argon2id` password hashing utilities.
  2. Implement JWT token generation (access token: 15 min, refresh token: 7 days) and rotation logic.
  3. Implement FastAPI security dependencies for RBAC (`SUPER_ADMIN`, `SITE_CURATOR`, `OPERATOR`, `VIEWER`).
  4. Create administrative endpoints: `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`.
  5. Implement administrative action audit logging into `audit_logs` table.
- **Files Expected**: `backend/app/core/security.py`, `backend/app/application/auth/`, `backend/app/api/v1/endpoints/auth.py`, `backend/tests/test_auth.py`.
- **Database Impact**: Seed default super admin account; writes to `admins` and `audit_logs`.
- **API Impact**: `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`.
- **UI Impact**: None.
- **Tests Required**: Login with valid/invalid credentials, token expiration, refresh rotation, role authorization guards.
- **Completion Criteria**: Secure JWT lifecycle verified with full test coverage and zero plain-text secrets.
- **Exclusions**: Tourist authentication (strictly forbidden).
- **Checkpoint**: `CHECKPOINT-P4`

---

### PHASE 5 — PDF Document Management & Secure Storage
- **Objective**: Implement administrative PDF document upload, validation, deduplication, and storage.
- **Scope**: Document upload and metadata lifecycle.
- **Tasks**:
  1. Implement secure file upload handler with MIME validation, magic-byte inspection (`%PDF-`), and 50MB size guard.
  2. Calculate SHA-256 hash to prevent duplicate document ingestion.
  3. Store physical PDFs under randomized UUIDs in dedicated storage directory.
  4. Implement admin document endpoints: list, view metadata, download raw PDF, soft delete.
  5. Record audit logs for all document operations.
- **Files Expected**: `backend/app/application/documents/`, `backend/app/infrastructure/storage/`, `backend/app/api/v1/endpoints/documents.py`, `backend/tests/test_documents.py`.
- **Database Impact**: CRUD operations on `documents` table.
- **API Impact**: `POST /api/v1/admin/documents/upload`, `GET /api/v1/admin/documents`, `DELETE /api/v1/admin/documents/{id}`.
- **UI Impact**: None.
- **Tests Required**: Valid PDF upload, invalid file rejection, duplicate hash rejection, file traversal protection.
- **Completion Criteria**: PDFs uploaded and stored securely with SHA-256 deduplication and audit tracking.
- **Exclusions**: Text extraction or chunking (Phase 6).
- **Checkpoint**: `CHECKPOINT-P5`

---

### PHASE 6 — Knowledge Base Pipeline & Immutable Generations
- **Objective**: Implement text extraction, semantic chunking, vector embedding, and immutable ChromaDB collection management.
- **Scope**: PyMuPDF extraction, Unicode cleaning, chunking, MiniLM embeddings, ChromaDB indexing, and promotion/rollback mechanics.
- **Tasks**:
  1. Implement PyMuPDF extractor preserving page numbers, section headers, and layout structure.
  2. Apply Unicode normalization for Kannada and English text.
  3. Implement structural semantic chunker (300–500 tokens with 10% overlap).
  4. Generate 384-dimensional embeddings via `sentence-transformers/all-MiniLM-L6-v2`.
  5. Index embeddings into isolated ChromaDB collection `kg_gen_{version}`.
  6. Store chunk and embedding metadata in MySQL (`document_chunks`, `embeddings`, `knowledge_generations`).
  7. Implement promotion logic (activating generation) and instant rollback logic.
- **Files Expected**: `backend/app/application/ingestion/`, `backend/app/infrastructure/vector/chroma.py`, `backend/app/api/v1/endpoints/generations.py`, `backend/tests/test_ingestion.py`.
- **Database Impact**: Bulk inserts into `knowledge_generations`, `generation_status`, `document_chunks`, `embeddings`.
- **API Impact**: `/api/v1/admin/generations/build`, `/api/v1/admin/generations/{id}/promote`, `/api/v1/admin/generations/{id}/rollback`.
- **UI Impact**: None.
- **Tests Required**: Text extraction fidelity, chunk boundary validity, vector dimension verification (384d), atomic promotion/rollback.
- **Completion Criteria**: PDF knowledge compiled into verified, immutable ChromaDB generations with rollback capability.
- **Exclusions**: Hybrid retrieval fusion (Phase 7).
- **Checkpoint**: `CHECKPOINT-P6`

---

### PHASE 7 — RAG Retrieval Optimization & Re-ranking
- **Objective**: Implement production hybrid retrieval (Dense + BM25), Reciprocal Rank Fusion (RRF), and Cross-Encoder re-ranking.
- **Scope**: High-precision RAG retrieval engine with noise filtering.
- **Tasks**:
  1. Implement dense vector retriever querying active ChromaDB collection.
  2. Implement sparse keyword retriever using `rank-bm25` over parsed chunks.
  3. Implement Reciprocal Rank Fusion ($RRF(d) = \sum \frac{1}{k + r_i(d)}$) to merge top-25 dense and top-25 sparse results.
  4. Implement re-ranking stage using `cross-encoder/ms-marco-MiniLM-L-6-v2` for top-15 fused chunks.
  5. Implement heuristic noise filter to remove headers, tables of contents, and references.
  6. Implement admin retrieval diagnostic endpoint `/api/v1/admin/diagnostics/retrieve`.
- **Files Expected**: `backend/app/application/rag/retriever.py`, `backend/app/application/rag/reranker.py`, `backend/app/application/rag/fusion.py`, `backend/tests/test_retrieval.py`.
- **Database Impact**: Read queries on `document_chunks` and `knowledge_generations`.
- **API Impact**: `POST /api/v1/admin/diagnostics/retrieve`.
- **UI Impact**: None.
- **Tests Required**: Recall@5 and MRR benchmarks on test query suite; verification of noise filtering.
- **Completion Criteria**: Retrieval pipeline returns top-5 relevant chunks in $\le 350$ ms with verifiable re-ranking scores.
- **Exclusions**: LLM generation (Phase 9).
- **Checkpoint**: `CHECKPOINT-P7`

---

### PHASE 8 — Multilingual Conversation Engine & Grounding Guard
- **Objective**: Implement language detection, session-level multi-turn memory, coreference resolution, and strict grounding verification.
- **Scope**: Conversational context building and anti-hallucination defense.
- **Tasks**:
  1. Implement lightweight language detector for Kannada and English.
  2. Implement anonymous session manager tracking multi-turn query history.
  3. Implement context builder resolving pronouns and follow-up references.
  4. Implement Strict Grounding Guard: if retrieval confidence < threshold, enforce standard missing evidence message in Kannada/English.
  5. Implement citation token formatting mapping chunks to source pages.
- **Files Expected**: `backend/app/application/conversation/`, `backend/app/domain/grounding.py`, `backend/tests/test_conversation.py`.
- **Database Impact**: Writes to `chat_sessions` and `chat_messages`.
- **API Impact**: Internal conversation orchestration interfaces.
- **UI Impact**: None.
- **Tests Required**: Multi-turn coreference resolution tests, grounding fallback trigger tests for ungrounded queries.
- **Completion Criteria**: Context accurately assembled with guaranteed fallback on missing evidence.
- **Exclusions**: Direct LLM streaming (Phase 9).
- **Checkpoint**: `CHECKPOINT-P8`

---

### PHASE 9 — Ollama LLM Integration & Token Streaming
- **Objective**: Connect local Ollama instance, format grounded prompts, and stream responses via Server-Sent Events (SSE).
- **Scope**: LLM inference, context budgeting, token streaming, and citation validation.
- **Tasks**:
  1. Implement `OllamaLLMProvider` interfacing with `http://localhost:11434` supporting `llama3.1:8b`.
  2. Implement context budgeting ensuring prompt context fits within model window without truncation.
  3. Implement SSE streaming response endpoint `/api/v1/tourist/chat/stream`.
  4. Validate citation tags in real-time stream and calculate end-to-end token latency.
- **Files Expected**: `backend/app/infrastructure/llm/ollama.py`, `backend/app/application/rag/generator.py`, `backend/app/api/v1/endpoints/tourist.py`, `backend/tests/test_llm.py`.
- **Database Impact**: Persist completed assistant turns into `chat_messages`.
- **API Impact**: `POST /api/v1/tourist/chat/stream`, `POST /api/v1/tourist/chat`.
- **UI Impact**: None.
- **Tests Required**: Mocked and live Ollama generation tests, token streaming integrity, prompt injection resistance.
- **Completion Criteria**: First token delivered in $\le 1.8$ s with verified grounding and citation metadata.
- **Exclusions**: Speech audio synthesis (Phase 10/12).
- **Checkpoint**: `CHECKPOINT-P9`

---

### PHASE 10 — Speech-To-Text (STT) Engine
- **Objective**: Implement high-accuracy voice transcription supporting Kannada, English, and code-mixed speech using `faster-whisper`.
- **Scope**: Browser audio ingest, validation, normalization, and local transcription.
- **Tasks**:
  1. Implement audio ingest endpoint accepting `WAV`, `WebM`, `OGG`, `MP3`, `M4A` audio buffers.
  2. Implement audio normalization using `ffmpeg` / `pydub` (16kHz mono PCM).
  3. Configure local `faster-whisper` model with Kannada language prompting.
  4. Return transcription text, detected language, confidence score, and segment timestamps.
  5. Implement STT health check probe.
- **Files Expected**: `backend/app/infrastructure/speech/whisper_stt.py`, `backend/app/application/speech/stt_service.py`, `backend/app/api/v1/endpoints/voice.py`, `backend/tests/test_stt.py`.
- **Database Impact**: Optional audio latency recording in `chat_messages`.
- **API Impact**: `POST /api/v1/tourist/voice/transcribe`.
- **UI Impact**: None.
- **Tests Required**: Audio decoding test across formats, Kannada transcription accuracy test, latency benchmark.
- **Completion Criteria**: 5-second audio snippet transcribed in $\le 800$ ms with $\ge 90\%$ accuracy.
- **Exclusions**: Text-to-speech synthesis (Phase 12).
- **Checkpoint**: `CHECKPOINT-P10`

---

### PHASE 11 — Offline Translation Hardening (Meta NLLB-200 600M)
- **Objective**: Harden offline English $\leftrightarrow$ Kannada translation for tourist queries, grounded responses, and heritage terminology preservation using `facebook/nllb-200-distilled-600M` under the provider-neutral `ITranslationProvider` port.
- **Scope**: NLLB-200 model loading, proper-noun and citation-label masking, retrieval query translation, grounded answer translation, and graceful fallback. (Argos excluded due to lack of official Kannada packages; IndicTrans2 blocked by Windows build requirements).
- **Tasks**:
  1. Implement `ITranslationProvider` domain port and `NLLBTranslationProvider` infrastructure adapter.
  2. Implement proper-noun, historical date, and citation-label protection (`mask_protected_tokens` / `unmask_protected_tokens`) with fail-safe validation.
  3. Integrate Kannada query translation to English for Phase 7 retrieval in `ConversationService`.
  4. Integrate grounded English response translation to Kannada with authoritative citation preservation.
  5. Implement exact hardcoded Kannada fallback for ungrounded queries (`"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`).
- **Files Expected**: `backend/app/domain/ports/translation.py`, `backend/app/infrastructure/translation/nllb.py`, `backend/app/application/translation/service.py`, `backend/tests/test_translation.py`.
- **Database Impact**: Active translation pair status in `translation_registry`.
- **API Impact**: `GET /api/v1/admin/translations`.
- **UI Impact**: None.
- **Tests Required**: Translation fidelity on heritage terms, entity & citation preservation tests, retrieval score improvement test, benchmark latency.
- **Completion Criteria**: Offline translation executes reliably with zero external API calls, preserving citation tags and heritage entities.
- **Exclusions**: TTS audio (Phase 12), frontend modifications (Phase 13+).
- **Checkpoint**: `CHECKPOINT-P11`

---

### PHASE 12 — Text-To-Speech (TTS) Synthesis (Piper)
- **Objective**: Implement high-speed local speech synthesis for Kannada and English responses using `Piper`.
- **Scope**: ONNX neural voice synthesis, audio streaming, and browser delivery.
- **Tasks**:
  1. Configure local Piper neural voice models for Kannada and English.
  2. Implement text pre-processing (stripping markdown, citation tags, and URLs before synthesis).
  3. Stream synthesized audio chunks in WAV/OGG format.
  4. Implement LRU audio cache for frequently generated tourist responses.
  5. Implement TTS health check probe.
- **Files Expected**: `backend/app/infrastructure/speech/piper_tts.py`, `backend/app/application/speech/tts_service.py`, `backend/app/api/v1/endpoints/voice.py`, `backend/tests/test_tts.py`.
- **Database Impact**: Update `voice_registry`.
- **API Impact**: `POST /api/v1/tourist/voice/synthesize`.
- **UI Impact**: None.
- **Tests Required**: Synthesis latency benchmark, audio format validation, markdown stripping test.
- **Completion Criteria**: Speech synthesis begins streaming in $\le 600$ ms with natural pronunciation.
- **Exclusions**: Frontend UI player (Phase 14).
- **Checkpoint**: `CHECKPOINT-P12`

---

### PHASE 13 — Unified FastAPI Client Gateway
- **Objective**: Consolidate and freeze all frontend-facing API contracts, error structures, and session lifecycles.
- **Scope**: Final backend contract hardening, CORS restrictions, rate limiting, and OpenAPI schema generation.
- **Tasks**:
  1. Review and freeze all `/api/v1/tourist/*` and `/api/v1/admin/*` routes.
  2. Enforce uniform JSON error envelopes across all HTTP status codes.
  3. Apply IP rate limiting (60 requests/min on public endpoints).
  4. Generate and validate OpenAPI 3.1 JSON schema.
- **Files Expected**: `backend/app/api/v1/router.py`, `backend/tests/test_api_gateway.py`.
- **Database Impact**: None.
- **API Impact**: Full `/api/v1` contract freeze.
- **UI Impact**: None.
- **Tests Required**: End-to-end API integration tests, rate limiting tests, schema validation.
- **Completion Criteria**: Complete OpenAPI spec exported and verified with zero schema inconsistencies.
- **Exclusions**: Frontend implementation (Phase 14).
- **Checkpoint**: `CHECKPOINT-P13`

---

### PHASE 14 — Premium Tourist Web Experience (React 19 + Tailwind)
- **Objective**: Build the world-class, commercial-grade Tourist Web Application.
- **Scope**: Complete tourist user interface with Kannada heritage aesthetics.
- **Tasks**:
  1. Initialize React 19 + TypeScript + Vite project in `frontend/`.
  2. Implement Karnataka Heritage Design System tokens (Temple Gold, Deep Brown, Soapstone Grey, Ivory).
  3. Build Hero Landing Page with immersive heritage visual aesthetics.
  4. Build Bilingual AI Chat Interface with real-time SSE streaming.
  5. Build Voice Assistant module with browser audio capture and animated waveform.
  6. Build Verifiable Citation Side Panel linking responses to source excerpts.
  7. Build Destination Explorer and Interactive Leaflet Heritage Map with custom markers.
  8. Implement Smart Suggested Follow-up Questions and Local Session persistence.
  9. Enforce full responsiveness, light/dark mode, and WCAG 2.1 AA accessibility.
- **Files Expected**: `frontend/src/pages/TouristApp.tsx`, `frontend/src/components/tourist/*`, `frontend/src/hooks/*`, `frontend/src/stores/touristStore.ts`.
- **Database Impact**: None (Client-side).
- **API Impact**: Consumes all `/api/v1/tourist/*` endpoints.
- **UI Impact**: Full tourist interface operational.
- **Tests Required**: Component unit tests, accessibility audits (axe-core), responsive layout checks.
- **Completion Criteria**: High-end UI with instantaneous streaming, voice interaction, and interactive map.
- **Exclusions**: Admin dashboard screens (Phase 15).
- **Checkpoint**: `CHECKPOINT-P14`

---

### PHASE 15 — Premium Admin Command Dashboard
- **Objective**: Build the administrative management and diagnostics portal.
- **Scope**: Complete admin UI for knowledge, vector, model, and system management.
- **Tasks**:
  1. Build secure Admin Login screen with JWT token storage.
  2. Build Executive Dashboard with telemetry counters and usage charts.
  3. Build Document Management view with drag-and-drop PDF upload and status indicators.
  4. Build Knowledge Generation Manager with visual pipeline status and one-click rollback.
  5. Build Chunk & Embedding Explorer for granular inspection of vector representations.
  6. Build Retrieval Diagnostics Tool for real-time testing of dense/sparse/rerank scores.
  7. Build Model, Voice, and Translation Registry management panels.
  8. Build System Health Monitor with live 5-second telemetry polling.
  9. Build Audit Logs & Conversation Analytics views.
- **Files Expected**: `frontend/src/pages/admin/*`, `frontend/src/components/admin/*`, `frontend/src/stores/adminStore.ts`.
- **Database Impact**: None (Client-side).
- **API Impact**: Consumes all `/api/v1/admin/*` and `/api/v1/auth/*` endpoints.
- **UI Impact**: Full admin interface operational.
- **Tests Required**: Admin authentication flow tests, document upload UI tests, retrieval diagnostics tests.
- **Completion Criteria**: Complete administrative suite operational with real-time telemetry and generation controls.
- **Exclusions**: Multi-node production deployment (Phase 17).
- **Checkpoint**: `CHECKPOINT-P15`

---

### PHASE 16 — Full End-to-End System Integration
- **Objective**: Connect all frontend and backend subsystems and verify complete user journeys.
- **Scope**: Tourist voice/text workflows, PDF ingestion to active RAG, citation rendering, and telemetry.
- **Tasks**:
  1. Execute complete tourist text query lifecycle: Query $\rightarrow$ Context $\rightarrow$ Hybrid RAG $\rightarrow$ Ollama $\rightarrow$ Citation Panel.
  2. Execute complete tourist voice lifecycle: Mic $\rightarrow$ Whisper $\rightarrow$ RAG $\rightarrow$ Piper TTS $\rightarrow$ Speaker playback.
  3. Execute admin knowledge lifecycle: Upload PDF $\rightarrow$ Build Generation $\rightarrow$ Diagnostics $\rightarrow$ Promote $\rightarrow$ Verify Tourist response.
  4. Verify instant rollback restoring previous knowledge state.
- **Files Expected**: `tests/e2e/test_complete_flows.py`.
- **Database Impact**: Verified transactional records across all tables.
- **API Impact**: Full system integration verified.
- **UI Impact**: Verified smooth user interaction across all viewports.
- **Tests Required**: End-to-end Playwright / automated integration test suite.
- **Completion Criteria**: 100% of integration test journeys pass without manual intervention.
- **Exclusions**: Cloud container orchestration (Phase 17).
- **Checkpoint**: `CHECKPOINT-P16`

---

### PHASE 17 — Docker & Cloud Deployment Configuration
- **Objective**: Package the platform into production-ready Docker containers and deployment profiles.
- **Scope**: Multi-stage Dockerfiles, Docker Compose, Nginx reverse proxy, and environment configs.
- **Tasks**:
  1. Create multi-stage `Dockerfile` for backend (Python 3.12, PyMuPDF, Whisper, Piper, Argos).
  2. Create multi-stage `Dockerfile` for frontend (Node 20, Vite build, Nginx static serve).
  3. Author `docker-compose.yml` for local standalone containerized execution.
  4. Author `docker-compose.cloud.yml` with Nginx SSL termination, automated health checks, and named volumes.
  5. Author deployment documentation for VPS, AWS, Azure, and GCP.
- **Files Expected**: `deployment/Dockerfile.backend`, `deployment/Dockerfile.frontend`, `deployment/docker-compose.yml`, `deployment/nginx/nginx.conf`.
- **Database Impact**: MySQL runs in isolated container with persistent volume.
- **API Impact**: Reverse-proxied via Nginx under `/api/v1`.
- **UI Impact**: Served via Nginx static caching.
- **Tests Required**: Container build verification, multi-container network health checks.
- **Completion Criteria**: Complete stack launches cleanly via `docker compose up` with zero errors.
- **Exclusions**: Performance tuning (Phase 18).
- **Checkpoint**: `CHECKPOINT-P17`

---

### PHASE 18 — Performance Benchmarking & Optimization
- **Objective**: Measure and optimize real system bottlenecks across all layers.
- **Scope**: Latency, memory, and database query optimization based strictly on measured metrics.
- **Tasks**:
  1. Benchmark API P95 latency under concurrent load (50 concurrent tourist sessions).
  2. Benchmark RAG retrieval latency across 50,000 document chunks.
  3. Benchmark Whisper and Piper inference times on target hardware.
  4. Optimize MySQL query indexes and connection pool settings.
  5. Optimize frontend bundle size and asset caching headers.
- **Files Expected**: `tests/benchmarks/benchmark_suite.py`, `docs/BENCHMARKS.md`.
- **Database Impact**: Query performance verified with `EXPLAIN ANALYZE`.
- **API Impact**: Verified P95 latency $< 1.8$ s for first token.
- **UI Impact**: Verified Lighthouse score $\ge 90$.
- **Tests Required**: Load testing with `locust` or `k6`.
- **Completion Criteria**: All performance NFRs (NFR-101 to NFR-105) fully satisfied and documented.
- **Exclusions**: Unmeasured speculative optimizations.
- **Checkpoint**: `CHECKPOINT-P18`

---

### PHASE 19 — Telemetry, Monitoring & Operational Analytics
- **Objective**: Implement production operational telemetry, resource monitoring, and analytics dashboards.
- **Scope**: System metrics collection, error aggregation, and conversation trend analysis.
- **Tasks**:
  1. Implement background telemetry task recording CPU, RAM, Disk, and Subsystem health every 60 seconds into `health_metrics`.
  2. Implement conversation analytics aggregating tourist query languages, top destinations, and feedback.
  3. Implement error rate alerting and structured log rotation.
  4. Expose operational metrics to admin dashboard.
- **Files Expected**: `backend/app/application/monitoring/`, `backend/tests/test_monitoring.py`.
- **Database Impact**: Periodic writes to `health_metrics` and reads from `chat_messages`.
- **API Impact**: `GET /api/v1/admin/health/history`, `GET /api/v1/admin/analytics/trends`.
- **UI Impact**: Real-time telemetry charts in Admin Dashboard.
- **Tests Required**: Telemetry background worker tests, analytics query aggregation tests.
- **Completion Criteria**: System health and tourist analytics visual in admin portal.
- **Exclusions**: Penetration testing (Phase 20).
- **Checkpoint**: `CHECKPOINT-P19`

---

### PHASE 20 — Security Hardening & OWASP Compliance
- **Objective**: Conduct comprehensive security hardening across auth, inputs, files, network, and dependencies.
- **Scope**: OWASP Top 10 mitigation, rate limiting, security headers, and vulnerability scanning.
- **Tasks**:
  1. Enforce strict Content Security Policy (CSP), HSTS, X-Frame-Options, and X-Content-Type-Options headers.
  2. Perform SQL injection, XSS, and CSRF automated vulnerability tests.
  3. Verify path traversal protection and secure file storage boundaries.
  4. Run dependency vulnerability audits (`pip-audit`, `npm audit`).
  5. Verify zero leakage of credentials or PII in logs or responses.
- **Files Expected**: `backend/app/core/security.py`, `docs/SECURITY_AUDIT.md`.
- **Database Impact**: None.
- **API Impact**: Hardened security middleware.
- **UI Impact**: Secure cookie handling and sanitized HTML rendering.
- **Tests Required**: Automated security regression suite.
- **Completion Criteria**: Zero high/critical vulnerabilities; 100% OWASP Top 10 compliance.
- **Exclusions**: User acceptance testing (Phase 21).
- **Checkpoint**: `CHECKPOINT-P20`

---

### PHASE 21 — Comprehensive Verification & Quality Assurance
- **Objective**: Execute end-to-end automated test suites across all functional and non-functional requirements.
- **Scope**: Unit tests, integration tests, RAG evaluation, voice tests, accessibility audits, and stress tests.
- **Tasks**:
  1. Run complete backend unit & integration test suite (Target: $\ge 90\%$ code coverage).
  2. Run RAG grounding evaluation on Karnataka heritage test dataset (Belur, Halebidu, Hampi).
  3. Run multilingual translation and transcription fidelity tests.
  4. Run automated accessibility test suite (WCAG 2.1 AA compliance).
  5. Run stress test validating system stability under prolonged execution.
- **Files Expected**: `tests/`, `frontend/tests/`, `docs/QA_REPORT.md`.
- **Database Impact**: Test database fixtures.
- **API Impact**: All endpoints exercised.
- **UI Impact**: All screens validated.
- **Tests Required**: Full Pytest, Playwright, Axe-core, and RAG evaluation suites.
- **Completion Criteria**: All test suites pass with zero regressions and documented QA report.
- **Exclusions**: Final documentation polish (Phase 22).
- **Checkpoint**: `CHECKPOINT-P21`

---

### PHASE 22 — Final Documentation & Operator Guides
- **Objective**: Finalize complete developer, operator, and deployment documentation.
- **Scope**: Setup guides, offline standalone installation manuals, cloud deployment playbooks, and API references.
- **Tasks**:
  1. Author `README.md` with quick-start instructions for dev, standalone, and cloud profiles.
  2. Author `docs/OFFLINE_SETUP.md` detailing model bundle downloads for offline kiosks.
  3. Author `docs/CLOUD_DEPLOYMENT.md` covering AWS, Azure, GCP, and Linux VPS deployments.
  4. Author `docs/ADMIN_OPERATOR_GUIDE.md` for Karnataka Tourism staff.
  5. Finalize API documentation and troubleshooting guides.
- **Files Expected**: `README.md`, `docs/OFFLINE_SETUP.md`, `docs/CLOUD_DEPLOYMENT.md`, `docs/ADMIN_OPERATOR_GUIDE.md`.
- **Database Impact**: None.
- **API Impact**: None.
- **UI Impact**: None.
- **Tests Required**: Documentation accuracy and link validation.
- **Completion Criteria**: Complete documentation suite ready for external handoff.
- **Exclusions**: Production sign-off (Phase 23).
- **Checkpoint**: `CHECKPOINT-P22`

---

### PHASE 23 — Production Readiness Review & GO / NO-GO Sign-Off
- **Objective**: Perform final multi-disciplinary architectural, security, performance, and operational review.
- **Scope**: Final release audit and GO / NO-GO decision.
- **Tasks**:
  1. Principal Architecture Review against `Architecture.md`.
  2. Principal Security Review against `Rules.md` and OWASP benchmarks.
  3. Principal AI Review of grounding accuracy, latency, and multilingual quality.
  4. Principal UI/UX Review of Karnataka Heritage aesthetics and accessibility.
  5. Backup and disaster recovery dry-run.
  6. Final GO / NO-GO executive decision sign-off.
- **Files Expected**: `docs/PRODUCTION_SIGN_OFF.md`, `Memory.md`.
- **Database Impact**: Production state locked.
- **API Impact**: Production deployment validated.
- **UI Impact**: Production build validated.
- **Tests Required**: Production smoke tests.
- **Completion Criteria**: Unanimous GO decision across all Principal engineering roles.
- **Exclusions**: None.
- **Checkpoint**: `CHECKPOINT-P23`
