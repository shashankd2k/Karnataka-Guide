# Project Memory & State Snapshot (Memory.md)

## Project Title
**AI-Powered Smart Tourist Guide Platform for Karnataka**

---

## 1. Current State Snapshot

- **Project Version**: `0.18.0`
- **Current Phase**: **Phase 18 — Performance & Scalability Optimization**
- **Phase Status**: **LEVEL 1 OPTIMIZATIONS COMPLETED (STOP GATE ACTIVE — DO NOT START LEVEL 2 / PHASE 19)**
- **Current Checkpoint**: **`CHECKPOINT-P17 = FINAL ACCEPTED`** *(Phase 18 Checkpoint is NOT set final; pending Level 2 evaluation)*
- **Next Step**: **EXPLICIT USER REVIEW FOR LEVEL 1 (DO NOT START LEVEL 2 / PHASE 19)**
- **Last Updated**: 2026-09-20
- **Phase 18 Level 1 Deliverables & Architecture Record**:
  - *L1-A Context Budget Sizing (`num_ctx = 1536`)*: Standardized across backend configuration and Ollama provider. Verified 455 tokens (29.6%) headroom on single-turn max input (895) and 552 tokens (35.9%) on 5-turn history max input (798). Num_ctx 1536 is SAFE.
  - *L1-B Controlled Docker Threading (`num_thread = 2`)*: Pinned to 2 threads matching physical cores on Intel Core i3-1115G4, eliminating spinlock convoying and reducing swap paging.
  - *L1-C Model Residency Keep-Alive (`keep_alive = "10m"`)*: Active model maintained in memory; warm turns reload in < 200ms without runner destruction.
  - *L1-D Persistent HTTP Client*: Persistent `httpx.AsyncClient` connection pool in `OllamaLLMProvider` with graceful lifecycle.
  - *L1-E Prompt Runaway Policy & Stop Sequences*: Directives 7 & 8 added to `prompt_builder.py`; engine stop tokens `["\n\n", "###", "\nTourist Question:", "\nTourist:", "\nUser:", "\nAssistant:", "\nQuestion:"]`. All 7 runaway queries (P07, P08, P10, P21, P22, P24, P28) passed with 0 runaways, 0 truncations, and 100% complete sentences.
  - *Post-L1 Output Distribution*: P50: 93.0 tok, P90: 159.5 tok, P95: 174.6 tok, Max: 186 tok, Mean: 80.9 tok.
  - *Retrieval Guardrails Floor*: 100% preserved (Hit@1 = 100.0%, Recall@5 = 100.0%, MRR = 1.0000, 0 bibliography intrusions, 0 hallucinations).
  - *Runner Stability*: Verified across warm turns (warm loads 23.45ms and 161.78ms; 0 reload spikes).
  - *Level 1 Benchmarks vs P0*: English warm text median 79.66s TTFT / 147.91s total; Kannada text cold 272.44s TTFT / 273.70s total; English voice warm Run 3 210.19s Server Audio Available; Kannada voice 300s timeout bound.
  - *Voice Classification*: `SERVER_TIME_TO_AUDIO_AVAILABLE > 12.0s` -> **STILL TOO SLOW FOR VOICE**. Level 2 Needed: **YES**.
  - *Regression Suite*: Backend 283 / 283 PASS (100%), Frontend 47 / 47 PASS (100%), Vite build clean, Docker 4/4 services healthy, 7/7 AI models loadable offline.
  - *Authoritative Generation*: Invariant strictly preserved (`1a2c6365-1bee-4478-9599-a706ee5c7221`, `is_active = True`).

- **Phase 17 Deliverables & Architecture Record**:
  - *Phase 17 Packaging/Configuration*: Implemented and verified on Docker Engine v29.8.0 / Compose v2.39.4.
  - *Host & Container Model Preflight*: Passed (7/7 models verified loadable offline).
  - *Backend Regression*: 283 / 283 PASS (100%).
  - *Frontend Regression*: 47 / 47 PASS (100%).
  - *Production Build*: PASS (Vite build clean, zero TypeScript errors).
  - *Actual Docker Runtime Verification*: 100% COMPLETE & VERIFIED.
  - *Stage A Clean Deployment*: Executed and cleanly torn down with zero orphaned containers or volumes.
  - *Stage B Persistent Deployment*: Deployed multi-container stack (`karnatakaguide-backend-1`, `karnatakaguide-frontend-1`, `karnatakaguide-mysql-1`, `karnatakaguide-ollama-1`) with 6 persistent volumes (`mysql_data`, `ollama_data`, `huggingface_cache`, `piper_models`, `pdf_storage`, `chroma_data`).
  - *Nginx Reverse Proxy Gateway (Port 80)*: Verified public routing for Frontend SPA (`/` -> 200 OK) and Backend API (`/api/v1/health` -> 200 OK).
  - *Live SSE Streaming & Citations*: `POST /api/v1/tourist/chat/stream` verified through Nginx. Emitted incremental `token` events, `citations` event, and `done` event. Citation contract strictly verified (4 public fields only: `citation_label`, `source_filename`, `page_number`, `section_header`; 0 leaked internal fields).
  - *Ungrounded Fallback*: Verified `grounded=False`, `citations=[]`, and exact bilingual fallback text.
  - *Voice Chat & Restricted TTS*: Faster-Whisper audio transcription verified via `POST /api/v1/tourist/chat/voice`. Restricted TTS verified via `POST /api/v1/tourist/voice/synthesize` (Piper English 22050 Hz and Meta MMS-TTS Kannada 16000 Hz).
  - *TTS Security*: Verified rejection of raw text synthesis and invalid message IDs (HTTP 404/422).
  - *PDF Limits & Proxy Allowance*: Verified exact near-limit 52,428,000 bytes PDF accepted (HTTP 201) and deleted via Admin API; 52,430,000 bytes payload rejected strictly by backend (HTTP 413 PAYLOAD_TOO_LARGE) through deployed Nginx 55M limit.
  - *Admin & Tourist Concurrency*: Concurrent tourist chat turns and administrative PDF operations executed without state collision or session leakage.
  - *Restart Resilience*: Verified Backend restart (Alembic no-op, admin bootstrap idempotency, `/ready` 200), MySQL restart (backend reconnects cleanly), Ollama offline restart (`phi3:mini` inference without pull), and Full stack restart.
  - *Authoritative Generation Invariant Preserved*: Active Generation `1a2c6365-1bee-4478-9599-a706ee5c7221` (`is_active = true`, 22 Chroma chunks, 5/5 referenced PDFs present in `/app/storage/documents`, 0 missing), Temporary Generation `24a31cd8-3680-494c-95f0-22c57c516ac1` (`is_active = false`).
  - *Container-Level Egress Isolation & Zero Cloud AI*: 100% verified with container network namespace routing isolation (`ip route del default` inside `karnatakaguide-backend-1` netns). From inside container, external IP (`8.8.8.8:443`) and cloud endpoint (`api.openai.com:443`) resulted in `OSError: [Errno 101] Network is unreachable`, while internal communication (`backend -> ollama`, `backend -> mysql`, and host/Nginx grounded chat) functioned 100% locally. External routing was cleanly restored afterward with all containers healthy.
  - *Host/Container Resource Observations*: Recorded container RAM metrics (Frontend ~5MB, Backend ~366MB idle / ~2.3GB peak, MySQL ~367MB, Ollama ~14MB idle / ~2.2GB active) and WSL2 VM RAM/swap metrics.
- **Phase 16 Deliverables & Architecture Record**:
  - *Full End-to-End Live Integration*: Comprehensive verification across all 17 integration matrix scenarios, covering bilingual tourist chat, streaming SSE, Faster-Whisper STT, Piper & MMS TTS voice synthesis, dense+BM25+CrossEncoder RAG, admin authentication & RBAC, document management, and knowledge generation promotion/rollback.
  - *MySQL 8.0 Contract Verification*: Verified active application persistence against approved MySQL 8.0.31 daemon on 127.0.0.1 (local dev instance on port 3307), with zero unapproved database versions.
  - *Authoritative Generation Invariant*: Validated real Generation B (`24a31cd8-3680-494c-95f0-22c57c516ac1`) promotion, query retrieval from promoted generation, and atomic rollback restoring Generation A (`1a2c6365-1bee-4478-9599-a706ee5c7221`, `v_20260829_183224_1a2c63`, `is_active=True`).
  - *100% Offline Standalone Operation*: Validated with strict socket-level WAN isolation blocking all non-loopback IP/host traffic. All 9 core services (RAG, Ollama phi3:mini, NLLB-200 translation, Faster-Whisper STT, Piper TTS, MMS-TTS, SSE streaming, Admin portal) operated 100% locally with zero calls to forbidden cloud AI endpoints.
  - *NLLB-200 Offline Defect Discovery & Minimal Cache-First Fix (`backend/app/infrastructure/translation/nllb.py`)*:
    - *Defect Discovered*: In strict offline mode with WAN blocked, `from_pretrained(model_name)` defaulted to checking remote Hugging Face Hub for metadata updates, causing offline connection failures even when weights were cached locally.
    - *Minimal Cache-First Fix*: Wrapped model and tokenizer loading with a cache-first `local_files_only=True` try block. If cached, model and tokenizer load locally without remote network attempts. If un-cached (first-time setup), the exception block falls back to standard online download (`AutoTokenizer.from_pretrained(model_name)` and `AutoModelForSeq2SeqLM.from_pretrained(model_name)`).
    - *First-Download Compatibility*: Initial setup and first-run model download path is 100% preserved.
    - *Zero Contract Changes*: Public API contract unchanged (`ITranslationProvider`), translation output contract unchanged, model (`facebook/nllb-200-distilled-600M`) unchanged.
    - *Focused Regression Coverage*: Added dedicated tests in `backend/tests/test_translation.py` verifying cached local-only loading, zero remote network access, first-download online fallback, and error handling.
  - *Database Runtime Artifact Hygiene*: Established root and backend `.gitignore` rules strictly ignoring `backend/storage/mysql8_data/`, `*.sql`, `dump_*.sql`, and MySQL runtime files, ensuring zero runtime data or migration dumps are tracked in git.
  - *Controlled Fault Resilience & Recovery*: Validated graceful extractive degradation on Ollama failure (port 11435) with database message integrity, TTS failure handling (HTTP 503 without DB corruption) and recovery, and translation failure fallback to raw query string.
  - *Real Browser Tile-Network Failure (CDP)*: Validated on live frontend (`/map`) using Chrome CDP Network emulation (blocking OpenStreetMap tile URLs and `offline=true`). Verified page integrity without crash, offline UI banner visibility, persistent destination markers and content access, AI Guide navigation link availability, and clean recovery upon restoring network.
  - *Interactive Responsive Smoke Verification (CDP)*: Verified at 390px (Mobile iPhone 14) and 1440px (Desktop Full) with zero horizontal overflow: citation drawer opens and fits, voice recorder modal opens, fits, and closes cleanly, and admin confirmation dialog fits viewport without overflow.
  - *Complete English Voice-to-Voice Loop*: Executed full spoken turn (Piper spoken input -> Faster-Whisper STT -> Grounded RAG + Ollama phi3:mini -> Piper TTS synthesis) with verified assistant message persistence and audio synthesis (1,087,020 bytes WAV).
  - *Regression Baseline*: 283 / 283 backend Pytest tests passing (100%), 47 / 47 frontend Vitest tests passing (100%), clean production build (`npm run build`, zero TypeScript errors).
  - *Preserved Project Debt & Known Limitations*:
    - *Phase 14*: Physical browser microphone capture remains unverified in headless automated CI environments.
    - *Phase 14*: Kannada font binaries are not bundled; standalone offline rendering relies on OS-level Kannada font fallbacks.
    - *Phase 16 Local Dev Security Debt*: Local development MySQL 8.0 instance uses default credentials; recorded for Phase 20 security hardening.
    - *Phase 18 Debt*: Whole-system RAM footprint reaches ~7.7 GB on 8 GB development hardware with the full local AI stack loaded. Zero new blocking Phase 16 defects.
- **Completed Phases**:
  - `Phase 1`: Requirements & Architecture Specification (`CHECKPOINT-P1`)
  - `Phase 2`: Backend Foundation & Core Infrastructure (`CHECKPOINT-P2`)
  - `Phase 3`: MySQL Persistence Foundation & Alembic Migrations (`CHECKPOINT-P3`)
  - `Phase 4`: Admin Authentication & RBAC (`CHECKPOINT-P4`)
  - `Phase 5`: Secure PDF Document Management (`CHECKPOINT-P5`)
  - `Phase 6`: Knowledge Base Pipeline, Parsing, Embeddings & ChromaDB Foundation (`CHECKPOINT-P6`)
  - `Phase 7`: RAG Retrieval Optimization (`CHECKPOINT-P7`)
  - `Phase 8`: Multilingual Conversation Engine (`CHECKPOINT-P8`)
  - `Phase 9`: Ollama LLM Integration, Grounded Prompting & Token Streaming (`CHECKPOINT-P9`)
  - `Phase 10`: Speech-To-Text (STT) Engine / Faster-Whisper (`CHECKPOINT-P10`)
  - `Phase 11`: Multilingual Translation Hardening / Meta NLLB-200 600M (`CHECKPOINT-P11`)
  - `Phase 12`: Text-To-Speech (TTS) Synthesis / Piper TTS & Meta MMS-TTS (`CHECKPOINT-P12`)
  - `Phase 13`: Unified FastAPI Client Gateway / Streaming Integration (`CHECKPOINT-P13`)
  - `Phase 14`: Premium Tourist Web Application (`CHECKPOINT-P14`)
  - `Phase 15`: Premium Admin Dashboard (`CHECKPOINT-P15`)
  - `Phase 16`: Full End-to-End System Integration (`CHECKPOINT-P16`)
  - `Phase 17`: Docker & Cloud Deployment (`CHECKPOINT-P17`)

---

## 2. Implemented Functionality & Summary

### Phase 12 Deliverables (Text-To-Speech Synthesis / Piper TTS & Meta MMS-TTS)
1. **Domain Port & Infrastructure TTS Providers (`app/domain/ports/tts.py`, `app/infrastructure/tts/`)**:
   - Declared `ITTSProvider` abstract domain port with `synthesize(text, language) -> AudioSynthesisResult`, `check_health() -> bool`, and `get_supported_languages() -> list[str]`.
   - Declared `AudioSynthesisResult` dataclass (`audio_bytes`, `sample_rate`, `channels`, `sample_width`, `duration_seconds`, `mime_type`).
   - Implemented `PiperTTSProvider` using `piper-tts==1.7.0` and ONNX model `en_US-lessac-medium` on CPU (22,050 Hz Mono, 16-bit PCM WAV, RTF 0.129x = **7.8x real-time speed**, +124.71 MB RAM, MIT engine license / Lessac Blizzard dataset terms).
   - Implemented `MMSTTSProvider` using `facebook/mms-tts-kan` via Hugging Face `transformers.VitsModel` on CPU (16,000 Hz Mono, 16-bit PCM WAV, RTF 0.658x = **1.5x real-time speed**, +170.57 MB RAM, CC-BY-NC-4.0 approved academic/development offline Kannada TTS provider).
   - Implemented `CompositeTTSProvider` routing `en` -> Piper and `kn` -> MMS-TTS with thread-safe lazy model initialization and non-blocking `asyncio.to_thread` execution.
2. **Restricted Synthesis Contract & Voice Security (`app/api/v1/endpoints/voice.py`, `app/application/speech/tts_service.py`)**:
   - `POST /api/v1/tourist/voice/synthesize`: Restricted endpoint requiring `session_uuid` and `assistant_message_id`. Verifies tourist session exists, confirms message belongs to that session, validates `sender_type=ASSISTANT`, extracts authoritative session/message language, and synthesizes that exact approved answer.
   - Raw unrestricted user-supplied text synthesis is strictly prevented.
   - Custom HTTP response headers: `X-Audio-Duration-Seconds`, `X-Audio-Sample-Rate`, `X-Audio-Channels`, `X-Language`.
3. **Pure Memory-First Audio Streaming & Wave Serialization**:
   - Model inference $\rightarrow$ waveform tensor / audio chunk $\rightarrow$ Python stdlib `wave` $\rightarrow$ `io.BytesIO` $\rightarrow$ WAV binary bytes $\rightarrow$ FastAPI StreamingResponse / Response. Zero temporary audio files written to disk.
4. **Deterministic Speech Text Sanitization (`app/application/speech/tts_service.py`)**:
   - `SpeechTextSanitizer`: Pure regex-based stripping of citation markers (`\[\d+\]`), markdown formatting (`**`, `*`, `_`, `#`, `>`), and URLs for audio rendering.
   - Preserves complete Kannada Unicode text, proper nouns, and historical dates (*1117 CE*, *733 CE*, *12th century*, *ಕ್ರಿ.ಶ. 1117*, *12ನೇ ಶತಮಾನ*).
   - Zero LLM rewriting; zero modifications to stored database messages, citations, or frontend display text.
5. **Testing, Quality & Combined Stack Memory Benchmark (`tests/test_tts.py`, `scratch/benchmark_phase12_tts.py`)**:
   - 32 unit, integration, and live model test cases in `tests/test_tts.py` (100% passing).
   - **Full Regression Suite**: **248 / 248 passed across all 22 test files (100% pass rate)**.
   - **Quality Benchmark (10 English + 10 Kannada Historical Tourism Sentences)**:
     - English (Piper TTS): **10/10 synthesized (100%)**, Avg Latency: 860.5 ms, Avg RTF: 0.129x (**7.8x real-time speed**), 22,050 Hz Mono WAV.
     - Kannada (MMS-TTS): **10/10 synthesized (100%)**, Avg Latency: 6,727.8 ms, Avg RTF: 0.658x (**1.5x real-time speed**), 16,000 Hz Mono WAV.
     - Exact Fallbacks: 100% playable WAV for `"Information is not available in the knowledge base."` and `"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`.
   - **Combined Stack Memory Profile**:
     - Baseline Process RAM: ~397.51 MB
     - RAM with Piper Loaded: +124.71 MB
     - RAM with MMS-TTS Loaded: +170.57 MB
     - Total Isolated TTS RAM Overhead: **+295.29 MB Working Set (+366.58 MB Private)**
     - Full Combined Multilingual Voice Stack (FastAPI + ChromaDB + CrossEncoder + NLLB + Whisper + Ollama + Piper + MMS): **1,853.20 MB Working Set (~1.85 GB) / 4,254.25 MB Private (~4.25 GB)** (comfortably within 8 GB host RAM budget).

### Phase 11 Deliverables (Multilingual Translation Hardening / Meta NLLB-200 600M)
1. **Domain Port & Infrastructure NLLB-200 Provider (`app/domain/ports/translation.py`, `app/infrastructure/translation/nllb.py`)**:
   - Declared `ITranslationProvider` abstract domain port with `translate_text`, `get_supported_languages`, and `check_health`.
   - Implemented `NLLBTranslationProvider` using Hugging Face Transformers running `facebook/nllb-200-distilled-600M` (CC-BY-NC-4.0 approved academic/development translation provider) on CPU with process-level singleton caching and non-blocking `asyncio.to_thread` execution.
   - ISO language mapping: `kn` / `kannada` $\rightarrow$ `kan_Knda`, `en` $\rightarrow$ `eng_Latn`.
2. **Direction-Aware Canonical Heritage Entity Restoration & Verification (`app/application/translation/service.py`)**:
   - Direction-aware pre-translation query preparation mapping 12+ core Kannada proper nouns (*ಬೇಲೂರು*, *ಚೆನ್ನಕೇಶವ*, *ಹಳೇಬೀಡು*, *ಹೊಯ್ಸಳೇಶ್ವರ*, *ಬಾದಾಮಿ*, *ಐಹೊಳೆ*, *ಪಟ್ಟದಕಲ್ಲು*, *ಹಂಪಿ*, *ವಿರೂಪಾಕ್ಷ*, *ವಿಠ್ಠಲ*, *ವಿಜಯನಗರ*, *ವಿಷ್ಣುವರ್ಧನ*) into their canonical English forms (*Belur*, *Chennakeshava*, *Halebidu*, *Hoysaleswara*, *Badami*, *Aihole*, *Pattadakal*, *Hampi*, *Virupaksha*, *Vittala*, *Vijayanagara*, *Vishnuvardhana*) before NLLB translation.
   - Post-translation entity preservation verification guaranteeing all proper nouns exist in the final English retrieval query.
   - Strict inline citation placeholder integrity (`[1]`, `[2]`) with safe English fallback upon citation distortion.
3. **Bilingual RAG Query & Response Translation (`app/application/conversation/service.py`)**:
   - Kannada search queries translated into English for Phase 7 hybrid dense/BM25/Cross-Encoder retrieval (`translate_retrieval_query`). English search queries bypass translation with zero overhead.
   - Grounded answers translated to Kannada (`translate_response`) with visible citation markers (`[1]`, `[2]`) preserved.
   - Authoritative metadata (`chunk_id`, `document_id`, `generation_id`, `source_filename`, `page_number`) strictly isolated on the backend and NEVER passed to the translation model.
   - Original tourist query persisted verbatim in `ChatMessage` (`sender_type=USER`).
   - Standardized exact fallbacks (`"Information is not available in the knowledge base."` $\leftrightarrow$ `"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`) returned with zero translation overhead and zero LLM calls.
4. **Admin Translation Registry Endpoint (`app/api/v1/endpoints/translations.py`)**:
   - `GET /api/v1/admin/translations`: Authenticated endpoint exposing active translation engine metadata (`nllb`, `nllb-200-distilled-600M`, CC-BY-NC-4.0 license, supported languages `kn`, `en`, ISO mappings `kan_Knda`, `eng_Latn`, offline model readiness).
5. **Testing & Hardening Verification (`tests/test_translation.py`, `scratch/verify_phase11_hardening.py`)**:
   - 37 unit, integration, and security tests in `tests/test_translation.py` (100% passing).
   - **Full Regression Baseline**: **216 / 216 passed across all 21 test files (100% pass rate)**.
   - **Target Kannada Retrieval Verification**:
     - Kannada Query: `"ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?"`
     - Corrected English query: `"Who built the Belur Chennakeshava Temple?"`
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
     - Full-Stack Process Working Set: ~2.3 GB RAM on CPU

### Phase 10 Deliverables (Speech-To-Text Engine / Faster-Whisper)
1. **Domain Port & Infrastructure STT Provider (`app/domain/ports/stt.py`, `app/infrastructure/stt/faster_whisper.py`)**:
   - Declared `ISpeechToTextProvider` abstract domain port with `transcribe_audio` and `check_health`.
   - Implemented `FasterWhisperProvider` using CTranslate2 running quantized `base` model (`int8` compute on CPU) with thread-safe process-level singleton caching and non-blocking `asyncio.to_thread` execution.
2. **Deep Audio & Container Decoder Validation (`app/infrastructure/stt/audio_validator.py`)**:
   - Multi-layer security pipeline: size limits ($\le 15$ MB), MIME/extension allowlist (`WAV`, `MP3`, `OGG`, `WebM`, `M4A`, `MP4`), magic bytes/EBML signature checks, and PyAV deep container decoding.
   - Verifies decodable audio streams exist, enforces duration bounds ($\le 60.0$ s), and rejects video-only/corrupt files.
3. **Transient Privacy & Guaranteed File Cleanup**:
   - Temporary audio files saved to `storage/temp_audio` are validated, transcribed, and deleted in guaranteed `finally` context blocks across all execution and exception paths. No raw voice recordings are permanently stored.
4. **Public Tourist Speech APIs & Language Security (`app/api/v1/endpoints/voice.py`, `app/application/speech/stt_service.py`)**:
   - `POST /api/v1/tourist/voice/transcribe`: Unauthenticated multipart audio upload returning structured `TranscriptionResponse`.
   - `POST /api/v1/tourist/chat/voice`: Voice-to-chat integration piping speech transcript directly into `ConversationService.process_turn()` returning combined transcript, grounded answer, and citations.
   - **Language Hint Allowlisting & Session Routing**: Validates language hints against allowlist (`{"en", "kn"}`) and automatically prefers established trusted session language (`language_code="kn"`) over unverified client parameters.
5. **Testing & Real Multilingual Audio Benchmark**:
   - 20 unit and integration tests in `tests/test_stt.py` (100% passing).
   - **Full Regression Baseline**: **179 / 179 passed across all 20 test files**.
   - **Performance Metrics**: Cold model load: 1510.96 ms, Decode latency: 23.35 ms, Warm transcription: 1344.42 ms, E2E STT: 1417.99 ms, RTF: 0.43x (2.3x faster than real-time on CPU).
   - **Known Kannada STT Quality Limitation**:
     - Faster-Whisper multilingual `base` on the current development laptop provides acceptable English STT (**WER: 21.71%**) but poor Kannada acoustic transcription quality (**Auto CER: 113.15%**, **Forced-kn CER: 109.63%**, **Forced-kn WER: 115.67%**).
     - Forced `language="kn"` improves tokenization and heritage proper noun recognition (`Aihole` $\rightarrow$ `Aiholi`, `Badami`, `Hampi`, `Vijayanagara`), but does not achieve production-quality transcription on `base`.
     - *Phase 11 Boundary*: Phase 11 will handle Kannada $\leftrightarrow$ English text translation and query normalization, but cannot repair severely corrupted acoustic transcripts.
     - *Phase 18 Benchmarking*: Full model evaluation across `base`, `small`, and `medium` models on target production hardware is scheduled for Phase 18 (Performance & Optimization).

---

## 2. Implemented Functionality & Summary

### Phase 9 Deliverables (Ollama LLM Integration & Token Streaming)
1. **Domain Port & Infrastructure LLM Client (`app/domain/ports/llm.py`, `app/infrastructure/llm/ollama.py`)**:
   - Implemented `ILLMProvider` abstract domain port declaring `generate_text`, `generate_stream`, and `check_health`.
   - Built lightweight asynchronous `OllamaLLMProvider` using native `httpx.AsyncClient` targeting local Ollama daemon (`http://127.0.0.1:11434`).
   - Supports local models (`phi3:mini`, `mistral:7b`, `llama3.1:8b`) with deterministic low temperature (`temperature=0.1`) and concise token budget (`num_predict=128`).
2. **Prompt Isolation & Anti-Injection Architecture (`app/application/rag/prompt_builder.py`)**:
   - Built strict structural prompt separation between System Directives, Verified Evidence (`=== EVIDENCE START ===` ... `=== EVIDENCE END ===`), and User Query.
   - Enforces explicit prompt directive treating retrieved documents as untrusted raw data and forbidding execution of injection instructions.
   - Implemented context character budgeting (`OLLAMA_MAX_CONTEXT_CHARS=2000`) and near-duplicate passage deduplication.
3. **Exact Fallback & Non-Streaming Validation (`app/application/conversation/service.py`)**:
   - Enforced strict `GroundingGuard` evaluation: ungrounded queries ($< -6.0$) **bypass Ollama completely** and return the exact localized fallback with 0 citations:
     - English: `"Information is not available in the knowledge base."`
     - Kannada: `"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`
   - Validated complete non-streaming responses, sanitizing citation markers `[1]`, `[2]` and stripping hallucinated tokens.
   - Preserved 100% authoritative server-side citation provenance from MySQL `document_chunks`.
4. **Graceful Degradation Resilience**:
   - If the local Ollama daemon is unreachable or times out, the conversational engine degrades gracefully to verified Phase 8 extractive source evidence with full MySQL citations and structured logging.
5. **Server-Sent Events (SSE) Streaming (`POST /api/v1/tourist/chat/stream`)**:
   - Implemented real-time token streaming endpoint via FastAPI `StreamingResponse` emitting `token`, `citations`, and `done` SSE events.
   - Evaluates `GroundingGuard` before streaming starts; persists final turn in MySQL only upon successful stream completion.
6. **Testing & Benchmark Verification**:
   - Comprehensive Phase 9 test suite in `tests/test_llm.py` (17 tests covering mock provider, injection defense, timeouts, connection errors, citation sanitization, streaming, and ungrounded bypass).
   - **Full Regression**: **159 passed in 209.40s (100% across all 19 test files)**.
   - **30-Turn Real Ollama Benchmark (`scratch/benchmark_phase9_llm.py`)**:
     - Grounding Classification Accuracy: **100.00% (30/30)**.
     - Unsupported Exact Fallback Rate: **100.00% (5/5)**.
     - Unsupported Zero Citation Rate: **100.00% (5/5)**.
     - Citation Provenance Precision (MySQL): **100.00% (25/25)**.
     - Hallucination Count: **0**.

---

## 2. Implemented Functionality & Summary

### Phase 8 Deliverables (Multilingual Conversation Engine)
1. **Zero-Auth Anonymous Tourist Session Management**:
   - `POST /api/v1/tourist/sessions`: Generates persistent UUID-identified sessions in MySQL `chat_sessions` table with preferred language code. Zero tourist login, signup, or JWT tokens required.
   - `GET /api/v1/tourist/sessions/{session_uuid}`: Returns chronological chat history with message timestamps and metadata.
   - `DELETE /api/v1/tourist/sessions/{session_uuid}`: Immediate cascading privacy deletion of session messages and conversation records.
2. **Multilingual Unicode Script Detection (`app/application/conversation/language_detector.py`)**:
   - Deterministic Unicode code-point script inspection for pure English (`en`), pure Kannada (`kn`), and script-mixed (`kn-mixed`) tourist queries without heavyweight external dependencies.
   - Documented Romanized Kannada limitation as a future Phase 11 item.
3. **Bounded Multi-Turn Context & Follow-Up Resolution (`app/application/conversation/context_builder.py`)**:
   - Strictly bounded 5-turn conversation windowing (`CONVERSATION_MAX_TURNS=5`).
   - Reverse-chronological heritage entity and proper noun extraction (`Belur Chennakeshava Temple`, `Badami Caves`, `Halebidu`, `Aihole`, etc.).
   - Follow-up query rewriting for referential pronouns (`it`, `its`, `this monument`, `there`, `here`) while preserving original user query in database verbatim.
4. **Strict Grounding Guard & Bilingual Fallbacks (`app/application/conversation/grounding_guard.py`)**:
   - Enforces empirical calibrated Cross-Encoder threshold (`CONVERSATION_GROUNDING_MIN_SCORE = -6.0`).
   - Verified active generation requirement; returns standardized fallbacks when evidence is absent:
     - English: `"Information is not available in the knowledge base."`
     - Kannada: `"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`
   - Yields zero citations when ungrounded.
5. **Extractive Source Evidence & Citation Formatter (`app/application/conversation/citation_formatter.py`)**:
   - Compiles verbatim ranked source passages with inline bracketed citation markers (`[1]`, `[2]`).
   - Populates structured citation objects containing `chunk_id`, `source_filename`, `page_number`, and `generation_id` without premature synthetic text generation.
6. **Public Canonical Tourist API (`app/api/v1/endpoints/tourist.py`)**:
   - `POST /api/v1/tourist/chat`: Validates session UUID, checks message length ($\le 1000$ chars), executes bounded context resolution, triggers Phase 7 `RAGRetrievalService`, applies grounding guard, persists user and assistant messages, and returns structured response.
7. **Real 30-Turn Multilingual Conversation Benchmark (`scratch/benchmark_conversation.py`)**:
   - Evaluated 30 conversational turns across 8 distinct tourist dialogue sessions against active generation `6ee08b45-823a-4bd5-8604-920bbdd61d58`.
   - **Language Detection Accuracy**: **100.00%** (30/30).
   - **Follow-Up Context Resolution Accuracy**: **100.00%** (10/10).
   - **Grounding Decision Accuracy**: **100.00%** (30/30).
   - **Emitted Citation Set Accuracy**: **100.00%** (22/22 grounded turns).
   - **Authoritative MySQL Provenance**: **100.00%** (44/44 citations verified against MySQL `document_chunks`).
   - **Safe Fallback Response Accuracy**: **100.00%** (8/8 ungrounded turns: 5 pure Kannada cross-script + 3 out-of-domain).
   - **Steady-State Warm Turn Latency**: **969.28 ms**.
8. **Automated Test Suite (`tests/`)**:
   - Total tests: **142 passed** (100% pass rate in 29.89s) across 18 test files.

### Previous Completed Phases
- **Phase 7**: RAG retrieval optimization, Dense + BM25 + RRF + Cross-Encoder re-ranking, 24-query real heritage benchmark (`CHECKPOINT-P7`).
- **Phase 6**: PDF parsing, semantic chunking, SentenceTransformer 384d embeddings, isolated Chroma collections, validation gates, atomic promotion, rollback (`CHECKPOINT-P6`).
- **Phase 5**: PDF upload, validation, UUID storage (`storage/documents/`), SHA-256 duplicate detection, failure-safe deletion, audit logging (`CHECKPOINT-P5`).
- **Phase 4**: Argon2id password hashing, PyJWT tokens, token rotation with reuse detection, RBAC dependencies, super admin bootstrap (`CHECKPOINT-P4`).
- **Phase 3**: MySQL 8.0 persistence, asyncmy driver, 16 ORM models, Alembic baseline migration, live DB health probe, idempotent seed (`CHECKPOINT-P3`).
- **Phase 2**: FastAPI application factory, Pydantic v2 settings, structlog logging, `X-Request-ID` correlation, typed error hierarchy (`CHECKPOINT-P2`).
- **Phase 1**: Core system architecture and specifications (`CHECKPOINT-P1`).

---

## 3. Important Architectural Decisions (Locked)

1. **Pure Software Architecture**: 100% software platform deployable locally and to cloud. Zero robotics/sensors code.
2. **Zero Tourist Authentication**: Tourists NEVER log in. Conversational exploration is 100% frictionless.
3. **Transactional Database (MySQL 8.0)**: MySQL 8.0 with SQLAlchemy 2.x (asyncmy) and Alembic is strictly locked.
4. **Active Generation Retrieval Isolation**: Dense vector search and BM25 search strictly query chunks belonging to the currently `ACTIVE` knowledge generation (`is_active=True`, status `ACTIVE`).
5. **Reciprocal Rank Fusion Constant**: $k=60$ locked for RRF ranking.
6. **Cross-Encoder Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2` loaded once per process and cached locally.
7. **No LangChain / No LlamaIndex**: Lightweight, explicit, inspectable implementation using native Python, NumPy, rank-bm25, sentence-transformers, and ChromaDB.
8. **Next Phase (Phase 8 Scope)**: Strict Evidence-Grounded Response Synthesis (Ollama LLM integration, prompt templates, anti-hallucination citations, guardrails). Phase 8 logic was NOT started during Phase 7.

---

## 4. File Index (Phase 7 Baseline)

```text
d:\Karnataka Guide\
├── PRD.md
├── Architecture.md
├── Rules.md
├── Phases.md
├── Design.md
├── Memory.md
├── docs/
│   ├── CHECKPOINTS.md
│   ├── changelog.md
│   └── milestones.md
└── backend/
    ├── requirements.txt
    ├── requirements-dev.txt
    ├── .env.example
    ├── .env
    ├── pytest.ini
    ├── alembic.ini
    ├── storage/
    │   ├── documents/
    │   └── chroma/
    ├── alembic/
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/
    │       └── 0001_initial_schema.py
    ├── app/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── core/
    │   │   ├── __init__.py
    │   │   ├── config.py
    │   │   ├── logging.py
    │   │   ├── errors.py
    │   │   ├── middleware.py
    │   │   └── security.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── auth/
    │   │   │   ├── __init__.py
    │   │   │   ├── schemas.py
    │   │   │   ├── service.py
    │   │   │   └── dependencies.py
    │   │   ├── documents/
    │   │   │   ├── __init__.py
    │   │   │   ├── schemas.py
    │   │   │   ├── storage.py
    │   │   │   └── service.py
    │   │   ├── knowledge/
    │   │   │   ├── __init__.py
    │   │   │   ├── schemas.py
    │   │   │   ├── extractor.py
    │   │   │   ├── chunker.py
    │   │   │   ├── embeddings.py
    │   │   │   ├── vector_store.py
    │   │   │   └── service.py
    │   │   └── rag/
    │   │       ├── __init__.py
    │   │       ├── schemas.py
    │   │       ├── normalization.py
    │   │       ├── dense.py
    │   │       ├── bm25.py
    │   │       ├── fusion.py
    │   │       ├── reranker.py
    │   │       ├── filters.py
    │   │       └── service.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   └── db/
    │   │       ├── __init__.py
    │   │       ├── session.py
    │   │       ├── health.py
    │   │       ├── seed.py
    │   │       ├── bootstrap_admin.py
    │   │       └── models/
    │   │           ├── __init__.py
    │   │           ├── base.py
    │   │           ├── admin.py
    │   │           ├── document.py
    │   │           ├── generation.py
    │   │           ├── chunk.py
    │   │           ├── chat.py
    │   │           ├── audit.py
    │   │           └── system.py
    │   └── api/
    │       ├── __init__.py
    │       └── v1/
    │           ├── __init__.py
    │           ├── router.py
    │           └── endpoints/
    │               ├── __init__.py
    │               ├── health.py
    │               ├── auth.py
    │               ├── documents.py
    │               ├── knowledge.py
    │               └── diagnostics.py
    └── tests/
        ├── __init__.py
        ├── conftest.py
        ├── test_config.py
        ├── test_logging.py
        ├── test_middleware.py
        ├── test_errors.py
        ├── test_health.py
        ├── test_db_config.py
        ├── test_db_models.py
        ├── test_db_session.py
        ├── test_db_health.py
        ├── test_db_seed.py
        ├── test_security.py
        ├── test_auth_service.py
        ├── test_auth_api.py
        ├── test_rbac.py
        ├── test_bootstrap_admin.py
        ├── test_document_validation.py
        ├── test_document_storage.py
        ├── test_document_api.py
        ├── test_pdf_extractor.py
        ├── test_semantic_chunker.py
        ├── test_embeddings.py
        ├── test_chroma_store.py
        ├── test_knowledge_pipeline.py
        ├── test_retrieval.py
        └── test_diagnostics_api.py
```

---

## 5. Database Migrations & APIs
- **Database Migrations**:
  - `0001_initial_schema.py` (all 16 tables in MySQL 8.0, untouched).
- **APIs Implemented/Extended**:
  - `GET /health`, `GET /live`, `GET /ready`, `GET /version`, `GET /api/v1/health`
  - `POST /api/v1/admin/auth/login`, `POST /api/v1/admin/auth/refresh`, `POST /api/v1/admin/auth/logout`, `GET /api/v1/admin/auth/me`
  - `POST /api/v1/admin/documents`, `GET /api/v1/admin/documents`, `GET /api/v1/admin/documents/{id}`, `GET /api/v1/admin/documents/{id}/download`, `DELETE /api/v1/admin/documents/{id}`
  - `POST /api/v1/admin/knowledge/generations/build`
  - `GET /api/v1/admin/knowledge/generations`
  - `GET /api/v1/admin/knowledge/generations/{id}`
  - `POST /api/v1/admin/knowledge/generations/{id}/promote`
  - `POST /api/v1/admin/knowledge/generations/{id}/rollback`
  - `POST /api/v1/admin/knowledge/retrieval-test` (RAG hybrid retrieval diagnostic)
  - `POST /api/v1/admin/diagnostics/retrieve` (RAG hybrid retrieval diagnostic alias)

---

## 6. Tests & Verification
- **Python Version**: Officially locked at **Python 3.12.10** (`.venv`).
- **Automated Tests**: 113 tests passing (`pytest tests -v` $\rightarrow$ 113 passed in 46.82s, 100% pass rate).
- **Test Coverage**: Settings, logging, request IDs, exceptions, DB configuration, ORM models, session lifecycles, health probes, seeding, Argon2id hashing, PyJWT tokens, token rotation & reuse detection, auth APIs, RBAC guards, super admin bootstrap, PDF validation, UUID disk storage, duplicate detection, listing pagination, download byte matching, failure-safe deletion, active document protection, PyMuPDF extraction, semantic chunking, SentenceTransformer 384d embeddings, persistent ChromaDB indexing, pipeline execution stages, atomic promotion, rollback, security audit logs, query normalization & diacritic mapping, BM25 indexing & scoring, dense vector querying, RRF math ($k=60$), Cross-Encoder re-ranking, bibliography & noise suppression, duplicate chunk suppression, and retrieval diagnostic endpoints.
- **Offline Model Cache Verification**: Verified offline cache reuse for both `all-MiniLM-L6-v2` and `cross-encoder/ms-marco-MiniLM-L-6-v2` (`local_files_only=True`).
- **Real MySQL + ChromaDB + BM25 + Cross-Encoder Benchmark**: Evaluated against live MySQL 8.0 `karnataka_guide` and persistent ChromaDB collection (`v_20260826_185105_9101c1`). Hit@1: 80.0%, Recall@5: 100.0%, MRR: 0.9000, Bibliography leaks: 0%, Steady-state warm latency: ~207 ms.

---

## 7. Known Technical Debt & Issues
- None.

---

## NEXT TASK

**RESUME PHASE 17 RUNTIME VERIFICATION ONCE DOCKER ENGINE / DOCKER COMPOSE BECOMES AVAILABLE ON HOST. DO NOT REDO PLANNING. DO NOT START PHASE 18.**
