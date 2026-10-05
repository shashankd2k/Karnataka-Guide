# Phase 18 Level 1 Optimization Walkthrough

**Status**: LEVEL 1 IMPLEMENTATION AND VERIFICATION CLOSEOUT COMPLETE WITH DOCUMENTED LIMITATIONS. Application real-time targets remain unmet; Phase 18 is NOT FINAL. (Level 2 proposal submitted awaiting approval — Level 2 NOT APPROVED; Level 3/4/Phase 19 NOT STARTED)  
**Target Hardware**: Intel Core i3-1115G4 @ 3.00GHz (2 Physical Cores, 4 Logical Threads), 8.0 GB RAM  
**Execution Environment**: Docker Desktop WSL2 Container Stack & Windows Bare-Metal Reference  
**Active Knowledge Generation**: `1a2c6365-1bee-4478-9599-a706ee5c7221` (Authoritative active generation strictly preserved: EXACTLY ONE active generation in MySQL)  
**Checkpoint Status**: `CHECKPOINT-P17 = FINAL ACCEPTED` (Phase 18 Checkpoint is NOT set final)  

---

## 1. Interruption Recovery & Scope Verification

- **Resumed From**: Retrieval Quality Benchmark (`backend/scratch/benchmark_retrieval.py`) & Section 12 Runtime Offline Sanity Verification.
- **Recovery Status**: **SUCCESS** (All historical benchmark artifacts, Section 12 run evidence, and database states preserved).
- **Retrieval Benchmark Recovered**: **YES** (persisted in `scratch/retrieval_benchmark_results.json`).
- **Completed Level 1-E Evidence**: Strictly preserved from `scratch/l1e_runaway_results.json` and individual `scratch/result_<QID>.json` files.
- **Production Changes Preserved & Reconciled**:
  - `backend/app/application/rag/prompt_builder.py` (Directives 7 & 8 preventing dialogue runaways)
  - `backend/app/infrastructure/llm/ollama.py` (Engine stop tokens and persistent `httpx.AsyncClient` with connection pooling)
  - `backend/app/core/config.py` (`OLLAMA_NUM_CTX = 1536`, `OLLAMA_NUM_THREAD = 2`, `OLLAMA_KEEP_ALIVE = "10m"`)
  - `backend/app/application/knowledge/embeddings.py` (Strict offline loading with `local_files_only=True` in standalone/offline mode; zero network fallback on missing cache)
  - `backend/app/application/rag/reranker.py` (Strict offline loading with `local_files_only=True` in standalone/offline mode; zero network fallback on missing cache)
  - *Note on `storage.py`*: Confirmed reverted to clean production code; test-only transient retry code was removed and git diff is zero.
- **Active Knowledge Generation Invariant**: Verified via strict read-only MySQL assertion (`task-18050`):
  - Exactly **ONE** active generation exists: `1a2c6365-1bee-4478-9599-a706ee5c7221` (`is_active = True`, status `GenerationLifecycleStatus.ACTIVE`, 22 Chroma chunks, 5/5 PDFs).
  - All other 15 historical generations remain `is_active = False`.

---

## 2. Retrieval Quality Guardrails Floor Verification & Coverage Distinction

Separation of historical 5-query timing artifact from canonical 24-query gold-standard coverage:

| Metric | Locked Quality Floor | 5-Query Timing Artifact | 24-Query Canonical Coverage | Status | Evidence Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hit@1 Rate** | $\ge 95.83\%$ | **100.0%** (5/5) | **95.83%** (23/24) | **PASS** | `run_isolated_rerank_experiment.py` (Q04 Rank 2) |
| **Recall@5 Rate** | $= 100.0\%$ | **100.0%** (5/5) | **100.0%** (24/24) | **PASS** | `run_isolated_rerank_experiment.py` |
| **Mean Reciprocal Rank (MRR)** | $\ge 0.9792$ | **1.0000** (5/5) | **0.9792** (23.5/24) | **PASS** | `run_isolated_rerank_experiment.py` |
| **Bibliography Intrusions** | $= 0$ leaks | **0** | **0** | **PASS** | `run_isolated_rerank_experiment.py` |
| **Grounding Policy Check** | Score $\ge -6.0$ | **PASS** | **PASS** ($\ge -6.0$, median +7.68) | **PASS** | `run_isolated_rerank_experiment.py` |
| **Answer Hallucinations** | $= 0$ | **NOT MEASURED** | **NOT MEASURED** | **NOT MEASURED** | Retrieval-only benchmark (no answers generated) |

> [!NOTE]
> A score $\ge -6.0$ is an evidence-grounding policy check, not proof of zero hallucinations. Because component retrieval benchmarks do not generate LLM answers, answer hallucination assessment is strictly `NOT MEASURED`. The zero-hallucination requirement remains outstanding for any later adoption decision.

---

## 3. Level 1-E Prompt Tightening & Runaway Prevention Matrix (7/7 Pass)

All seven identified runaway query prompts passed under resident Docker Ollama runner with the tightened prompt policy:

| Query ID | Status | Generated Tokens | Prompt Tokens | Prompt Eval (tok/s) | Gen Speed (tok/s) | Sentence Count | Runaway Detected | Truncated | Sentence Complete |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **P07** | **PASS** | 68 tok | 727 tok | 15.34 tok/s | 1.30 tok/s | 2 | False | False | True |
| **P08** | **PASS** | 101 tok | 896 tok | 6.83 tok/s | 1.97 tok/s | 4 | False | False | True |
| **P10** | **PASS** | 58 tok | 787 tok | 4.29 tok/s | 0.79 tok/s | 2 | False | False | True |
| **P21** | **PASS** | 100 tok | 832 tok | 26.43 tok/s | 1.79 tok/s | 2 | False | False | True |
| **P22** | **PASS** | 98 tok | 790 tok | 26.48 tok/s | 2.15 tok/s | 4 | False | False | True |
| **P24** | **PASS** | 61 tok | 868 tok | 11.79 tok/s | 1.00 tok/s | 2 | False | False | True |
| **P28** | **PASS** | 91 tok | 770 tok | 5.22 tok/s | 0.95 tok/s | 2 | False | False | True |

**Summary**: 0 runaways, 0 truncations, 0 incomplete sentences. Every response strictly adhered to 2–4 concise sentences answering only the tourist query.

---

## 4. Post-L1 Output Distribution, Context Headroom & Output Budget Audit

- **Output Sample Count**: 30 real production queries
- **P50 Output Tokens**: **93.0**
- **P90 Output Tokens**: **159.5**
- **P95 Output Tokens**: **174.6**
- **Max Output Tokens**: **186**
- **Mean Output Tokens**: **80.9**
- **Runaway Responses**: **0**
- **Truncated Responses**: **0** (under streaming budget 192)
- **Incomplete Sentences**: **0**
- **Headroom Verification against `num_ctx = 1536`**:
  - *Token Scope Clarification*: Maximum single-turn prompt input was 895 tokens in the 30-query baseline profiling, and reached 896 tokens for Query P08 under the tightened L1-E prompt formatting (`scratch/result_P08.json`). Multi-turn 5-turn history reached a maximum of 798 tokens (`scratch/real_5turn_context_budget.json`).
  - Max Single-Turn Input ($896$) + Valid Output Max ($186$) = $\mathbf{1082\text{ tokens}} \le 1536$ (**454 tokens / 29.6% headroom**).
  - Max Single-Turn Input ($896$) + Proposed Unified Output Budget ($192$) = $\mathbf{1088\text{ tokens}} \le 1536$ (**448 tokens / 29.2% headroom**).
  - Max 5-Turn History Input ($798$) + Valid Output Max ($186$) = $\mathbf{984\text{ tokens}} \le 1536$ (**552 tokens / 35.9% headroom**).
  - Max 5-Turn History Input ($798$) + Proposed Unified Output Budget ($192$) = $\mathbf{990\text{ tokens}} \le 1536$ (**546 tokens / 35.5% headroom**).
- **Safety Verdict**: **NUM_CTX 1536 = SAFE** (`num_ctx = 1024` remains strictly prohibited).

### Output Budget (`num_predict`) Audit & Supported Finding
- **Effective Configuration Recovery**:
  - `backend/app/infrastructure/llm/ollama.py`: `generate_text` (normal chat & voice) defaults to `num_predict: max_tokens or 128`. `generate_stream` (streaming chat) defaults to `num_predict: max_tokens or 192`.
  - `backend/app/core/config.py`: No `OLLAMA_NUM_PREDICT` setting exists; `max_tokens` is not passed by `tourist.py`.
  - Controlled benchmark used `num_predict: 128` (evaluating `generate_text`).
  - Source history confirms `128` was an existing historical production value in `generate_text` dating back to P0, while `192` was used in `generate_stream`. It was not a newly introduced diagnostic limit.
- **Completeness Analysis (Supported Finding)**:
  - The verified output distribution under natural generation (`scratch/production_output_results.json`) reports: P50: 93.0 tokens, P90: 159.5 tokens, P95: 174.6 tokens, Max complete output: 186 tokens.
  - **Supported Finding**: Six of 30 saved complete outputs exceed 128 tokens (`P14`: 186 tok, `P27`: 176 tok, `P16`: 173 tok, `P11`: 158 tok, `P13`: 143 tok, `P20`: 130 tok); this establishes risk, not a measured production truncation rate.
  - The observed maximum of 186 accommodates the observed distribution under testing, but does not guarantee future completeness at 192 for every possible query.
- **Resolution & Required Correction**:
  - Claiming `num_predict = 128` is "sufficient" based solely on the requested 2–4 sentence guideline is rejected by the empirical output distribution.
  - **Unresolved Completeness Limitation**: Normal chat and voice endpoints currently operate under an asymmetric 128-token default that presents a completeness risk for legitimate answers exceeding 128 tokens.
  - **Proposed Correction**: In Level 2 (when approved), unify `generate_text` to `num_predict = 192` (matching `generate_stream`). The proposed correction remains pending its existing approval gate.
  - **Context Headroom Verification**: Under `num_ctx = 1536`, an output budget of 192 tokens maintains **448 tokens / 29.2% safety headroom** on the maximum observed single-turn input ($896 + 192 = 1088 \le 1536$).
  - `num_ctx = 1536` and prompt directives 7 & 8 are retained. `num_ctx = 1024` remains strictly prohibited.
  - Because Level 2 is NOT APPROVED, no code modification has been made to production defaults.

---

## 5. Runner Stability Verification (100% Pass)

Sequential turns executed via normal application path (`scratch/runner_stability_results.json`):
- **Turn 1 (Cold Load)**: Load duration: **246.18s**, TTFT: 284.75s
- **Turn 2 (Warm Turn)**: Load duration: **23.45 ms**, TTFT: 321.36 ms (Ollama load duration < 200 ms)
- **Turn 3 (Warm Turn)**: Load duration: **161.78 ms**, TTFT: 2613.24 ms (Ollama load duration < 200 ms)
- **Verdict**: **RUNNER STABILITY = PASS** (Zero runner destruction, zero parameter alternation between paths).

---

## 6. Combined Level 1 Benchmarks vs P0 Baseline

| Metric / Scenario | P0 Baseline | Level 1 Measured | Status / Tag |
| :--- | :--- | :--- | :--- |
| **English Warm Text TTFT (Median)** | **2.46s** | **79.66s** (Min 25.30s, Max 106.96s) | `MEASURED` (Application streaming path) |
| **English Warm Text Total (Median)**| ~14s | **147.91s** (Min 67.85s, Max 344.51s) | `MEASURED` (Application streaming path) |
| **Kannada Warm Text TTFT (Median)** | **98.48s** | **> 300.00s** (Gateway Timeout) | `TIMEOUT_BOUND` |
| **English Voice Warm Server Audio** | **189.50s median** | **210.19s min / > 300.00s median** | `MEASURED / TIMEOUT_BOUND` |
| **Kannada Voice Warm Server Audio** | **> 300.00s** | **> 300.00s** (Gateway Timeout) | `TIMEOUT_BOUND` |
| **Ollama Cold Load** | ~120–212s | **246.18s** | `MEASURED` |
| **Direct Ollama Engine Load + Prompt Eval** | 258.24 ms (P0-equivalent direct engine) | **242.94 ms (0.24s)** | `DERIVED_FROM_MEASURED` (Direct engine port 11434; not application TTFT) |
| **Generation Speed** | 2.55 – 5.60 tok/s | **0.13 – 2.20 tok/s** (Docker under swap) | `MEASURED` |
| **Ollama RSS** | ~2.2 GB | **2.44 GB** | `MEASURED` |
| **Backend RSS** | ~366 MB idle | **579.3 MB idle** | `MEASURED` |
| **WSL Available RAM** | ~500–600 MB | **394.5 – 597.6 MB** | `MEASURED` |
| **WSL Swap Used** | 711 – 807 MB | **1024.0 MB** (100% full swap limit) | `MEASURED` |

---

## 7. Full Regression Testing & System Verification

- **Historical Baseline Test Suites (Reused Historical Evidence)**:
  - **Backend Test Suite**: **283 / 283 PASSED (100%)**, 0 failed, 0 skipped, duration: 427.70s (`REUSED HISTORICAL EVIDENCE`). *Note on Raw Provenance*: The raw task execution log for this 283-test run has not been recovered from the current local task directory; it originates as recorded historical benchmark evidence from Phase 17 / earlier Level 1 audit documentation.
  - **Frontend Test Suite**: **47 / 47 PASSED (100%)**, 9 test files, duration: 55.84s (`REUSED HISTORICAL EVIDENCE`).
  - **Frontend Production Build**: **PASS** (`tsc -b && vite build` in 10.79s, 0 errors) (`REUSED HISTORICAL EVIDENCE`).
- **Offline Model Loader Verification & Defect Resolution (Reused Evidence from Task-18111)**:
  - **False-Positive Verifier Defect Discovery**:
    - The inline verification check in `scratch/verify_offline_loading.py` previously raised `AssertionError("Should have failed in offline mode!")` inside a `try` block, followed by `except Exception as e:` which caught any exception and checked `if "offline" in str(e).lower()`.
    - This created a false-positive vulnerability where an unexpected successful model load would trigger `AssertionError`, which was then caught by `except Exception`, potentially printing `PASS` if "offline" appeared anywhere in the error message.
  - **Verifier Correction & Implementation**:
    - Rewrote `scratch/verify_offline_loading.py` using a strict `try / except OSError as exc: / else: raise AssertionError(...)` structure.
    - Catches only the expected loader exception (`OSError` from Hugging Face hub / sentence-transformers), placing unexpected-success failures strictly outside the exception handler.
    - Unrelated import, syntax, argument, and configuration errors are treated strictly as failures.
    - Added an active network call guard: monkeypatched `socket.socket.connect` during offline testing to raise `RuntimeError("Network access attempted during offline verification")`, ensuring zero network attempts occur.
    - Added unit test validation ensuring that `SentenceTransformer` and `CrossEncoder` are called strictly once with `local_files_only=True` without calling any unrestricted online fallback.
  - **Empirical Execution & Raw Evidence Recovery**:
    - Recovered raw evidence from `task-18044`: The actual execution log confirmed genuine `OSError: Can't load tokenizer for 'nonexistent/model-that-does-not-exist'` raised by the Hugging Face hub, confirming the underlying implementation in `embeddings.py` and `reranker.py` was sound despite the script defect.
    - Executed the corrected verifier in `karnatakaguide-backend-1` via `task-18111` (reused evidence from earlier work session; exit code 0, **PASS**): Confirmed cached models (`all-MiniLM-L6-v2` and `cross-encoder/ms-marco-MiniLM-L-6-v2`) load locally, missing models strictly raise `OSError`, zero socket connections are attempted, and no online fallback is called.
- **Pytest Suite Focused Test Scope Clarification (Reused Evidence from Task-17967)**:
  - Executed focused pytest suite targeting embeddings and reranking via `task-17967` (reused evidence from earlier work session; duration 0.42s):
    - **4 focused unit tests PASSED** (`test_embedding_dimensions`, `test_embedding_normalization`, `test_rerank_ordering`, `test_rerank_empty_candidates`).
    - **279 tests DESELECTED** by the `-k "embedding or rerank"` filter.
  - These tests assert embedding vector dimensionality (384-d), vector normalization ($L_2 \approx 1.0$), and candidate ranking order using **mock model objects**.
  - They **do not** assert offline-specific Hugging Face hub network isolation or model loading behavior. They are described strictly as embedding/retrieval functional unit tests, not offline loader verification tests.
- **Docker Compose Topology**: All 4 containers healthy (`karnatakaguide-backend-1`, `karnatakaguide-frontend-1`, `karnatakaguide-mysql-1`, `karnatakaguide-ollama-1`).
- **Offline Model Preflight (Reused Historical Evidence)**: **PASS** (`deployment/preflight_models.py --verify-offline` verified 7/7 local models with zero cloud AI).
- **Active Knowledge Generation Invariant (Reused Evidence from Task-18050)**: **PASS** (Strict read-only DB query via `task-18050` from earlier work session verified **exactly ONE** active generation in MySQL: `1a2c6365-1bee-4478-9599-a706ee5c7221`, status `ACTIVE`, `is_active = True`).
- **Lean-Code Review (Current Closeout)**: **PASS** (Zero unnecessary abstractions, zero debug prints, no new unapproved dependencies, clean persistent HTTP client lifecycle, and `backend/app/application/documents/storage.py` clean/reverted).

---

## 8. Application Usability Classification & Level 2 Recommendation

#### Real-Time UX Evaluation & Usability Classification:
- **Historical Streaming Text TTFT (Docker Container Stack)**:
  - *Measurement Boundary & Route Clarification*: Measured against the streaming endpoint `/api/v1/tourist/chat/stream` with `is_stream: true` in `scratch/p0_results.json`. Non-streaming responses on `/api/v1/tourist/chat` measure total roundtrip response latency and cannot establish client-observed streaming token arrival.
  - **English Text Application TTFT (Warm Median)**: **79.66 seconds** (Warm Mean: 72.00s, Min: 25.30s, Max: 106.96s) — **FAILS REAL-TIME TEXT REQUIREMENT** (Target: $\le 2\text{–}3\text{s}$).
    - *Classification Correction*: Removed "Usable with Noticeable Delay" as an acceptance classification for the 79.66-second result. On the target hardware (Intel Core i3-1115G4, 2 physical cores, 8 GB host RAM, Docker WSL2 with 1024 MB swap limit), a 79.66-second TTFT fails interactive real-time text usability.
  - **Kannada Text Application TTFT (Warm)**: **> 300.00 seconds** (Nginx Gateway Timeout) — **FAILS REAL-TIME TEXT REQUIREMENT** (Target: $\le 2\text{–}3\text{s}$).
- **Historical Voice Turnaround (Docker Container Stack)**:
  - **English Voice: Server Time to Audio Available (Warm Median)**: **> 300.00 seconds** (Min measured: **210.19s**; P0 historical median: **189.50s**) — **FAILS REAL-TIME VOICE REQUIREMENT** (Target: $\le 4.0\text{s}$).
  - **Kannada Voice: Server Time to Audio Available**: **> 300.00 seconds** (Gateway Timeout) — **FAILS REAL-TIME VOICE REQUIREMENT** (Target: $\le 4.0\text{s}$).
- **Client Playback Start**: Tagged strictly as **`NOT_MEASURED`** (no audible playback listener or browser audio event captured).
- **Comparison Boundary Warning**: Historical application TTFT cannot be compared directly with the ~0.24s direct Ollama engine load-plus-prompt-evaluation sum. The direct engine metric reflects isolated HTTP inference over port 11434 (`stream: False`), omitting Nginx, session resolution, DB persistence, hybrid retrieval, reranking, and translation.
- **Model Residency Scoping (`keep_alive = "10m"`)**:
  - `keep_alive = "10m"` retains the runner process in memory during the configured 10-minute residency window (`load_duration < 200ms` across warm turns).
  - It **does not** eliminate cold loads after window expiration, engine/daemon restarts, or loss of residency due to memory pressure eviction.
- **Level 2 Necessity & Governance**:
  - **Level 2 Needed**: **YES** (The current pipeline fails real-time requirements in both languages for text and voice).
  - **Proposed Level 2 scope — implementation not approved**: Proposed initial candidates are strictly low-risk, verified compute reductions: Cross-Encoder reranker candidate reduction (15 $\rightarrow$ 10 subject to locked retrieval quality floors) and NLLB input-aware token capping. Active-generation caching and parallel Dense/BM25 retrieval are deferred. Unifying the output budget (`num_predict = 192`) is kept as a separate completeness decision with its own approval requirement.
  - **Level 2 remains NOT APPROVED. Level 3, Level 4, and Phase 19 are NOT STARTED. Awaiting explicit user approval.**

---

## 9. Apples-to-Apples Controlled Benchmark & Offline Isolation Results

### Controlled A/B Benchmark (Target Hardware: Intel Core i3-1115G4)
Tested under identical model-residency conditions on Belur grounded query (`scratch/controlled_ab_results.json`):

> [!NOTE]
> **Measurement Boundary, Metric Renaming & Scope Clarification**:
> 1. **Measurement Boundary**: The controlled A/B benchmark measured direct HTTP inference from `karnatakaguide-backend-1` to `karnatakaguide-ollama-1` over port 11434 (`/api/generate` with `stream: False`). It **did not** include the end-to-end tourist application path (Nginx gateway, session lookup, DB message persistence, BM25 + Dense hybrid retrieval, Cross-Encoder reranking, or NLLB translation). Its generation speed and duration observations cannot be generalized to the full application pipeline.
> 2. **Timing Metric Renaming (`~0.24s`)**: The benchmark evaluated `stream: False` and calculated `load_duration + prompt_eval_duration` from Ollama's response JSON. This metric is now formally renamed to:
>    **“Engine load plus prompt-evaluation duration”**
>    and tagged as **`DERIVED_FROM_MEASURED`**. It represents an internal engine timing sum, not an observed first-token arrival, and does not include an explicitly measured first generated token. It does not establish application TTFT or real-time communication.
> 3. **Prompt Evaluation Speed**: The reported prompt evaluation rate (~1,938–2,436 tok/s) reflects **Ollama prompt prefix / KV cache hits** across repeated identical prompts. Uncached CPU prompt evaluation throughput on this hardware profile is ~28–30 tok/s (measured in DIAG-B).
> 4. **Historical P0 Latency Reconciliation**: The historical P0 warm median total duration of ~13.48s (~14s) was recorded in the Docker thread benchmark (`scratch/docker_thread_results.json`) under `default/auto` (`num_thread=0`, 53 tokens generated at 4.29 tok/s). The 8.87s figure was from diagnostic test `DIAG-B` generating a shorter response (~35 tokens) on an unburdened runner.
> 5. **Memory Attribution**: The observed memory reductions (Ollama RSS: -192.5 MB, Swap: -148.5 MB) reflect the **aggregate effect of the Level 1 bundle** (`num_ctx = 1536`, `num_thread = 2`, tightened prompt length, stop tokens), not solely isolated to `num_ctx`.
> 6. **Swap Metrics**: WSL2 SwapTotal is 1024.0 MB. Control A median swap used was 956.5 MB (**93.4% full**). Control B median swap used was 808.0 MB (**78.9% full**). `pswpin_diff` and `pswpout_diff` in `controlled_ab_results.json` are **interval deltas** for that specific query, whereas `/proc/vmstat` values are cumulative boot counters.

| Metric | Control A (P0-Equivalent: ctx=2048, thread=0, Base Prompt) | Control B (Level 1: ctx=1536, thread=2, L1-E Prompt + Stops) | Delta / Improvement | Measurement Type |
| :--- | :--- | :--- | :--- | :--- |
| **Engine load plus prompt-evaluation duration (Median)** | 258.24 ms (0.26s) | 242.94 ms (0.24s) | **-15.30 ms (-5.9% faster)** | `DERIVED_FROM_MEASURED` (load_duration + prompt_eval_duration) |
| **Gen Speed (Median)** | 3.87 tok/s | 4.48 tok/s | **+0.61 tok/s (+15.8% throughput)** | `MEASURED` |
| **Total Duration (Median)** | 21,481.18 ms (21.48s) | 12,548.15 ms (12.55s) | **-8,933 ms (-41.6% faster)** | `MEASURED` |
| **Prompt Eval Speed (Median)** | 1,938.28 tok/s | 2,436.52 tok/s | **+498.24 tok/s (+25.7%)** | `MEASURED` (KV cache hits) |
| **Tokens Generated (Median)** | 57 tokens (hit 128 tok runaway in 2/5 runs) | 52 tokens (0 runaways in 5/5 runs) | **Clean stop preserved** | `MEASURED` |
| **WSL Swap Used (Median)** | 956.5 MB (93.4% of 1024MB SwapTotal) | 808.0 MB (78.9% of 1024MB SwapTotal) | **-148.5 MB swap freed** | `MEASURED` |
| **WSL Available RAM (Median)** | 393.4 MB | 454.5 MB | **+61.1 MB RAM freed** | `MEASURED` |
| **Ollama RSS (Resident)** | 2,910.8 MB | 2,718.3 MB | **-192.5 MB process memory** | `MEASURED` |

### Section 12: Runtime Offline Isolation Sanity Verification (Persisted Task-17662)
*Script*: `scratch/run_section12_offline_sanity.py`, *Task Log*: `task-17662.log`

> [!NOTE]
> **Section 12 Attempt Reconciliation & Boundary Scope**:
> - **Attempt History**:
>   - `task-17541` (Attempt 1): Timed out at 120s due to huggingface hub retry loop during sentence-transformers import with default route blocked.
>   - `task-17628` (Attempt 2a): Timed out at 120s due to cold Ollama runner reload under memory contention.
>   - `task-17640` (Attempt 2b): Backend completed in ~115s, but script assertion failed because it checked `chat_data.get("message")` instead of `chat_data.get("answer")`.
>   - `task-17662` (Attempt 3): Passed 100% (exit code 0, completed in 118.48s, validated answer, citations, and route restoration).
>   - *Narrative vs Task Count*: The previous narrative referred to "three attempts" because Attempt 2 was immediately retried after fixing the script assertion field mismatch. All 4 tasks were recorded in `.system_generated/tasks/`.
> - **Isolation Boundary**: Default route deletion was applied strictly inside `karnatakaguide-backend-1` (`ip route del default`). Ollama and MySQL containers remained on private Docker bridge network without external WAN egress dependencies.
> - **Residency Terminology**: The `/api/tags` probe verified model availability and Ollama bridge connectivity; active model runner residency in RAM was verified by Ollama `load_duration` (< 200 ms) and `/api/ps`.
> - **Timing & Completion Order**: The grounded response and citations were completely received at `[11:32:14]`, and default route restoration was initiated at `[11:32:14]` and completed at `[11:32:17]` via `172.18.0.1`.

- **External WAN Egress**: `BLOCKED` (default route deleted inside backend, connection to `8.8.8.8` failed with Errno 101 Network unreachable) — `MEASURED` (Task ID: `task-17662`).
- **Backend -> Ollama Connectivity**: `PASS` (`phi3:mini` responsive over private Docker bridge network) — `MEASURED`.
- **Backend -> MySQL Connectivity**: `PASS` (`SELECT 1: 1` over private Docker bridge network) — `MEASURED`.
- **End-to-End Grounded Query**: `PASS` (`/api/v1/tourist/chat` response field `answer`: `"The Chennakeshava Temple at Belur was commissioned by King Vishnuvardhana in the year 1117 CE. [1]"` in 118.48s under active isolation) — `MEASURED`.
- **Authoritative Citations**: `PASS` (Citations array containing `[[1]] Belur_Halebidu_Hoysala_Guide.pdf (p. 2)`) — `MEASURED`.
- **Default Route Restoration**: `PASS` (Default route restored cleanly via `172.18.0.1`, confirmed via `/proc/net/route`) — `MEASURED`.
- **Overall Status**: **RUNTIME OFFLINE SANITY: PASS**.

---

## 10. Application-Path Warm Streaming Sanity Measurements (Task-18132)

*Artifacts*: `scratch/run_application_warm_stream.py`, `scratch/application_warm_stream_results.json`, Task Log: `.system_generated/tasks/task-18132.log`  
*Execution Scope*: Single-sample bounded warm streaming request per language executed against the frozen public application endpoint `/api/v1/tourist/chat/stream`.

> [!NOTE]
> **Measurement Boundary, Scope Limitation & Execution Analysis**:
> 1. **Accurate Execution Summary**: Exactly two requests were executed (`en` and `kn`), with zero observed first tokens recorded for either language, resulting in two timeouts (`TIMEOUT_BOUND`). The harness exit code 0 indicates only that the failure outcomes were recorded successfully by the test harness; it does not establish application success or responsive streaming.
> 2. **Memory-Pressure Diagnosis**: The checks recorded 79.9% (818.3 MB) and 81.9% (839.1 MB) swap occupancy, which must be distinguished from historical runs with 100% swap saturation (1024.0 MB full). Memory pressure remains a plausible contributor to latency rather than a proven sole cause, unless stronger evidence establishes causation.
> 3. **Kannada Elapsed Time Breakdown & Metric Separation**:
>    - The client harness configured an HTTP socket timeout of 180s in `urllib.request.urlopen(req, timeout=180)`.
>    - Stage-level durations and log-derived intervals must be separated from inferred mechanisms:
>      - Approximately **32.86 seconds** of NLLB model loading from disk/cache into RAM (measured duration from backend logs `05:34:40`–`05:35:12`);
>      - The subsequent approximately **81.43-second** interval to query-translation completion (`kn -> en`) (log-derived interval `05:35:12`–`05:36:34`);
>      - **5.44 seconds** of reported hybrid RAG retrieval (`05:36:34`–`05:36:39`);
>      - An approximately **84-second** Ollama inference request (logged in Ollama access logs as `POST /api/generate 200 1m24s` `05:36:39`–`05:38:04`).
>    - These stages suggest substantial pipeline delays. Adding them highlights the total time elapsed before translated tokens could be produced, but adding them does not prove the exact timeout mechanism.
>    - The client-side socket read timed out at 204.46s (total script elapsed 205.40s) as Ollama finished and client socket aborted.
> 4. **English / Kannada Server-Side Overlap Analysis**:
>    - Ollama logs show the English runner task was cancelled at `05:34:35Z` after client timeout (`[GIN] 2026/09/27 - 05:34:35 | 500 | 2m26s`, `srv stop: cancel task, id_task = 0`).
>    - The Kannada request arrived at the backend at `05:34:39Z` (4 seconds later). While the Ollama runner task was aborted, backend process cleanup and swap occupancy remained at 81.9% full, presenting a potential concurrency/teardown overlap and comparison limitation.

| Parameter | English Warm Stream (`en`) | Kannada Warm Stream (`kn`) | Measurement Type |
| :--- | :--- | :--- | :--- |
| **Query** | "Who commissioned the Chennakeshava Temple at Belur and in what year?" | "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವ ವರ್ಷದಲ್ಲಿ ನಿರ್ಮಿಸಿದರು?" | Grounded Heritage Query |
| **Route** | `/api/v1/tourist/chat/stream` | `/api/v1/tourist/chat/stream` | Frozen Public SSE Route |
| **Model & Options** | `phi3:mini` (`ctx=1536, thread=2, predict=192, keep_alive=10m`) | `phi3:mini` (`ctx=1536, thread=2, predict=192, keep_alive=10m`) | Effective Production Config |
| **Residency Prior to Request** | Ollama warm (`phi3:mini` resident in RAM) | Ollama warm, NLLB initially unloaded | `MEASURED` |
| **Starting WSL2 Available RAM** | 463.6 MB | 329.2 MB | `MEASURED` |
| **Starting WSL2 Swap Used** | 818.3 MB / 1024.0 MB (79.9% full) | 839.1 MB / 1024.0 MB (81.9% full) | `MEASURED` |
| **First Nonempty Visible Token** | `None` (0 observed tokens; Client socket read timeout reached after 180s timeout) | `None` (0 observed tokens; Client socket read timeout reached after 180s timeout) | `TIMEOUT_BOUND` |
| **Total Duration** | **180.22 seconds** | **205.40 seconds** | `TIMEOUT_BOUND` |
| **Result / Status** | `TIMEOUT_BOUND (> 180s)` | `TIMEOUT_BOUND (> 180s)` | `TIMEOUT_BOUND` |

---

## 11. Level 2 Isolated Reranker Candidate Experiment (15 vs 10 Candidates)

### 11.1 Experiment Specification & Governance Constraints
- **Authorization**: Solely authorized for the isolated benchmark harness, focused validation, result artifacts, and documentation updates.
- **Production Default Preserved**: The production configuration in `backend/app/core/config.py` remains strictly at `RETRIEVAL_RERANK_CANDIDATES = 15` (file SHA-256 hash verified: `357d6274450ddde14ec746e6e62f53337a62b3f835babab6303ba493e0a080c4`).
- **Active Generation Invariant (Read-Only)**: Exactly ONE active generation in MySQL: `1a2c6365-1bee-4478-9599-a706ee5c7221` (Status `ACTIVE`, `is_active = True`).
- **Benchmark Process & Architecture**:
  - Single benchmark process with single loaded `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")` instance shared by both arms.
  - Cold model initialization measured separately (538.04 ms).
  - Initial warm-up query executed and explicitly excluded from measured dataset.
  - Slicing location verified: RRF candidate generation produces identical candidate order; fused candidates prepared once per query and fresh independent copies provided to Arm 15 (`[:15]`) and Arm 10 (`[:10]`).
  - Score-independent filtering (`filter_noise_chunks`) and order-dependent duplicate suppression (`suppress_duplicate_chunks`) preserved in their current production positions.
  - Alternating serial execution across 24 queries with 2 paired repetitions:
    - Repetition 1: Arm 15 -> Arm 10
    - Repetition 2: Arm 10 -> Arm 15
    - Total measured arm executions: **96** (48 Arm 15, 48 Arm 10; 48 paired repetition pairs).
  - Incremental persistence after each query pair to `scratch/level2_rerank_experiment/benchmark_results.json`.

### 11.2 Empirical Reranker Latency Results (96 Executions, 48 Paired Repetitions)

| Arm / Metric | Count | Mean (ms) | Median (ms) | Min (ms) | Max (ms) | P90 (ms) | P95 (ms) | StDev (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Arm 15 (Production Default)** | 48 | 1,106.46 | 944.15 | 807.02 | 2,385.50 | 1,531.09 | 1,602.49 | 355.82 |
| **Arm 10 (Experimental)** | 48 | 767.93 | 645.76 | 531.83 | 1,562.47 | 1,153.03 | 1,360.66 | 263.47 |
| **Paired Delta ($T_{15} - T_{10}$)** | 48 | **+338.53** | **+292.40** | -487.17 | +1,683.98 | **+691.82** | **+987.10** | 362.60 |

- **Absolute Savings**: Arm 10 saves a **median of 292.40 ms** (~292 ms) and a **mean of 338.53 ms** per query on Cross-Encoder reranking.
- **Variability**: Latency savings ranged from -487.17 ms to +1,683.98 ms, with 81.25% of paired runs demonstrating positive savings.
- **Cold Initialization**: Cross-Encoder cold load took **538.04 ms**, recorded separately from warm inference.

### 11.3 Quality Floor Verification & Regression Audit (Canonical 24 Queries)

| Quality Metric | Locked Quality Floor | Arm 15 Result | Arm 10 Result | Floor Status | Quality Regressions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hit@1 Rate** | $\ge 95.83\%$ | **95.83%** (23/24) | **95.83%** (23/24) | `PASS` | 0 regressions (identical ranks) |
| **Recall@5 Rate** | $= 100.0\%$ | **100.0%** (24/24) | **100.0%** (24/24) | `PASS` | 0 regressions (identical ranks) |
| **Mean Reciprocal Rank (MRR)** | $\ge 0.9792$ | **0.9792** | **0.9792** | `PASS` | 0 regressions (identical ranks) |
| **Bibliography Intrusions** | $= 0$ leaks | **0** | **0** | `PASS` | 0 regressions |

- **Quality Regression Count**: **ZERO (0)** across all 24 queries and all 96 arm executions.
- **Rank Comparison**: Every single query produced identical ranks for expected evidence between Arm 15 and Arm 10 (23 queries at Rank 1, Q04 at Rank 2).

### 11.4 Grounding Guard Policy & Fallback Verification
- **In-Corpus Grounding Policy Check**:
  - Evaluated all 24 queries through `GroundingGuard(min_score_threshold=-6.0)`.
  - All 24 queries produced top Cross-Encoder scores $\ge -6.0$ (range: -3.11 to +10.64; median: +7.68) for both arms, resulting in `is_grounded = True`.
- **Synthetic Out-of-Corpus Fallback Check**:
  - Evaluated query: *"What is the ticket price for the Eiffel Tower in Paris?"*
  - Arm 15 Top Score: **-10.852** (< -6.0) $\rightarrow$ `is_grounded = False`, fallback message: `"Information is not available in the knowledge base."` (`PASS`).
  - Arm 10 Top Score: **-10.852** (< -6.0) $\rightarrow$ `is_grounded = False`, fallback message: `"Information is not available in the knowledge base."` (`PASS`).
- **Answer Hallucination Assessment**:
  - Labeled **`NOT MEASURED`** because this isolated experiment does not generate LLM answers.
  - A score $\ge -6.0$ is a grounding-policy check, not proof of zero hallucinations. The existing zero-hallucination requirement remains outstanding for any later adoption decision.

### 11.5 Evaluation & Final Recommendation
- **Finding**: Reducing Cross-Encoder candidates from 15 to 10 reliably saves **~292 ms median reranking latency** while preserving 100% of canonical retrieval quality (zero regressions, Hit@1 = 95.83%, Recall@5 = 100%, MRR = 0.9792, Bib Leaks = 0).
- **Recommendation**: The 10-candidate setting is a **viable candidate for a separately approved production change**.
- **Scope & Governance Boundaries**:
  - Adopting candidate reduction to 10 **does not establish that Phase 18 application real-time targets are met** (overall voice pipeline remains bounded by Ollama inference ~12–86s and NLLB translation ~81s).
  - Production default remains at **15**. Any change to production configuration requires separate explicit approval.
  - Other Level 2 proposals, the 128-to-192 output budget change, Level 3/4, and Phase 19 remain **UNAPPROVED**. Phase 18 remains **NOT FINAL**.

---

> [!IMPORTANT]
> **STOP GATE ACTIVE**: Level 1 closeout is complete with documented limitations; isolated Level 2 reranker candidate experiment (15 vs 10) is verified and recorded.
> In strict accordance with user directives:
> - **PRODUCTION DEFAULT REMAINS AT 15**.
> - **DO NOT IMPLEMENT LEVEL 2 PRODUCTION CHANGES**.
> - **DO NOT START LEVEL 3 OR LEVEL 4**.
> - **DO NOT START PHASE 19**.
> - **DO NOT SET CHECKPOINT-P18 FINAL**.
> - **AWAITING EXPLICIT USER REVIEW**.
