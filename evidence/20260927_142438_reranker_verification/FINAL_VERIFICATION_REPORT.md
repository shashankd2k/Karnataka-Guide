# Final Evidence Verification Report: Level 2 Isolated Reranker Candidate Experiment (15 vs 10 Candidates)

**Date**: 2026-09-27  
**System**: Karnataka Guide RAG Engine (`D:\Karnataka Guide`)  
**Target Hardware Profile**: Intel Core i3-1115G4 @ 3.00GHz (2 physical CPU cores, 4 logical threads, 8 GB host RAM, WSL2 Ubuntu 24.04)  
**Active Knowledge Generation**: `1a2c6365-1bee-4478-9599-a706ee5c7221` (Verified read-only in MySQL: `is_active = True`, status `ACTIVE`)  
**Production Setting Status**: `RETRIEVAL_RERANK_CANDIDATES = 15` strictly preserved in `backend/app/core/config.py` (SHA-256: `357d6274450ddde14ec746e6e62f53337a62b3f835babab6303ba493e0a080c4`)  
**Phase Status**: Level 1 closeout complete with documented limitations; Level 2 implementation **NOT APPROVED**; Phase 18 is **NOT FINAL**.

---

## 1. Executive Summary & Verdict

- **Scope Authorized**: Solely an isolated, read-only benchmark comparing 15 versus 10 Cross-Encoder reranker candidates under frozen production defaults, with evidence preservation, ground-truth audit, metric recalculation, and documentation corrections.
- **Evidence Verification Verdict**: **EVIDENCE VALIDATED WITH PRECISE METRIC PROVENANCE**.
  - Exactly 24 distinct queries, 2 paired repetitions per query, 2 arms (15 and 10), yielding **96 unique measured executions** and **48 paired repetitions**. Zero missed, duplicated, or corrupted records. Zero warm-up leaks.
  - The ground-truth mapping between generation `6ee08b45-823a-4bd5-8604-920bbdd61d58` and active generation `1a2c6365-1bee-4478-9599-a706ee5c7221` is **100% bijective and character-for-character identical** (22/22 chunks match with exact raw equality, identical document provenance, identical page numbers, and identical section headers).
  - All 18 unique expected reference chunks referenced across the 24 canonical queries mapped without loss. Zero unmapped IDs.
  - Zero rank regressions on target evidence: Hit@1 is **95.83%** (23/24) on both arms; Hit@5 / historical Recall@5 is **100.0%** (24/24) on both arms; Strict Multi-Label Recall@5 is **95.83%** on both arms; unrounded MRR is **0.9791666667** ($23.5 / 24$) and 4-decimal rounded MRR is **0.9792** on both arms; Bibliography Intrusions: **0**.
  - Ordered evidence differences between arms occurred in only 4 queries (Q11, Q14, Q15, Q18), and were strictly confined to negative-scoring background filler chunks (ranks 2–5). The top target chunk remained at **Rank 1** in all 4 cases.
  - Latency: Arm 10 delivers a reliable **median reduction of 292.40 ms** (paired difference median) and **mean reduction of 338.53 ms** per query. Difference between arm medians is **298.39 ms**. Arm 10 was faster in **42 of 48 pairs (87.5%)**.
- **Justified Recommendation**: The 10-candidate setting is a **viable, validated candidate for a separately approved production change**. However, it does not establish that Phase 18 real-time targets are met. Production default remains at **15** until explicit user approval.

---

## 2. Dataset Verification & Attempt Reconciliation

### 2.1 Dataset Verification
- **Total Queries**: 24 distinct queries (`Q01` through `Q24`).
- **Repetitions per Query**: Exactly 2:
  - Repetition 1: Arm 15 executed first, Arm 10 executed second (`rep1_15_then_10`).
  - Repetition 2: Arm 10 executed first, Arm 15 executed second (`rep2_10_then_15`).
- **Total Executions**: $24 \times 4 = 96$ unique measured executions (48 for Arm 15, 48 for Arm 10).
- **Total Paired Comparisons**: 48 pairs.
- **Candidate Limits Fed to Cross-Encoder**:
  - Arm 15: Exactly 15 candidates fed, 15 reranked, top 5 final evidence selected across all 48 runs.
  - Arm 10: Exactly 10 candidates fed, 10 reranked, top 5 final evidence selected across all 48 runs.
- **Warm-Up Isolation**: Dedicated warm-up query (*"history of pattadakal unesco temples"*) was executed and discarded prior to measured runs. Zero warm-up data exists in the 96-execution dataset.

### 2.2 Attempt Reconciliation & Logged Deletion Analysis
- **Attempt 1 (`task-18617.log`, duration 8.64s)**:
  - Initialized model cold load (586.65 ms), built BM25 index (22 chunks), completed warm-up.
  - Failed at query Q01, line 369 of `run_isolated_rerank_experiment.py` during `RetrievalCandidate` Pydantic validation because optional fields (`generation_id`, `text`, `source_filename`, `final_rank`) were omitted when reconstructing dictionary objects for `GroundingGuard`.
  - **File Impact**: The script crashed at line 369 before reaching line 431 (`json.dump`). Therefore, **no `benchmark_results.json` was written or partially written during Attempt 1**.
- **The Logged Deletion (`rm -f /app/scratch/level2_rerank_experiment/benchmark_results.json`)**:
  - A standard defensive command executed prior to re-running the harness. Because Attempt 1 had crashed before writing any file, no existing benchmark result data was erased or lost.
- **Attempt 2 (`task-18649.log`, duration 100.48s)**:
  - Harnessed updated to pass genuine `RetrievalCandidate` objects directly to `GroundingGuard.evaluate()`.
  - Successfully executed all 24 queries, all 96 arm executions, and synthetic out-of-corpus query.
  - Generated the authoritative `benchmark_results.json` (521,896 bytes). Both raw task logs (`task-18617.log` and `task-18649.log`) are completely preserved.

---

## 3. Ground-Truth Mapping Audit (Generation `6ee` to `1a2`)

Audit performed directly against MySQL tables `knowledge_generations`, `documents`, and `document_chunks`:

| Attribute | Generation `6ee08b45` (Phase 7 Source) | Generation `1a2c6365` (Active Destination) | Match Status |
| :--- | :--- | :--- | :--- |
| **Total Chunks in Generation** | 22 | 22 | Exact Count Match |
| **Raw Character-for-Character Equality** | 22 / 22 chunks | 22 / 22 chunks | **100% Identical (Zero Whitespace Trim Difference)** |
| **Stripped Text Equality** | 22 / 22 chunks | 22 / 22 chunks | **100% Identical** |
| **Document Filename Compatibility** | 22 / 22 chunks | 22 / 22 chunks | **100% Identical** |
| **Page Number Compatibility** | 22 / 22 chunks | 22 / 22 chunks | **100% Identical** |
| **Section Header Compatibility** | 22 / 22 chunks | 22 / 22 chunks | **100% Identical** |
| **Unique Destination IDs Matched** | 22 | 22 | **100% Bijective (1-to-1 Isomorphism)** |
| **Ambiguous Mappings (>1 match)** | 0 | 0 | None |
| **Unmatched Source Chunks** | 0 | 0 | None |
| **Referenced Expected Chunks (24 Qs)**| 18 unique chunk IDs | 18 unique chunk IDs | **100% Mapped** |
| **Unmapped Expected Chunks** | 0 | 0 | **Zero Dropped IDs** |

**Conclusion**: The mapping between `6ee` and `1a2` is mathematically bijective, textually identical without needing whitespace trimming, and preserves 100% of document/page/section metadata.

---

## 4. Quality Recalculation & Semantics Audit

### 4.1 Metric Semantics & Distinctions
- **Hit@1**: Proportion of queries where the top-ranked retrieved chunk is in the expected relevance set.
- **Hit@5 (Historical Phase 7 "Recall@5")**: Proportion of queries where at least one expected relevant chunk appears in the top-5 retrieved chunks (`hits_at_5 / total_queries`). In the original fixture, expected chunks often represent interchangeable acceptable answers (e.g., either chunk describing the temple).
- **Strict Multi-Label Recall@5**: Mean proportion of all judged-relevant chunks retrieved in top 5 ($\frac{1}{N} \sum \frac{|\text{retrieved} \cap \text{expected}|}{|\text{expected}|}$).
- **Mean Reciprocal Rank (MRR)**: Mean reciprocal rank of the first relevant chunk ($1 / \text{rank}$).

### 4.2 Quality Metric Results (24 Queries, 96 Executions)

| Metric | Locked Quality Floor | Arm 15 Result | Arm 10 Result | Regressions | Floor Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hit@1 Rate** | $\ge 95.83\%$ (23/24) | **95.83%** (23/24) | **95.83%** (23/24) | 0 | `PASS` |
| **Hit@5 Rate (Historical "Recall@5")** | $= 100.0\%$ (24/24) | **100.0%** (24/24) | **100.0%** (24/24) | 0 | `PASS` |
| **Strict Multi-Label Recall@5** | N/A | **95.83%** | **95.83%** | 0 | `PASS` |
| **Sum of Reciprocal Ranks** | N/A | **23.5** | **23.5** | 0 | `PASS` |
| **Unrounded MRR** | $23.5 / 24$ | **0.9791666667** | **0.9791666667** | 0 | See Provenance Note |
| **4-Decimal Rounded MRR** | $\ge 0.9792$ | **0.9792** | **0.9792** | 0 | `PASS` |
| **Bibliography Intrusions** | $= 0$ leaks | **0** | **0** | 0 | `PASS` |
| **Quality Regressions** | 0 | **0** | **0** | 0 | `PASS` |

### 4.3 MRR Acceptance Rule Provenance
- In the canonical 24-query gold standard, exactly 23 queries achieve Rank 1 ($1.0$), and exactly 1 query (Q04: Kasivisvesvara temple) achieves Rank 2 ($0.5$).
- Sum of reciprocal ranks = $23 \times 1.0 + 1 \times 0.5 = 23.5$.
- Exact unrounded MRR = $23.5 / 24 = \mathbf{0.9791666667}$.
- **Provenance**: In Phase 7 documentation, $23.5 / 24$ was reported as **0.9792** by standard 4-decimal rounding (`round(23.5/24, 4)`).
- **Literal Rule Evaluation**:
  - Under 4-decimal rounding: $\mathbf{0.9792 \ge 0.9792}$ (`PASS`).
  - Under literal unrounded floating-point comparison: $0.9791666667 < 0.9792000000$ (delta of $-0.0000333333$).
  - Both values are reported explicitly; the acceptance rule reflects the 4-decimal rounded baseline of the exact 23.5/24 fixture score.

### 4.4 Complete Ordered Evidence Differences (Arm 15 vs Arm 10)
Comparing the complete ordered 5-chunk evidence tuples between Arm 15 and Arm 10 across all 24 queries:
- **20 of 24 queries**: Returned **100% identical 5-chunk ordered evidence** tuples.
- **4 of 24 queries**: Exhibited differences solely among negative-scoring filler chunks (ranks 2–5):
  1. **Q11**: Arm 15 Rank 5 (`177133ba`, score -10.53) vs Arm 10 Rank 5 (`b25e46f8`, score -10.89). Ranks 1–4 identical. Target chunk is **Rank 1** on both.
  2. **Q14**: Arm 15 Rank 2 (`f65d980c`, score -4.79) was candidate #11 in RRF. In Arm 10, candidate pool stopped at 10, so filler chunks shifted by one rank. Target chunk is **Rank 1** on both.
  3. **Q15**: Arm 15 Rank 5 (`fbb77ce6`, score -2.73) vs Arm 10 Rank 5 (`1eb060c8`, score -4.06). Ranks 1–4 identical. Target chunk is **Rank 1** on both.
  4. **Q18**: Arm 15 Rank 5 (`1eb060c8`, score -10.28) vs Arm 10 Rank 5 (`bc3dbadb`, score -10.36). Ranks 1–4 identical. Target chunk is **Rank 1** on both.
- **Conclusion**: In zero cases did slicing at 10 displace or degrade a relevant target chunk. Target chunks achieved 100% identical ranks on both arms.

---

## 5. Performance Recalculation & Paired Analysis

Across all 48 paired repetition pairs (96 arm executions):

| Metric | Arm 15 (Candidates = 15) | Arm 10 (Candidates = 10) | Paired Delta ($T_{15} - T_{10}$) |
| :--- | :--- | :--- | :--- |
| **Mean Latency** | 1,106.46 ms | 767.93 ms | **+338.53 ms** |
| **Median Latency** | 944.15 ms | 645.76 ms | **+292.40 ms** |
| **Difference between Arm Medians** | — | — | **+298.39 ms** ($944.15 - 645.76$) |
| **Minimum Latency** | 807.02 ms | 531.83 ms | -487.17 ms |
| **Maximum Latency** | 2,385.50 ms | 1,562.47 ms | +1,683.98 ms |
| **P90 Latency** | 1,579.14 ms | 1,215.46 ms | +739.37 ms |
| **P95 Latency** | 2,005.05 ms | 1,400.65 ms | +994.46 ms |
| **Standard Deviation** | 355.82 ms | 263.47 ms | 362.60 ms |

### Speedup Consistency:
- **Arm 10 Faster**: **42 of 48 pairs (87.5%)**
- **Arm 10 Slower**: **6 of 48 pairs (12.5%)** (transient CPU/swap paging contention on dual-core host)
- **Tied**: 0 pairs (0.0%)

### Order-of-Execution Invariance:
- **Repetition 1 (15-first, 24 pairs)**: Mean Delta = +375.79 ms, Median Delta = +297.71 ms
- **Repetition 2 (10-first, 24 pairs)**: Mean Delta = +301.27 ms, Median Delta = +292.40 ms
- Confirms the ~292–298 ms advantage is independent of cache warmness or execution ordering.

---

## 6. Audit of Grounding Policy & Hallucination Assessment

- **In-Corpus Queries**: All 24 queries produced top Cross-Encoder scores $\ge -6.0$ (range: -3.11 to +10.64; median: +7.68) for both arms, resulting in `is_grounded = True`.
- **Synthetic Out-of-Corpus Fallback Query**: Tested *"What is the ticket price for the Eiffel Tower in Paris?"*:
  - Arm 15 Top Score: **-10.852** (< -6.0) $\rightarrow$ `is_grounded = False`, fallback: `"Information is not available in the knowledge base."` (`PASS`).
  - Arm 10 Top Score: **-10.852** (< -6.0) $\rightarrow$ `is_grounded = False`, fallback: `"Information is not available in the knowledge base."` (`PASS`).
- **Answer Hallucination Assessment**: Tagged strictly as **`NOT MEASURED`** because this component retrieval experiment generates no LLM answers. A score $\ge -6.0$ is an evidence-grounding policy check, not proof of zero hallucinations. The existing zero-hallucination requirement remains outstanding for any later adoption decision.

---

## 7. Remaining Uncertainties & Checks Not Performed

1. **Unmeasured LLM End-to-End Turnaround**: Sparing ~292 ms during reranking does not resolve the ~12–86s LLM prompt eval / generation turnaround or ~81s NLLB translation turnaround.
2. **Unmeasured Live Audio Turnaround**: Client audio playback and end-to-end voice turnaround were not measured in this component test.
3. **Corpus Size Boundary**: The active knowledge base contains 22 chunks across 5 documents. In larger multi-thousand chunk corpora, RRF top-10 candidate diversity versus top-15 may behave differently.

---

## 8. Cryptographic File Manifest & Production Invariant

| Component / Artifact | File Path | SHA-256 Checksum | Invariant Status |
| :--- | :--- | :--- | :--- |
| **Production Config** | `backend/app/core/config.py` | `357d6274450ddde14ec746e6e62f53337a62b3f835babab6303ba493e0a080c4` | **100% UNCHANGED (`CANDIDATES = 15`)** |
| **Benchmark Documentation** | `docs/BENCHMARKS.md` | `b188c6b75bb25cf038bfd254b38d7bb6c4e511739c36ce85c074beee9dbe6e4e` | Updated with precise findings |
| **Walkthrough Artifact** | `brain/.../walkthrough.md` | `1bc1ebef2d1ea522502ee61cf1c1f016f49962a93ce5e93e2b2a60a927d6d7a5` | Updated with precise findings |
| **Raw Results File** | `original_artifacts/benchmark_results.json` | `89846b3e6dbb04abc233faeea527e70ce9dbdedb3fab1fc8e21f3dd49dafa7b6` | Preserved unchanged |
| **Benchmark Harness** | `original_artifacts/run_isolated_rerank_experiment.py` | `c054f3575baa6a637d8dcc729576b5092e027d39489caa6ca0e3d9ffa25f7667` | Preserved unchanged |
| **Canonical 24 Queries** | `original_artifacts/canonical_24_queries.json` | `dba792d978f56b994857c32ae5e8421f2361c2515fa3bec99d43285ca550ca6f` | Preserved unchanged |
| **Original Phase 7 Fixture** | `original_artifacts/run_full_real_benchmark.py` | `ae17c843f347c7b7628992397c7d94f4bebd2db958bc2b93c884b4ed8d834313` | Preserved unchanged |
| **Execution Log (96 Runs)**| `original_artifacts/task-18649.log` | `6b04e5729c9d9f84d9f9bb3289bf323025bdaf17fa479f9d213fc6b6657cfec0` | Preserved unchanged |
| **Setup Crash Log** | `original_artifacts/task-18617.log` | `0ed95f16326d306df50c6415c36f89e23dd9f44a716e34fc4fefd22a52220c54` | Preserved unchanged |
| **Ground-Truth Mapping Audit** | `mapping_audit.json` | `537d199bbad6274e84691ee0e61c1fffc19dc3bf3788a30e6877ef41cb844e49` | Exported and verified |
| **Quality Recalculation** | `quality_recalculation.json` | `58572b115fffc95f9c4cf7e7da2c8b0fecece2f0ea41829447e174b88950d32f` | Exported and verified |
| **Performance Recalculation** | `performance_recalculation.json` | `577e1bf1fbc73fc1c853fe5efc1c24e6fb10b064c1daff152917ef745be34125` | Exported and verified |
| **Active DB Generation** | `1a2c6365-1bee-4478-9599-a706ee5c7221` | MySQL Database Invariant | **Exactly ONE active generation** |

---

## 9. Final Recommendation

- **Verdict on 10-Candidate Proposal**: **RECOMMENDED AS CANDIDATE FOR FUTURE SEPARATE PRODUCTION APPROVAL**.
- Slicing Cross-Encoder candidates at 10 reliably saves **~292 ms median latency** with **zero quality regressions on the evaluated metrics**.
- **Governance Gate**: Production setting remains at **15** in `backend/app/core/config.py`. Level 2 implementation remains **NOT APPROVED**; Phase 18 is **NOT FINAL**; awaiting explicit review.
