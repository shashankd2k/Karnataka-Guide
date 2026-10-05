# Engineering Rules & Standards (Rules.md)

## Project Title
**AI-Powered Smart Tourist Guide Platform for Karnataka**

---

## 1. Core Engineering Philosophy: Lean Vibe-Coding

All development on this project must adhere to a **minimal-code-first philosophy**:
- **Minimum Necessary Complexity**: Strive for the simplest correct implementation. Never write 50 lines of boilerplate when a robust 5–10 line native solution suffices.
- **No Premature Abstraction**: Do not create interfaces, wrappers, managers, or factories unless multiple concrete implementations or strict domain testing boundaries require them.
- **Native Capabilities Priority**:
  1. Python / JavaScript Language Standard Library
  2. Framework-native feature (FastAPI / React 19)
  3. Browser-native Web API (MediaRecorder, Web Audio, SpeechSynthesis)
  4. Existing installed dependency
  5. New dependency (only when explicitly justified)

---

## 2. Approved Technology Stack (Locked)

### 2.1 Backend Stack
- **Language**: Python 3.12+ (Strict type annotations mandatory)
- **Web Framework**: FastAPI (AsyncIO throughout)
- **Data Validation**: Pydantic v2
- **ORM / Querying**: SQLAlchemy 2.x (Async Engine)
- **Database Migrations**: Alembic
- **Database Engine**: MySQL 8.0 ONLY (utf8mb4_unicode_ci)
- **Structured Logging**: Structlog (JSON in prod, colored console in dev)
- **Authentication**: PyJWT (HS256 with key rotation)
- **Password Hashing**: Argon2id (`argon2-cffi`)
- **Testing**: Pytest + pytest-asyncio + httpx

### 2.2 AI & Machine Learning Stack
- **Local LLM Engine**: Ollama (Default: `llama3.1:8b`, Supported: `mistral:7b`, `qwen2.5`, `gemma2`)
- **Vector Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **Vector Database**: ChromaDB (Persistent local collections keyed by generation version)
- **Sparse Retrieval**: `rank-bm25`
- **Re-ranking**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Speech-to-Text (STT)**: `faster-whisper` (Kannada, English, Mixed)
- **Text-to-Speech (TTS)**: `Piper` (Offline ONNX neural voice)
- **Translation**: `Argos Translate` (Offline English $\leftrightarrow$ Kannada packages)
- **PDF Extraction**: `PyMuPDF` (`fitz`)

### 2.3 Frontend Stack
- **Core**: React 19 + TypeScript (Strict mode enabled)
- **Build Tool**: Vite
- **Styling**: Tailwind CSS (Scoped design tokens)
- **UI Components**: `shadcn/ui` (Selected accessible primitives)
- **Animations**: `framer-motion` (Micro-interactions, smooth reveals)
- **Data Fetching & Cache**: `@tanstack/react-query`
- **State Management**: `zustand` (Lightweight client session store)
- **Routing**: `react-router-dom` v6/v7
- **Maps**: `leaflet` + `react-leaflet` + OpenStreetMap
- **Charts / Telemetry**: `recharts`

---

## 3. Anti-Bloat & Dependency Rules

### 3.1 Dependency Addition Protocol
Before introducing any new non-trivial library, you must provide a justification comment in the pull request or task log:
```text
Dependency: <package-name>
Purpose: <exact problem solved>
Existing alternative considered: <std library or installed tool>
Why dependency is justified: <concrete technical justification>
```

### 3.2 Prohibited Dependencies & Practices
- **NO Robotics / Hardware Libraries**: Never install ROS2, Jetson packages, RPi.GPIO, Arduino CLI, or physical serial sensor readers.
- **NO Database Switching**: Never introduce PostgreSQL, SQLite, or MongoDB. MySQL 8.0 is permanently locked.
- **NO Utility Bloat**: Never install libraries like `lodash`, `moment.js`, or `axios` when native ES2024 / browser `fetch` / Python standard libraries are sufficient.
- **NO Ad-hoc CSS Frameworks**: Do not mix Tailwind with Bootstrap or raw inline styles.

---

## 4. Coding & Architecture Standards

### 4.1 Python / Backend Standards
- **Asynchronous by Default**: All I/O operations (database, file system, HTTP calls, vector queries) must be `async def`.
- **Type Safety**: All function signatures must have complete type hints (`mypy` compliant).
- **Domain Ports**: Only create interfaces (`Protocol` or `ABC`) where decoupling an external engine is required (e.g., `ILLMProvider`, `IVectorStore`).
- **Structured Error Handling**: Raise custom typed domain exceptions inheriting from `AppException`. Never return raw 500 error traces to the client.

### 4.2 Frontend Standards
- **Clean Component Hierarchy**: Separate UI presentational components from container / query hooks.
- **No Any in TypeScript**: Enforce strict TypeScript types for all API contracts, props, and states.
- **Accessibility by Default**: Ensure all interactive elements have ARIA labels, semantic HTML tags (`<nav>`, `<main>`, `<article>`), and clear keyboard focus rings.
- **Zero Placeholder Images**: All visual assets must be grounded, authentic Karnataka imagery or generated design assets.

---

## 5. Strict AI Grounding & Hallucination Rules

1. **Strict Evidence Grounding**: The conversational engine must answer tourist questions **exclusively** from retrieved and validated context chunks.
2. **Missing Evidence Mandate**: If the knowledge base does not contain the answer, the LLM must NEVER extrapolate or fabricate. It must reply:
   - English: *"Information is not available in the knowledge base."*
   - Kannada: *"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."*
3. **Verifiable Citations**: Every factual claim must reference a verified chunk ID, source document, and page number.
4. **Immutable Knowledge Generations**: Never write directly to active vector collections. Always build a new generation, run automated validation, and promote atomically.

---

## 6. Security & Privacy Rules

- **Zero Tourist Accounts**: Tourists never create accounts or log in. Do not collect PII or store client IP addresses in plain text.
- **Admin Authentication**: Use Argon2id for password hashing and short-lived JWT access tokens with rotating refresh tokens stored in HTTP-only, Secure cookies.
- **File Upload Security**: Validate all uploaded PDFs for MIME type (`application/pdf`), magic bytes (`%PDF-`), SHA-256 deduplication, and enforce a 50MB file size limit. Store files under randomized UUID filenames outside the web root.
- **Zero Plain-Text Secrets**: Never commit API keys, JWT secrets, or database passwords. Use `.env` and `.env.example`.

---

## 7. Database & Migration Rules

- **Alembic Exclusivity**: Never execute raw manual DDL in production. All schema changes must be versioned and committed as Alembic migrations.
- **UTC Timestamps**: All database timestamps must be stored in UTC (`TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP`).
- **Foreign Key Indexing**: Every foreign key constraint must be explicitly indexed.
- **Rollback Safety**: Migrations must implement both `upgrade()` and `downgrade()` where feasible.

---

## 8. What Must NEVER Be Done

1. **NEVER** introduce robotics, sensors, or hardware controller code.
2. **NEVER** force tourists to register, sign in, or provide phone numbers.
3. **NEVER** silently redesign the approved architecture or database schema.
4. **NEVER** skip automated unit or integration tests before completing a phase.
5. **NEVER** commit dummy mock fallback code into production paths (fail fast with structured health degradation instead).
6. **NEVER** proceed to the next phase without updating `Memory.md` and obtaining explicit review.
