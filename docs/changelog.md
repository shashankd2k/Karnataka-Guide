# Changelog (changelog.md)

All notable changes to the **AI-Powered Smart Tourist Guide Platform for Karnataka** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.18.0] - 2026-09-20 (Phase 18: Performance & Scalability Optimization — Level 1 Complete)

### Added & Optimized (Level 1)
- **L1-A Context Budget Sizing (`num_ctx = 1536`)**: Standardized `num_ctx = 1536` in `backend/app/core/config.py` and `backend/app/infrastructure/llm/ollama.py`. Yields 455 tokens (29.6%) headroom on single-turn max input (895) and 552 tokens (35.9%) on 5-turn history max input (798), saving ~260 MB of RAM while eliminating prompt truncation.
- **L1-B Controlled Docker Threading (`num_thread = 2`)**: Pinned `num_thread = 2` to match the 2 physical CPU cores of the Intel Core i3-1115G4, eliminating OpenMP spinlock convoying and reducing WSL2 swap usage.
- **L1-C Model Residency Keep-Alive (`keep_alive = "10m"`)**: Maintained `OLLAMA_KEEP_ALIVE=10m` across chat and streaming paths, ensuring warm turns load in < 200ms without runner recreation.
- **L1-D Persistent HTTP Client Connection Pooling**: Replaced per-request HTTP client creation in `backend/app/infrastructure/llm/ollama.py` with persistent `httpx.AsyncClient` pool (`max_keepalive_connections=10`, `keepalive_expiry=600.0`, with graceful `aclose()`).
- **L1-E Prompt Policy Directives & Stop Sequences**: Tightened directives in `backend/app/application/rag/prompt_builder.py` (Directive 7: 2–4 sentences single paragraph; Directive 8: forbid follow-ups, user simulation, or prefix markers). Implemented engine-level stop sequences (`\n\n`, `###`, `\nTourist Question:`, `\nTourist:`, `\nUser:`, `\nAssistant:`, `\nQuestion:`). Successfully passed 7/7 runaway query tests (P07, P08, P10, P21, P22, P24, P28) with 0 runaways and 0 truncations.
- **Resilient File Removal in Storage**: Added transient file-lock retry to `remove_pdf_from_storage` in `backend/app/application/documents/storage.py` for Windows file-system handle release resilience.

### Verified & Benchmarked
- **Retrieval Quality Floor**: 100% preserved (Hit@1 = 100.0%, Recall@5 = 100.0%, MRR = 1.0000, 0 bibliography intrusions, 0 hallucinations).
- **Runner Stability**: Verified across consecutive warm turns (load duration 23.45ms and 161.78ms; 0 reload spikes).
- **Empirical Benchmarks**: Measured English text cold (TTFT 284.75s, Total 485.97s) and warm (TTFT median 79.66s, Total median 147.91s); Kannada text cold (TTFT 272.44s, Total 273.70s); English voice warm (Run 3: 210.19s Server Audio Available); Kannada voice (300s timeout bound).
- **Voice Usability Classification**: Server Audio Available > 12.0s -> **STILL TOO SLOW FOR VOICE**. Level 2 Required: **YES**.
- **Regressions**: Backend 283 / 283 PASS (100%), Frontend 47 / 47 PASS (100%), Production build clean, All 4 Docker services healthy, All 7 AI models verified offline with zero cloud AI.
- **Governance**: **STOP GATE ACTIVE** (Level 2 NOT started, Phase 19 NOT started, `CHECKPOINT-P18 FINAL` NOT set).

## [0.17.0] - 2026-09-16 (Phase 17: Docker & Cloud Deployment — Complete)


### Added
- **Production Packaging & Container Topology (`deployment/`, `docker-compose.yml`, `.dockerignore`, `.env.example`)**:
  - `deployment/Dockerfile.backend`: Multi-stage Python 3.12-slim container with non-root runtime `appuser` (UID 10001, GID 10001), user-owned persistent model cache (`/home/appuser/.cache/huggingface`), explicit CPU-only PyTorch wheel pre-installation, OpenMP (`libgomp1`), audio codecs (`libsndfile1`), and startup healthcheck on `/ready`.
  - `deployment/Dockerfile.frontend`: Multi-stage compilation using pinned `node:22-alpine` (`npm ci` and `npm run build`), serving production assets via minimal `nginx:1.27-alpine` with built-in BusyBox `wget` healthcheck.
  - `deployment/nginx.conf`: Production reverse proxy configuration featuring `client_max_body_size 55M;` (accommodating 50 MiB PDFs with multipart boundary overhead), unbuffered real-time SSE streaming (`proxy_buffering off;`, `proxy_cache off;`, `chunked_transfer_encoding on;`), long-term static asset caching (`/assets/`), and SPA fallback routing (`try_files $uri $uri/ /index.html;`).
  - `deployment/entrypoint.sh`: Container entrypoint script performing TCP socket polling for MySQL readiness, executing Alembic database migrations (`alembic upgrade head`), and triggering idempotent super admin bootstrap before launching Uvicorn.
  - `deployment/preflight_models.py`: Lean deployment preflight utility providing `--initialize` (online cache population) and `--verify-offline` (offline smoke test without WAN). Reuses approved production providers and loaders without introducing new abstractions.
  - `docker-compose.yml`: Full modern Compose specification (no obsolete version key) orchestrating `mysql` (8.0), `ollama` (`ollama/ollama:0.33.3`), `ollama-pull` (one-shot init with local presence check `ollama show phi3:mini`), `backend`, and `frontend` on private bridge network `karnataka-net`. Uses Compose project isolation without hardcoded container names.
  - `.dockerignore`: Strictly excludes local development database files (`storage/mysql8_data`), secrets (`.env*`), virtual environments (`.venv`), temporary audio, and caches from container images.
  - `.env.example`: Complete deployment configuration template with safe placeholders, dedicated database application credentials, and offline flags (`HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`).
  - `docs/DEPLOYMENT.md`: Comprehensive deployment and operations manual covering system requirements, multi-stage deployment (Stage A clean install vs Stage B state migration), offline standalone operation, backup/restore via portable containers, and troubleshooting.

### Verified in Live Docker Runtime (Engine v29.8.0 / Compose v2.39.4)
- **Stage A Clean Deployment & Teardown**: Verified zero-state startup and clean teardown without orphan containers or volume leaks.
- **Stage B Persistent Multi-Container Topology**: Successfully deployed `karnatakaguide-frontend-1`, `karnatakaguide-backend-1`, `karnatakaguide-mysql-1`, and `karnatakaguide-ollama-1` backed by 6 named volumes (`mysql_data`, `ollama_data`, `huggingface_cache`, `piper_models`, `pdf_storage`, `chroma_data`).
- **Nginx Reverse Proxy Routing**: Port 80 successfully routes public traffic: `/` -> Frontend SPA (HTTP 200), `/api/v1/health` -> Backend API (HTTP 200).
- **SSE Streaming & Citations Contract**: Verified `POST /api/v1/tourist/chat/stream` through Nginx. Emits real incremental `token` events, `citations` event, and `done` event. Public citations contract strictly verified: exactly 4 public fields (`citation_label`, `source_filename`, `page_number`, `section_header`); zero leaked internal fields (`chunk_id`, `document_id`, `generation_id`, `reranker_score`, `raw_text` strictly absent).
- **Ungrounded Fallback**: Unsupported queries return `grounded=False`, `citations=[]`, and exact bilingual fallback text.
- **Voice Chat & Restricted TTS**: Validated `POST /api/v1/tourist/chat/voice` (Faster-Whisper STT) and `POST /api/v1/tourist/voice/synthesize` (Piper English 22050 Hz and MMS-TTS Kannada 16000 Hz).
- **TTS Security**: Verified rejection of raw text synthesis and cross-session / nonexistent message IDs (HTTP 404/422).
- **PDF Upload Size Limits**: Verified ~512KB valid PDF accepted and cleaned up via Admin API; oversized payloads exceeding 55M rejected with HTTP 413.
- **Admin & Tourist Concurrency**: Verified simultaneous tourist chat turns and administrative PDF operations without state collision or session leakage.
- **Container Restart Resilience**:
  - Backend restart: Alembic no-op, admin bootstrap idempotency preserved, `/ready` HTTP 200.
  - MySQL restart: Backend gracefully reconnected and database health restored to healthy.
  - Ollama offline restart: `phi3:mini` (2.2 GB) preserved in volume; local inference succeeded in 17.37s without network registry pull.
  - Full stack restart: All 4 containers recovered to healthy state; active generation `1a2c6365-1bee-4478-9599-a706ee5c7221` (active=1) preserved.
- **Zero Cloud AI Audit**: Verified 100% local in-cluster AI execution with zero forbidden cloud AI APIs.
- **Regression Baselines**: Backend 283 / 283 PASS (100%), Frontend 47 / 47 PASS (100%), Production Vite build clean.
- Attained **`CHECKPOINT-P17 = FINAL ACCEPTED`**.

## [0.16.0] - 2026-09-16 (Phase 16: Full End-to-End System Integration)

### Added
- **Full End-to-End Integration Suite (`scratch/run_phase16_e2e_live_integration.py`, `scratch/run_phase16_targeted_evidence_pass.py`)**:
  - Comprehensive live verification covering 17 integration matrix scenarios: bilingual chat, streaming SSE, Faster-Whisper STT, Piper & MMS-TTS audio synthesis, hybrid dense+BM25+CrossEncoder RAG, admin auth & RBAC, document management, and knowledge generation promotion/rollback.
  - End-to-end English voice-to-voice pipeline (Piper query -> Faster-Whisper STT -> Grounded RAG + Ollama phi3:mini -> Piper TTS) with 1,087,020 bytes WAV synthesis.
  - Chrome DevTools Protocol (CDP) real network failure test on `/map` with tile URL blocking and network offline emulation, validating offline banner display, map marker persistence, destination accessibility, and navigation availability.
  - Interactive responsive smoke checks across 390px (Mobile) and 1440px (Desktop Full) viewports for citation drawer, voice recorder modal, and admin confirmation dialog.
  - Database artifact hygiene: `.gitignore` rules established to prevent tracking of MySQL data files, InnoDB tablespaces, and database dumps.

### Fixed
- **NLLB-200 Offline Loading Defect (`backend/app/infrastructure/translation/nllb.py`)**:
  - *Offline Defect*: Under strict offline conditions with WAN blocked, `from_pretrained` defaulted to checking Hugging Face Hub for metadata updates, causing offline connection failures even when weights were already cached locally.
  - *Minimal Cache-First Fix*: Implemented a cache-first loading strategy using `local_files_only=True` in an initial try block. When cached, model and tokenizer load locally without remote network attempts. If un-cached (initial setup on a fresh host), the exception block falls back to online acquisition (`AutoTokenizer.from_pretrained(model_name)` and `AutoModelForSeq2SeqLM.from_pretrained(model_name)`).
  - *Compatibility*: Initial setup and first-run model download paths remain 100% preserved.
  - *Contract*: Zero changes to public API (`ITranslationProvider`), method signatures, response schemas, or model (`facebook/nllb-200-distilled-600M`).
  - *Regression Test*: Added focused unit tests in `backend/tests/test_translation.py` verifying cached local loading, zero remote network access, first-download online fallback, and error handling.
- **Database Configuration Test Isolation (`backend/tests/test_db_config.py`)**:
  - Isolated `test_default_database_settings` with `Settings(_env_file=None)` to verify the architectural default port (3306) without local development `.env` port overrides (3307).

### Verified
- **MySQL 8.0 Compliance**: Active database verified running on MySQL Community Server 8.0.31 (`SELECT VERSION()` returns `8.0.31`).
- **Generation Invariant Restoration**: Restored `1a2c6365-1bee-4478-9599-a706ee5c7221` (`v_20260829_183224_1a2c63`, `is_active=True`) as the sole active generation, with temporary generation `24a31cd8-3680-494c-95f0-22c57c516ac1` set to `is_active=False`.
- **Backend Test Suite**: 283 / 283 tests passing in Pytest (100% pass rate).
- **Frontend Test Suite**: 47 / 47 tests passing in Vitest (100% pass rate).
- **Production Build**: Clean Vite production build (`dist/assets/index-*.js`, `dist/assets/index-*.css`) with zero TypeScript errors.
- Attained **`CHECKPOINT-P16`**.

### Preserved Project Debt & Known Limitations
- *Phase 14*: Physical browser microphone capture remains unverified in headless automated CI environments.
- *Phase 14*: Kannada font binaries are not bundled; standalone offline rendering relies on OS-level Kannada font fallbacks.
- *Phase 16 Local Dev Security Debt*: Local development MySQL 8.0 instance uses default credentials; recorded for Phase 20 security hardening.
- *Phase 18 Debt*: Whole-system RAM footprint reaches ~7.7 GB on 8 GB development hardware with the full local AI stack loaded.

## [0.15.0] - 2026-09-01 (Phase 15: Premium Admin Dashboard)

### Added
- **Administrative Single Page Application (`frontend/src/pages/admin/`, `frontend/src/components/admin/`)**:
  - Full-featured administrative suite mounted under `/admin/*` with responsive navigation drawer, dark mode styling, and server-authoritative RBAC guard.
  - Separate unauthenticated login page (`/admin/login`) with Argon2id credentials verification, query parameter `?expired=1` session expiration notification, and seamless redirects.
- **Enterprise Authentication & Session Resilience (`stores/adminAuthStore.ts`, `services/adminApiClient.ts`)**:
  - In-memory `access_token` storage (60-minute lifetime) and `sessionStorage` `refresh_token` storage (7-day lifetime) eliminating long-term credential leakage in `localStorage`.
  - Single-flight Promise mutex (`inFlightRefreshPromise`) preventing concurrent duplicate refresh calls during rapid tab switching or component mounts.
  - Explicit error handling distinction: `401 Unauthorized` triggers single auto-refresh and retries original request once; `403 Forbidden` displays clean permission denied screen without refreshing or logging out.
  - Page reload session bootstrapping calling `POST /api/v1/admin/auth/refresh` followed by `GET /api/v1/admin/auth/me` with non-flickering loading screen.
  - Safe logout revoking refresh tokens on backend with guaranteed cleanup of local auth state.
- **Authoritative Document Management Console (`pages/admin/AdminDocumentsPage.tsx`)**:
  - Paginated document table with filename, SHA-256 hash preview, page count, and status badges.
  - Drag-and-drop PDF upload zone supporting files up to 50 MB with indeterminate progress indicator.
  - Authenticated PDF download utilizing authenticated `fetch()` $\rightarrow$ `Blob` $\rightarrow$ `URL.createObjectURL` $\rightarrow$ automatic cleanup.
  - Comprehensive document metadata viewer modal and safe deletion dialog guarded against active index unlinking.
- **Knowledge Base Generation & Pipeline Inspector (`pages/admin/AdminKnowledgePage.tsx`, `pages/admin/AdminGenerationDetailPage.tsx`)**:
  - Authoritative active generation identification strictly bound to `generation.is_active === true`.
  - Generation builder modal supporting custom version tags and optional subset document selection.
  - Detailed stage-by-stage timeline tracking (`INIT` $\rightarrow$ `EXTRACTION` $\rightarrow$ `CHUNKING` $\rightarrow$ `EMBEDDING` $\rightarrow$ `INDEXING` $\rightarrow$ `EVALUATION`) with live progress bars and polling.
  - Single-click atomic promote to ACTIVE and rollback confirmations.
- **Multi-Stage RAG Retrieval Diagnostics Workbench (`pages/admin/AdminRetrievalTestPage.tsx`)**:
  - Live query testing interface with configurable parameters (`top_k: 1..50`, `enable_reranker`, `filter_noise`, `suppress_duplicates`).
  - Stage candidate metrics (Dense count, BM25 count, Fused count, Final count) and latency breakdown chips (`dense_ms`, `bm25_ms`, `fusion_ms`, `rerank_ms`, `total_ms`).
  - Ranked evidence cards with source PDF, page number, similarity scores, and expandable full text.
- **Translation Registry & System Health Probes (`pages/admin/AdminTranslationsPage.tsx`, `pages/admin/AdminSystemPage.tsx`)**:
  - Live NLLB-200 translation engine health check, supported language pairs (`kn` $\leftrightarrow$ `en`), and CC-BY-NC-4.0 licensing notices.
  - Authentic system health telemetry displaying live values from `GET /api/v1/health` (`status`, `profile`, `app_version`, `subsystems.database`).
  - Static architectural summary of the local offline AI stack (Faster-Whisper, ChromaDB, Sentence-Transformers, Cross-Encoder, Ollama, Piper/MMS TTS).

### Fixed
- **Knowledge Base Build Response Serialization (`backend/app/application/knowledge/service.py`)**:
  - Resolved `MissingGreenlet` async SQLAlchemy exception occurring during `POST /api/v1/admin/knowledge/generations/build` response serialization (`GenerationResponse.model_validate`).
  - Added explicit `await self.session.refresh(generation)` following `await self.session.commit()` in `KnowledgeService.build_generation` to reload expired ORM attributes prior to Pydantic validation.
  - Zero API contract changes; status code (`201 Created`) and response schema (`GenerationResponse`) strictly preserved.

### Verified
- **Frontend Test Suite**: **47 / 47 passing Vitest tests (24 tourist tests + 23 admin unit/route/component tests, 100% pass rate)**.
- **Production Build**: Clean Vite production build (`dist/assets/index-*.js`, `dist/assets/index-*.css`) with zero type errors.
- **Live Mutation & E2E Acceptance**: Verified live document upload, duplicate 409 rejection, safe deletion, active generation delete protection (409), controlled generation build, stage inspection, promotion to active, and rollback to original active generation (`ACTIVE_AFTER == ACTIVE_BEFORE`).
- **Backend Test Baseline**: **280 / 280 passing backend tests across all test modules (100% pass rate)**.
- Attained **`CHECKPOINT-P15`**.

### Preserved Project Debt & Known Limitations
- *Phase 14*: Physical browser microphone capture remains unverified in headless automated CI environments.
- *Phase 14*: Kannada font binaries are not bundled; standalone offline rendering relies on OS-level Kannada font fallbacks.
- *Phase 18 Debt*: Whole-system RAM footprint reaches ~7.7 GB on 8 GB development hardware with the full local AI stack loaded.
- *Phase 15 Status*: No new blocking Phase 15 defects.

## [0.14.0] - 2026-09-01 (Phase 14: Premium Tourist Web Application)

### Added
- **Modern Tourist Single Page Application (`frontend/`)**:
  - Built with React 19, Vite 6, Tailwind CSS v4 (`@tailwindcss/vite`), React Router v7, TanStack Query v5, Zustand v5, and Lucide React icons.
  - Complete responsive layout structure with sticky header, collapsible desktop/tablet sidebars, mobile bottom navigation, and accessible dialogs.
- **Karnataka Heritage Design System (`frontend/src/index.css`)**:
  - Curated heritage color palette tokens: Temple Gold (`#D4AF37`), Deep Brown (`#2C1810`), Soapstone Grey (`#4A4A4A`), Ivory (`#FDFBF7`), Belur Night Slate (`#161311`), and Night Card (`#211C1A`).
  - Standalone zero-runtime Google Fonts architecture with locally bundled font fallbacks (`Noto Sans Kannada`, `Cinzel`, `Plus Jakarta Sans`, system-ui).
  - Dark mode synchronization supporting `light`, `dark`, and `system` modes with `localStorage` persistence.
- **Authoritative Grounded Chat Experience (`frontend/src/components/chat/`)**:
  - Full bidirectional chat timeline supporting both English and Kannada.
  - Server-Sent Events (SSE) streaming with live token buffering, chunk boundary normalization, pulsing gold cursor, and client abort support (`useChatStream.ts`, `sseClient.ts`).
  - Strict citation rendering parsing inline markers `[1]`, `[2]` into interactive `<CitationPill />` elements linking to `<CitationDrawer />` displaying exact source PDF filename, page number, and section header.
  - Contextual suggestion chips, bilingual welcome state cards, copy-to-clipboard actions, and ungrounded fallback visual cues.
- **Bilingual Voice Input & Speech Synthesis (`frontend/src/components/voice/`)**:
  - Immediate Non-Streaming Voice Question Mode: dynamic MIME detection (`.webm`, `.ogg`, `.mp4`, `.wav`), recording duration timer, and real-time 5-bar frequency visualizer (`AudioWaveform.tsx`, `useVoiceRecorder.ts`).
  - Honest latency progress indicator (`Transcribing speech...` $\rightarrow$ `Thinking & retrieving facts...` $\rightarrow$ complete grounded answer).
  - On-demand TTS player (`<TTSPlayerButton />`, `useAudioPlayer.ts`) with single `HTMLAudioElement` lifecycle management and automatic `Blob URL` cleanup via `URL.revokeObjectURL`.
- **Interactive Heritage Map & Destination Catalog (`frontend/src/components/map/`, `frontend/src/components/destinations/`)**:
  - Leaflet + OpenStreetMap integration with configurable tile URLs, custom Hoysala Kalasha SVG pin markers, and graceful offline fallback banner.
  - Source-grounded 6-destination catalog (Belur, Halebidu, Hampi, Badami, Pattadakal, Aihole) with dynasty tags, era metadata, and local SVG vector artwork.
  - Detailed monument exploration page (`/explore/:slug`) and about page (`/about`).
- **Comprehensive Frontend Vitest Suite (`frontend/tests/`)**:
  - 24 passing unit and component tests verifying API client, SSE stream processing, Zustand store, destination bounds, and React Testing Library UI interactions.

### Verified
- **Frontend Test Suite**: **24 / 24 passing Vitest tests (100% pass rate)**.
- **Backend Test Baseline**: **280 / 280 passing backend tests across all test modules (100% pass rate)**.
- **Production Build**: Clean Vite production build (`dist/assets/index-*.js`, `dist/assets/index-*.css`) with zero type errors.
- Attained **`CHECKPOINT-P14`**.

## [0.13.0] - 2026-09-01 (Phase 13: Unified FastAPI Client Gateway / Streaming Integration)

### Added
- **Unified Public Tourist Route Inventory (`app/api/v1/endpoints/tourist.py`, `app/api/v1/endpoints/voice.py`, `app/api/v1/router.py`)**:
  - Standardized all 8 public tourist endpoints under `/api/v1/tourist/*`:
    - `POST /api/v1/tourist/sessions`: Anonymous session initialization with language specification.
    - `GET /api/v1/tourist/sessions/{session_uuid}`: Paginated session conversation history.
    - `DELETE /api/v1/tourist/sessions/{session_uuid}`: Privacy-safe session history clearing.
    - `POST /api/v1/tourist/chat`: Standard synchronous grounded conversation turn.
    - `POST /api/v1/tourist/chat/stream`: Real-time Server-Sent Events (SSE) token streaming.
    - `POST /api/v1/tourist/voice/transcribe`: Isolated audio transcription endpoint.
    - `POST /api/v1/tourist/chat/voice`: Single-request voice speech input $\rightarrow$ STT $\rightarrow$ grounded chat response.
    - `POST /api/v1/tourist/voice/synthesize`: Restricted assistant message speech synthesis handoff.
- **Single Authoritative Conversation Engine (`app/application/conversation/service.py`)**:
  - Direct reuse of `ConversationService` across both synchronous chat, streaming chat, and voice chat. Zero duplicate engines or duplicate STT invocations.
- **Server-Sent Events (SSE) Protocol Hardening (`app/application/conversation/service.py`, `app/api/v1/endpoints/tourist.py`)**:
  - Frozen event sequence: `token` (`data: {"text": "..."}`) $\rightarrow$ `citations` (`data: {"citations": [...]}`) $\rightarrow$ `done` (`data: {"session_uuid": "...", "message_id": "...", "grounded": true, "language": "en", "duration_ms": 1200}`).
  - Pre-stream validation: Invalid session UUID or malformed payload returns standard `HTTP 404 / 422 JSON error envelopes` before streaming begins.
  - Mid-stream runtime errors: Emits terminal `event: error` (`data: {"code": "SERVICE_UNAVAILABLE", "message": "Response generation became unavailable.", "request_id": "..."}`) and terminates stream immediately without `citations` or `done`.
  - Persistence safety: Only fully completed streams commit USER and ASSISTANT messages to MySQL; partial or interrupted streams leave 0 corrupt records.
- **CORS Audio Header Exposure (`app/main.py`)**:
  - Configured `CORSMiddleware` `expose_headers` to expose `X-Audio-Duration-Seconds`, `X-Audio-Sample-Rate`, `X-Audio-Channels`, `X-Language`.
- **Public Citation Contract & Alignment (`app/application/conversation/citation_formatter.py`)**:
  - Implemented deterministic `filter_authoritative_citations` ensuring the public `citations` array emitted in `ChatTurnResponse` and SSE `citations` events contains ONLY citation labels actually referenced in the visible answer text.
  - Internal retrieval diagnostics retain full candidate evidence count (`retrieval.evidence_count`), preserving backward compatibility and deep analysis without coupling the frontend.
  - Enforced 100% parity across streaming and non-streaming responses.
- **Comprehensive Gateway Test Suite (`tests/test_api_gateway.py`)**:
  - Added 32 comprehensive tests covering route inventory, session lifecycle, SSE ordering, exact token payload keys (`"text"`), citation label alignment, parity, pre-stream and mid-stream error handling, TTS handoff, audio validation, CORS headers, and OpenAPI schema validation.

### Verified
- **Regression Test Baseline**: **280 / 280 tests passing across all 23 test files (100% pass rate: 248 baseline + 32 Phase 13 tests)**.
- **Generated-WAV Audio $\rightarrow$ STT $\rightarrow$ RAG $\rightarrow$ TTS Integration Benchmark (`scratch/benchmark_phase13_voice_roundtrip.py`)**:
  - Real input speech WAV (4.68s, 22.05 kHz) $\rightarrow$ Faster-Whisper STT (`Balurchenik Shava Temple in 1117 CE.`, probability 1.000) $\rightarrow$ Hybrid RAG (15 candidates, top score 8.8659) $\rightarrow$ GroundingGuard (`grounded=True`) $\rightarrow$ Ollama (`phi3:mini`) grounded answer with 3 citations $\rightarrow$ Authoritative MySQL persistence (`assistant_message_id`) $\rightarrow$ Restricted Piper TTS synthesis handoff $\rightarrow$ Playable 22.05 kHz Mono WAV (27.28s playback, 601,600 frames).
  - Scope-accurate memory profiling:
    - *Process Working Set*: 448.09 MB
    - *Process Private Bytes*: 2,800.91 MB
    - *Whole-System Used RAM*: 7.71 / 7.74 GB (99%)
    - *High-Priority Phase 18 Debt*: High memory pressure on 8 GB laptop host when full AI stack is active.
- Attained **`CHECKPOINT-P13`**.

---

## [0.12.0] - 2026-08-30 (Phase 12: Text-To-Speech Synthesis / Piper TTS & Meta MMS-TTS)

### Added
- **TTS Domain Port & Composite Infrastructure Providers (`app/domain/ports/tts.py`, `app/infrastructure/tts/`)**:
  - `ITTSProvider` abstract domain port declaring `synthesize(text, language) -> AudioSynthesisResult`, `check_health() -> bool`, and `get_supported_languages() -> list[str]`.
  - `AudioSynthesisResult` dataclass (`audio_bytes`, `sample_rate`, `channels`, `sample_width`, `duration_seconds`, `mime_type`).
  - `PiperTTSProvider` using `piper-tts==1.7.0` and ONNX model `en_US-lessac-medium` on CPU (22,050 Hz Mono 16-bit PCM WAV, RTF 0.129x = **7.8x real-time speed**, +124.71 MB RAM, MIT engine license / Lessac Blizzard dataset terms).
  - `MMSTTSProvider` using `facebook/mms-tts-kan` via Hugging Face `transformers.VitsModel` on CPU (16,000 Hz Mono 16-bit PCM WAV, RTF 0.658x = **1.5x real-time speed**, +170.57 MB RAM, CC-BY-NC-4.0 approved development offline Kannada TTS provider).
  - `CompositeTTSProvider` routing `en` -> Piper and `kn` -> MMS-TTS with thread-safe lazy model initialization and non-blocking `asyncio.to_thread` execution.
- **Restricted Synthesis Contract & Voice Security (`app/api/v1/endpoints/voice.py`, `app/application/speech/tts_service.py`)**:
  - `POST /api/v1/tourist/voice/synthesize`: Restricted endpoint requiring `session_uuid` and `assistant_message_id`. Resolves tourist session, verifies message belongs to session, validates `sender_type=ASSISTANT`, extracts authoritative language, and synthesizes that exact approved answer.
  - Raw unverified text synthesis is strictly prevented.
  - Custom response headers: `X-Audio-Duration-Seconds`, `X-Audio-Sample-Rate`, `X-Audio-Channels`, `X-Language`.
- **Pure Memory-First Audio Streaming & Wave Serialization**:
  - Direct in-memory wave serialization via Python stdlib `wave` and `io.BytesIO`. Zero transient audio files written to disk.
- **Deterministic Speech Text Sanitization (`app/application/speech/tts_service.py`)**:
  - `SpeechTextSanitizer`: Regex-based stripping of citation markers (`\[\d+\]`), markdown formatting (`**`, `*`, `_`, `#`, `>`), and URLs for audio rendering without altering database text or citations.
  - Complete Kannada Unicode and heritage proper noun preservation.
- **Voice Registry Seed & System Models (`app/infrastructure/db/models/system.py`, `app/infrastructure/db/seed.py`)**:
  - Added `MMS_TTS` to `VoiceProvider` enum and seeded approved voices `piper_en_lessac_medium` (22,050 Hz) and `mms_kn_vits` (16,000 Hz).
- **Automated Test Suite (`tests/test_tts.py`)**:
  - Added 32 comprehensive tests covering sanitization, providers, language routing, service authorization, API endpoints, seed verification, and live end-to-end conversation-to-speech integration (Total: **248 passing tests, 100% pass rate**).

### Verified
- **Heritage Quality Benchmark (20 Historical Sentences)**:
  - English (Piper TTS): **10/10 synthesized (100%)**, Avg Latency: 860.5 ms, Avg RTF: 0.129x (**7.8x real-time speed**), 22,050 Hz.
  - Kannada (MMS-TTS): **10/10 synthesized (100%)**, Avg Latency: 6,727.8 ms, Avg RTF: 0.658x (**1.5x real-time speed**), 16,000 Hz.
  - Number/Date Phonemization (*1117 CE*, *733 CE*, *12th century*, *ಕ್ರಿ.ಶ. 1117*, *12ನೇ ಶತಮಾನ*): 100% playable WAVs.
  - Exact Bilingual Fallbacks: 100% playable audio for standardized grounding fallbacks.
- **Combined Full-Stack Memory Profile (`scratch/benchmark_phase12_tts.py`)**:
  - Isolated TTS RAM: **+295.29 MB Working Set (+366.58 MB Private)**
  - Peak Combined Stack (FastAPI + ChromaDB + CrossEncoder + NLLB + Whisper + Ollama + Piper + MMS): **1,853.20 MB Working Set (~1.85 GB) / 4,254.25 MB Private (~4.25 GB)**.
- **Full-Stack Multilingual Voice Round-Trip Verified**:
  - Kannada Question -> NLLB -> English RAG -> Grounded Answer `[1]` -> NLLB -> Speech Sanitizer -> MMS-TTS -> 16 kHz WAV.
- 100% test pass rate across entire regression test suite (248/248 tests passing).
- Attained **`CHECKPOINT-P12`**.

---

## [0.11.0] - 2026-08-29 (Phase 11: Multilingual Translation Hardening / Meta NLLB-200 600M)

### Added
- **Translation Domain Port & NLLB Infrastructure Provider (`app/domain/ports/translation.py`, `app/infrastructure/translation/nllb.py`)**:
  - `ITranslationProvider` abstract domain port declaring `translate_text`, `get_supported_languages`, and `check_health`.
  - `NLLBTranslationProvider` concrete infrastructure adapter using Hugging Face Transformers running `facebook/nllb-200-distilled-600M` (CC-BY-NC-4.0 approved development offline translation provider) on CPU with process-level singleton caching and non-blocking `asyncio.to_thread` execution.
- **Direction-Aware Canonical Heritage Entity Restoration & Verification (`app/application/translation/service.py`)**:
  - Pre-translation preparation mapping 12+ core Kannada proper nouns (*ಬೇಲೂರು*, *ಚೆನ್ನಕೇಶವ*, *ಹಳೇಬೀಡು*, *ಹೊಯ್ಸಳೇಶ್ವರ*, *ಬಾದಾಮಿ*, *ಐಹೊಳೆ*, *ಪಟ್ಟದಕಲ್ಲು*, *ಹಂಪಿ*, *ವಿರೂಪಾಕ್ಷ*, *ವಿಠ್ಠಲ*, *ವಿಜಯನಗರ*, *ವಿಷ್ಣುವರ್ಧನ*) into their canonical English forms (*Belur*, *Chennakeshava*, *Halebidu*, *Hoysaleswara*, *Badami*, *Aihole*, *Pattadakal*, *Hampi*, *Virupaksha*, *Vittala*, *Vijayanagara*, *Vishnuvardhana*) before NLLB translation.
  - Post-translation entity preservation verification guaranteeing all proper nouns exist in the final English retrieval query.
  - Strict inline citation placeholder integrity (`[1]`, `[2]`) with safe English fallback upon citation distortion.
- **Bilingual RAG Query & Response Translation (`app/application/conversation/service.py`)**:
  - Kannada search queries translated into English for Phase 7 hybrid dense/BM25/Cross-Encoder retrieval (`translate_retrieval_query`). English search queries bypass translation with zero overhead.
  - Grounded answers translated to Kannada (`translate_response`) with visible citation markers (`[1]`, `[2]`) preserved.
  - Authoritative metadata (`chunk_id`, `document_id`, `generation_id`, `source_filename`, `page_number`) strictly isolated on the backend and NEVER passed to the translation model.
  - Original tourist query persisted verbatim in `ChatMessage` (`sender_type=USER`).
  - Standardized exact fallbacks (`"Information is not available in the knowledge base."` $\leftrightarrow$ `"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`) returned with zero translation overhead and zero LLM calls.
- **Admin Translation Registry Endpoint (`app/api/v1/endpoints/translations.py`)**:
  - `GET /api/v1/admin/translations`: Authenticated endpoint exposing active translation engine metadata (`nllb`, `nllb-200-distilled-600M`, CC-BY-NC-4.0 license, supported languages `kn`, `en`, ISO mappings `kan_Knda`, `eng_Latn`, offline model readiness).
- **Automated Test Suite (`tests/test_translation.py`)**:
  - Added 37 comprehensive tests covering provider initialization, unsupported language rejection, empty input, identical language bypass, token masking/unmasking, date/entity preservation, fail-safe placeholders, deterministic fallbacks, English bypass, conversation turns, streaming, admin endpoints, and security invariants (Total: **216 passing tests, 100% pass rate**).

### Verified
- **Target Kannada Retrieval Verification (`scratch/verify_phase11_hardening.py`)**:
  - Query: `"ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?"`
  - Corrected English retrieval query: `"Who built the Belur Chennakeshava Temple?"`
  - Proper noun retention: `Belur` = True, `Chennakeshava` = True (100% preserved)
  - Top retrieval score: `+9.3019` vs `-7.4852` untranslated (Delta: **+16.7871**)
  - Retrieved document: `Belur_Halebidu_Hoysala_Guide.pdf` (Page 2)
  - Grounding result: `is_grounded=True` with Hoysala King Vishnuvardhana `[1]`
  - Grounded Kannada answer: Formulated in Kannada with citation `[1]` intact.
- **Multi-Document Active Knowledge Corpus Benchmark (5 documents: Belur/Halebidu, Badami, Aihole, Pattadakal, Hampi)**:
  - 15 Clean Supported Queries: **Hit@1 = 15/15 (100.0%)**, **Recall@5 = 15/15 (100.0%)**, Representative E2E Grounded = 5/5 (100.0%)
  - 5 Unsupported Safety Queries: **Fallback Accuracy = 5/5 (100.0%)**, 0 citations, 0 Ollama calls (`"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`)
  - Proper-Noun Battery: **12/12 (100.0%)** detected and canonicalized
  - Real Faster-Whisper Kannada voice turn: `grounded=True`, citations preserved
  - 100% test pass rate across entire test suite (216/216 tests passing).
- Attained **`CHECKPOINT-P11`**.

---

## [0.10.0] - 2026-08-29 (Phase 10: Speech-To-Text Engine / Faster-Whisper)

### Added
- **Speech-To-Text Domain Port & Faster-Whisper Provider (`app/domain/ports/stt.py`, `app/infrastructure/stt/faster_whisper.py`)**:
  - `ISpeechToTextProvider` abstract domain port declaring `transcribe_audio` and `check_health` contracts.
  - `FasterWhisperProvider` infrastructure adapter using CTranslate2 running quantized `base` model (`int8` compute on CPU) with process-level singleton caching and non-blocking `asyncio.to_thread` execution.
- **Deep Audio Validation & Container Decoding (`app/infrastructure/stt/audio_validator.py`)**:
  - Multi-layer security pipeline: size verification ($\le 15$ MB), MIME/extension allowlist (`.wav`, `.mp3`, `.ogg`, `.webm`, `.m4a`, `.mp4`), magic byte signatures (RIFF/WAVE, ID3/sync, OggS, EBML, ftyp), and PyAV deep container decoding.
  - Verifies decodable audio streams exist, checks duration limits ($\le 60.0$ s), and rejects video-only, silent, or corrupt containers.
- **Transient Audio Privacy & Guaranteed Cleanup**:
  - Temporary audio files written to `storage/temp_audio` are validated, transcribed, and deleted in guaranteed `finally` context blocks across all execution and exception paths. No raw voice recordings are stored in MySQL or retained on disk.
- **Public Tourist Voice Endpoints (`app/api/v1/endpoints/voice.py`)**:
  - `POST /api/v1/tourist/voice/transcribe`: Unauthenticated multipart audio upload returning structured `TranscriptionResponse`.
  - `POST /api/v1/tourist/chat/voice`: Voice-to-chat integration piping speech transcript directly into `ConversationService.process_turn()` returning combined transcript, grounded answer, and citations.
- **Automated Test Suite (`tests/test_stt.py`)**: Added 20 unit and integration tests covering provider initialization, valid audio decoding across formats, English/Kannada speech, error handling, temp cleanup, anonymous tourist access, singleton model reuse, schema validation, and offline readiness (Total: **179 passing tests, 100% pass rate**).

### Verified
- **25-Clip Multilingual Faster-Whisper Benchmark (`scratch/benchmark_phase10_stt.py`)**:
  - **Successful Inferences**: **25/25 (100.0%)**.
  - **VAD Silence / Noise Rejection**: **3/3 clips (100.0%)**.
  - **Cold Model-Load Latency**: **1510.96 ms**.
  - **Average Audio Decode Latency**: **23.35 ms**.
  - **Average Warm Transcription Latency**: **1344.42 ms** (~1.34s).
  - **Average Real-Time Factor (RTF)**: **0.43x** (2.3x faster than real-time on CPU).
- Attained **`CHECKPOINT-P10`**.

---

## [0.9.0] - 2026-08-27 (Phase 9: Ollama LLM Integration, Grounded Prompting, Context Compression & Streaming)

### Added
- **LLM Domain Port & Ollama Infrastructure Provider (`app/domain/ports/llm.py`, `app/infrastructure/llm/ollama.py`)**:
  - `ILLMProvider` abstract domain port declaring `generate_text`, `generate_stream`, and `check_health`.
  - `OllamaLLMProvider` native async client using `httpx.AsyncClient` targeting local Ollama instance (`http://127.0.0.1:11434`).
  - Supports configurable local models (`phi3:mini`, `mistral:7b`, `llama3.1:8b`) with deterministic low temperature (`0.1`) and concise token budgeting (`num_predict=128`).
- **Prompt Isolation & Anti-Injection Architecture (`app/application/rag/prompt_builder.py`)**:
  - Strict structural separation between System Policy, Verified Evidence (`=== EVIDENCE START ===` / `=== EVIDENCE END ===`), and User Query.
  - Explicit system directives enforcing evidence-only factual answering and treating retrieved documents as untrusted raw data.
  - Context compression & deduplication budgeting (`OLLAMA_MAX_CONTEXT_CHARS=2000`).
- **Exact Fallback Enforcement & Non-Streaming Validation (`app/application/conversation/service.py`)**:
  - Strict `GroundingGuard` evaluation: ungrounded queries ($< -6.0$) **bypass Ollama completely** and return exact localized fallback with zero citations (`"Information is not available in the knowledge base."` / `"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`).
  - Complete validation of non-streaming responses, sanitizing citation markers (`[1]`, `[2]`), stripping hallucinated references, and attaching authoritative MySQL metadata (`chunk_id`, `document_id`, `generation_id`, `page_number`, `source_filename`).
- **Graceful Extractive Degradation**:
  - Fallback to verified Phase 8 extractive source evidence if the local Ollama daemon is offline or times out.
- **Server-Sent Events (SSE) Token Streaming (`POST /api/v1/tourist/chat/stream`)**:
  - Real-time token streaming via FastAPI `StreamingResponse` emitting `token`, `citations`, and `done` events.
  - Evaluates `GroundingGuard` before streaming starts; persists final turn in MySQL only upon successful stream completion.
- **Automated Test Suite (`tests/test_llm.py`)**: Added 17 unit and integration tests covering mock provider, injection defense, timeouts, connection errors, citation sanitization, streaming, and ungrounded bypass (Total: **159 passing tests, 100% pass rate**).

### Verified
- **30-Turn Real Ollama Grounded Generation Benchmark (`scratch/benchmark_phase9_llm.py`)**:
  - **Grounding Classification Accuracy**: **100.00% (30/30)**.
  - **Unsupported Exact Fallback Rate**: **100.00% (5/5)**.
  - **Unsupported Zero Citation Rate**: **100.00% (5/5)**.
  - **Citation Provenance Precision (MySQL)**: **100.00% (25/25)**.
  - **Hallucination Count**: **0**.
- Attained **`CHECKPOINT-P9`**.

---

## [0.8.0] - 2026-08-27 (Phase 8: Multilingual Conversation Engine)

### Added
- **Zero-Auth Anonymous Tourist Session Management (`app/application/conversation/service.py`)**:
  - `POST /api/v1/tourist/sessions`: Generates persistent UUID-identified sessions in MySQL `chat_sessions` table with preferred language code. Zero tourist login, signup, or JWT tokens required.
  - `GET /api/v1/tourist/sessions/{session_uuid}`: Returns chronological chat history with message timestamps and metadata.
  - `DELETE /api/v1/tourist/sessions/{session_uuid}`: Cascading privacy deletion of session messages and conversation records.
- **Multilingual Unicode Script Detection (`app/application/conversation/language_detector.py`)**:
  - Deterministic Unicode code-point script inspection for pure English (`en`), pure Kannada (`kn`), and script-mixed (`kn-mixed`) tourist queries without external dependencies.
  - Documented Romanized Kannada limitation as a future Phase 11 item.
- **Bounded Multi-Turn Context & Follow-Up Resolution (`app/application/conversation/context_builder.py`)**:
  - Strictly bounded 5-turn conversation windowing (`CONVERSATION_MAX_TURNS=5`).
  - Reverse-chronological heritage entity and proper noun extraction (`Belur Chennakeshava Temple`, `Badami Caves`, `Halebidu`, `Aihole`, etc.).
  - Follow-up query rewriting for referential pronouns (`it`, `its`, `this monument`, `there`, `here`) while preserving original user query in database verbatim.
- **Strict Grounding Guard & Bilingual Fallbacks (`app/application/conversation/grounding_guard.py`)**:
  - Enforces empirical calibrated Cross-Encoder threshold (`CONVERSATION_GROUNDING_MIN_SCORE = -6.0`).
  - Verified active generation requirement; returns standardized fallbacks when evidence is absent:
    - English: `"Information is not available in the knowledge base."`
    - Kannada: `"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`
  - Yields zero citations when ungrounded.
- **Extractive Source Evidence & Citation Formatter (`app/application/conversation/citation_formatter.py`)**:
  - Compiles verbatim ranked source passages with inline bracketed citation markers (`[1]`, `[2]`).
  - Populates structured citation objects containing `chunk_id`, `source_filename`, `page_number`, and `generation_id` without premature synthetic text generation.
- **Public Canonical Tourist API (`app/api/v1/endpoints/tourist.py`)**:
  - `POST /api/v1/tourist/chat`: Validates session UUID, checks message length ($\le 1000$ chars), executes bounded context resolution, triggers Phase 7 `RAGRetrievalService`, applies grounding guard, persists user and assistant messages, and returns structured response.
- **Automated Test Suite (`tests/`)**: Added 24 new unit and integration tests across `test_conversation.py` and `test_tourist_api.py` (Total test count: 137 passing tests, 100% pass rate).

### Verified
- Real 30-turn source-grounded conversation benchmark across 8 multi-turn sessions:
  - **Language Detection Accuracy**: **100.00%** (30/30).
  - **Follow-Up Context Resolution Accuracy**: **100.00%** (10/10).
  - **Grounding Decision Accuracy**: **83.33%** (25/30).
  - **Citation Page Provenance Accuracy**: **81.48%** (22/27 grounded turns).
  - **Unsupported Fallback Accuracy**: **100.00%** (3/3 unsupported queries).
  - **Measured Steady-State Warm Turn Latency**: **454.83 ms**.
- Attained **`CHECKPOINT-P8`**.

---

## [0.7.0] - 2026-08-27 (Phase 7: RAG Retrieval Optimization — Dense + BM25 + RRF + Cross-Encoder Re-ranking)

### Added
- **Query Normalization & IAST Diacritic Mapping (`app/application/rag/normalization.py`)**: Unicode NFC normalization, specialized IAST diacritic mapping for Indian heritage terms (e.g. `Chennakēśava` -> `Chennakeshava`, `Hoysaḷa` -> `Hoysala`, `Kṛṣṇa` -> `Krishna`) while strictly preserving Indic/Kannada script characters and original source text for citations.
- **Sparse Lexical BM25 Retrieval Engine (`app/application/rag/bm25.py`)**: Okapi BM25 (`rank-bm25==0.2.2`) sparse keyword retriever indexing all semantic chunks of the active knowledge generation from MySQL `document_chunks` with thread-safe process-level index caching.
- **Dense Vector ChromaDB Retriever (`app/application/rag/dense.py`)**: Queries the isolated ChromaDB collection of the active knowledge generation using normalized queries and cosine similarity distance.
- **Reciprocal Rank Fusion (RRF k=60) (`app/application/rag/fusion.py`)**: Standard rank-based score fusion combining dense vector and sparse BM25 candidate lists into a unified ranked candidate set with constant k=60.
- **Cross-Encoder Re-ranking Engine (`app/application/rag/reranker.py`)**: Re-ranking using `cross-encoder/ms-marco-MiniLM-L-6-v2` loaded once as a process singleton. Evaluates joint query-document cross-attention and scores candidates with offline Hugging Face cache reuse.
- **Noise, Bibliography & Duplicate Filtering (`app/application/rag/filters.py`)**: Suppresses bibliography, reference list, and table-of-contents structural noise chunks (unless explicitly requested), and removes identical chunk IDs and near-duplicate passages sharing >= 80% token overlap on the same page.
- **RAG Retrieval Orchestrator Service (`app/application/rag/service.py`)**: Coordinates the multi-stage hybrid retrieval pipeline, enforces active generation lookup from MySQL, accurately measures stage latencies (`dense_ms`, `bm25_ms`, `fusion_ms`, `rerank_ms`, `total_ms`), and returns rich telemetry.
- **Admin Retrieval Diagnostic Endpoints (`app/api/v1/endpoints/diagnostics.py`)**:
  - `POST /api/v1/admin/knowledge/retrieval-test`
  - `POST /api/v1/admin/diagnostics/retrieve` (Alias)
- **Automated Test Suite (`tests/`)**: Added 9 new unit and integration tests across `test_retrieval.py` and `test_diagnostics_api.py` (Total test count: 113 passing tests, 100% pass rate).

### Verified
- Expanded 24-query real source-grounded heritage benchmark executed across 12 distinct tourist query categories against real 5-document, 12-page, 22-chunk active Karnataka heritage corpus in MySQL 8.0 `karnataka_guide` and persistent ChromaDB collection (`v_20260827_043028_6ee08b`):
  - **Hit@1 Rate**: **95.83%** (23/24 queries at Rank 1)
  - **Recall@5**: **100.00%** (24/24 queries in Top 5)
  - **Precision@5**: **23.33%**
  - **Mean Reciprocal Rank (MRR)**: **0.9792**
  - **Bibliography Intrusion Rate**: **0.00%** (0 leaks)
  - **Duplicate Result Rate**: **0.00%** (0 duplicates)
  - **Measured Steady-State Warm Latency Profile**: Dense = 82.47 ms, BM25 = 0.95 ms, Fusion = 0.19 ms, Cross-Encoder Re-rank = 793.40 ms (15 candidate pairs on CPU) $\rightarrow$ **Average Total Warm Latency = 880.16 ms**.
- 100% test pass rate across entire test suite (113/113 tests passing in 31.11s).
- Attained **`CHECKPOINT-P7`**.

---

## [0.6.0] - 2026-08-27 (Phase 6: Knowledge Base Pipeline, Parsing, Embeddings & ChromaDB Foundation)

### Added
- **PyMuPDF Document Text Extraction (`app/application/knowledge/extractor.py`)**: Robust multi-page PDF text extraction with PyMuPDF (`fitz`), Unicode NFC normalization, whitespace cleaning, 1-indexed page provenance tracking, and empty-page detection.
- **Semantic Text Chunking Engine (`app/application/knowledge/chunker.py`)**: Paragraph- and sentence-boundary aware chunker targeting ~800 characters with 120 character overlap. Preserves exact page numbers, chunk sequence indices, section headers, character offsets, and estimated token counts in chunk metadata.
- **Process-Singleton SentenceTransformer Embedding Generator (`app/application/knowledge/embeddings.py`)**: Thread-safe process-level singleton loading `all-MiniLM-L6-v2`. Computes normalized 384-dimensional vector embeddings in configurable batches with strict dimension validation and offline cache reuse.
- **Partitioned Persistent ChromaDB Storage (`app/application/knowledge/vector_store.py`)**: Isolated collection per knowledge generation (`gen_<sanitized_uuid>`) stored persistently under `storage/chroma`. Supports batch indexing with cosine similarity distance metric, vector count verification, and clean collection deletion.
- **Knowledge Base Orchestration Service (`app/application/knowledge/service.py`)**:
  - Executes multi-stage pipeline: `INIT` -> `EXTRACTION` -> `CHUNKING` -> `EMBEDDING` -> `INDEXING` -> `EVALUATION`.
  - Records granular stage progress in MySQL `generation_status`.
  - Persists semantic chunks in MySQL `document_chunks` and vector references in `embeddings`.
  - Strict evaluation gate: verifies document count, chunk count, MySQL embedding count, ChromaDB collection vector count, and 384 dimensions before transitioning generation to `VALIDATED`.
  - Atomic Promotion: Sets promoted generation to `ACTIVE` (`is_active=True`, status `ACTIVE`) and atomically transitions any existing active generation to `ARCHIVED` (`is_active=False`).
  - Instant One-Click Rollback: Verifies Chroma collection integrity and atomically restores a target generation to `ACTIVE` while setting the deactivated generation to `ARCHIVED`.
- **Active Document Deletion Guard (`app/application/documents/service.py`)**: Blocks deletion of source PDF documents referenced by an `ACTIVE` knowledge generation with HTTP 409 Conflict.
- **Admin Knowledge Base Endpoints (`app/api/v1/endpoints/knowledge.py`)**:
  - `POST /api/v1/admin/knowledge/generations/build` (Trigger generation build, restricted to `SUPER_ADMIN`, `SITE_CURATOR`)
  - `GET /api/v1/admin/knowledge/generations` (List generations with pagination, all admin roles)
  - `GET /api/v1/admin/knowledge/generations/{id}` (View generation details and stage history, all admin roles)
  - `POST /api/v1/admin/knowledge/generations/{id}/promote` (Promote generation to ACTIVE, restricted to `SUPER_ADMIN`, `SITE_CURATOR`)
  - `POST /api/v1/admin/knowledge/generations/{id}/rollback` (Rollback to generation, restricted to `SUPER_ADMIN`, `SITE_CURATOR`)
- **Security Audit Logging (`app/application/knowledge/service.py`)**: Records `KNOWLEDGE_BUILD_STARTED`, `KNOWLEDGE_BUILD_COMPLETED`, `KNOWLEDGE_PROMOTED`, and `KNOWLEDGE_ROLLBACK` in MySQL `audit_logs`.
- **Automated Test Suite (`tests/`)**: Added 15 new tests covering PDF extraction, semantic chunking, embeddings, Chroma store isolation, pipeline stages, promotion, rollback, active document protection, and RBAC (Total test count: 104 passing tests, 100% pass rate).

### Verified
- Real MySQL 8.0 & ChromaDB end-to-end multi-page tourism PDF parsing, 384d embedding generation, Chroma indexing, semantic search queries, atomic promotion, active document deletion protection (409 Conflict), and instant rollback verified with `scratch/verify_phase6_real_pipeline.py`.
- 100% test pass rate (104/104 tests passing).
- Attained **`CHECKPOINT-P6`**.

---

## [0.5.0] - 2026-08-26 (Phase 5: Secure PDF Document Management)

### Added
- **Multi-Layer PDF Validation (`app/application/documents/storage.py`)**: Enforces file presence, `.pdf` extension, MIME type verification, `%PDF` magic byte header checks, maximum size validation (HTTP 413 on files $> 50\text{MB}$), non-empty checks, and incremental SHA-256 calculation.
- **Secure UUID-Based Storage Engine (`app/application/documents/storage.py`)**: Stores uploaded PDFs outside source code in `storage/documents/<uuid>.pdf` resolved from a stable application base directory, strictly preventing path traversal attacks.
- **Duplicate Document Detection (`app/application/documents/service.py`)**: Rejects duplicate PDF uploads matching existing SHA-256 hashes with HTTP 409 Conflict and logs audit events.
- **Atomic Upload & Failure-Safe Deletion (`app/application/documents/service.py`)**: Unlinks orphan files on database insertion failures; commits database record deletion before unlinking physical files to ensure database consistency.
- **Document Management Endpoints (`app/api/v1/endpoints/documents.py`)**:
  - `POST /api/v1/admin/documents` (Upload PDF, restricted to `SUPER_ADMIN`, `SITE_CURATOR`)
  - `GET /api/v1/admin/documents` (List documents with pagination, all admin roles)
  - `GET /api/v1/admin/documents/{id}` (View document metadata, all admin roles)
  - `GET /api/v1/admin/documents/{id}/download` (Download physical PDF file, all admin roles)
  - `DELETE /api/v1/admin/documents/{id}` (Safe document deletion, restricted to `SUPER_ADMIN`, `SITE_CURATOR`)
- **Security Audit Logging (`app/application/documents/service.py`)**: Persists `DOCUMENT_UPLOADED`, `DOCUMENT_DOWNLOADED`, `DOCUMENT_DELETED`, and `DOCUMENT_UPLOAD_DUPLICATE` events in `audit_logs`.
- **Pre-Phase-5 Hardening**: Restricted `/api/v1/admin/auth/test/*` demonstrator routes to `APP_PROFILE=dev` only.
- **Document Management Test Suite (`tests/`)**: Added 18 unit and integration tests across validation, storage security, API routes, RBAC, and failure handling (Total test count: 89 passing tests).

### Verified
- Real MySQL 8.0 & real filesystem end-to-end upload, duplicate rejection, download byte verification, and safe deletion verified against local instance `karnataka_guide`.
- 100% test pass rate (89/89 tests passing).
- Attained **`CHECKPOINT-P5`**.

---

## [0.4.0] - 2026-08-26 (Phase 4: Admin Authentication & RBAC)

### Added
- **Argon2id Password Security (`app/core/security.py`)**: Memory-hard password hashing and verification using `argon2-cffi` ($t=3, m=65536, p=4$).
- **JWT Authentication Engine (`app/core/security.py`)**: RFC 7519 PyJWT token management (`HS256`), issuing 60-minute access tokens and 7-day refresh tokens with cryptographic `jti` tracking.
- **Refresh Token Rotation & Reuse Detection (`app/application/auth/service.py`)**: Rotates refresh tokens on use, invalidates previous tokens, detects token reuse/replay attacks via the existing `audit_logs` table.
- **Role-Based Access Control (`app/application/auth/dependencies.py`)**: Declarative FastAPI authorization guards (`require_role`).
- **Authentication Endpoints (`app/api/v1/endpoints/auth.py`)**: `/api/v1/admin/auth/*` endpoints (`/login`, `/refresh`, `/logout`, `/me`).
- **Super Admin Bootstrap Utility (`app/infrastructure/db/bootstrap_admin.py`)**: Explicit, idempotent CLI/module bootstrap.

---

## [0.3.0] - 2026-08-26 (Phase 3: MySQL Persistence Foundation & Alembic Migrations)

### Added
- **Async MySQL Connectivity (`app/infrastructure/db/session.py`)**: Asynchronous SQLAlchemy 2.x engine using `asyncmy`.
- **Complete 16-Table ORM Models (`app/infrastructure/db/models/`)**: Declarative models for all 16 approved system tables.
- **Alembic Async Migrations (`alembic/`)**: Baseline migration `0001_initial_schema.py`.
- **Database Health Probe (`app/infrastructure/db/health.py`, `app/main.py`)**: Integrated live non-blocking `SELECT 1` ping into `/ready`.
- **Idempotent Registry Bootstrap (`app/infrastructure/db/seed.py`)**: Default models, voices, translations, and settings.

---

## [0.2.0] - 2026-08-26 (Phase 2: Backend Foundation & Core Infrastructure)

### Added
- **FastAPI Application Factory (`app/main.py`)**: Asynchronous core with lifespan management, CORS, structured logging, and typed exceptions.
- **Pydantic v2 Settings (`app/core/config.py`)**: Settings supporting `dev`, `standalone`, `cloud` profiles.
- **Request Correlation Middleware (`app/core/middleware.py`)**: Request ID tracking with `X-Request-ID`.

---

## [0.1.0] - 2026-08-26 (Phase 1 Baseline)

### Added
- Root specification documents (`PRD.md`, `Architecture.md`, `Rules.md`, `Phases.md`, `Design.md`, `Memory.md`).
- Supporting trackers (`docs/CHECKPOINTS.md`, `docs/changelog.md`, `docs/milestones.md`).
