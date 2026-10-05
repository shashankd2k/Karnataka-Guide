"""
Script to apply evidence corrections to docs/BENCHMARKS.md and walkthrough.md.
"""
import sys

def correct_benchmarks(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 1. Section 1 table
    old_sec1 = "| **Retrieval Guardrails Floor** | **Hit@1=95.83%, Recall@5=100%, MRR=0.9792** | `MEASURED` | Quality Floor: Hit@1>=95.83%, Recall@5=100%, MRR>=0.9792 |"
    new_sec1 = "| **Retrieval Baseline Parity** | **Hit@1=95.83%, Hit@5=100%, Macro Recall@5=95.83%, MRR=0.9792** | `MEASURED` | Baseline Parity: Hit@1=95.83% (23/24), Hit@5=100% (24/24), Macro Recall@5=95.83% (23/24), MRR=0.9792 ($23.5/24$) |"
    if old_sec1 in text:
        text = text.replace(old_sec1, new_sec1, 1)

    # 2. Section 7
    old_sec7 = """## 7. Retrieval Quality Guardrails Floor (100% Preserved & Permanently Locked)

All optimization activities are subject to the non-negotiable permanent Quality Floor:
- **Hit@1**: $\\ge$ **95.83%** (Permanent Floor: $\\ge 95.83\\%$; 23/24 on canonical gold standard) — `LOCKED & PRESERVED`
- **Recall@5**: **100.0%** (Permanent Floor: $= 100.0\\%$; 24/24 on canonical gold standard) — `LOCKED & PRESERVED`
- **MRR**: $\\ge$ **0.9792** (Permanent Floor: $\\ge 0.9792$; (23*1.0 + 1*0.5)/24 on canonical gold standard) — `LOCKED & PRESERVED`"""

    new_sec7 = """## 7. Retrieval Quality Guardrails Floor & Baseline Parity (Preserved & Audited)

All optimization activities are evaluated against established retrieval baseline parity:
- **Hit@1 Rate**: **95.83%** (Baseline Parity: 23/24 on canonical gold standard; Q04 at Rank 2) — `LOCKED & PRESERVED`
- **Hit@5 Rate**: **100.0%** (Baseline Parity: 24/24 queries retrieve $\\ge 1$ expected chunk in top 5; historically labelled Recall@5 in single-label context) — `LOCKED & PRESERVED`
- **Strict Macro Recall@5**: **95.83%** (Baseline Parity: 23/24; Q01: 1/2 = 0.5, Q24: 1/2 = 0.5, remaining 22 queries = 1.0) — `LOCKED & PRESERVED`
- **MRR**: **0.9792** (Baseline Parity: exact $(23 \\times 1.0 + 1 \\times 0.5)/24 = 47/48 \\approx 0.979167$; rounded to 4 decimals: 0.9792) — `LOCKED & PRESERVED`"""
    if old_sec7 in text:
        text = text.replace(old_sec7, new_sec7, 1)

    # 3. Section 10 summary
    old_sec10_summary = """    - **Hit@1 Rate**: **95.83%** (23/24 queries at Rank 1; Q04 at Rank 2) (Locked Threshold: $\\ge 95.83\\%$) — `PASS`
    - **Recall@5**: **100.0%** (24/24 queries in top 5) (Locked Threshold: $= 100.0\\%$) — `PASS`
    - **Mean Reciprocal Rank (MRR)**: **0.9792** ($(23 \\times 1.0 + 1 \\times 0.5) / 24$) (Locked Threshold: $\\ge 0.9792$) — `PASS`
    - **Bibliography Intrusions**: **0** (Locked Threshold: $= 0$) — `PASS`"""

    new_sec10_summary = """    - **Hit@1 Rate**: **95.83%** (23/24 queries at Rank 1; Q04 at Rank 2) — `PASS (Baseline Parity)`
    - **Hit@5 Rate**: **100.0%** (24/24 queries with $\\ge 1$ relevant chunk in top 5) — `PASS (Baseline Parity)`
    - **Strict Macro Recall@5**: **95.83%** (23/24; Q01: 1/2 = 0.5, Q24: 1/2 = 0.5, remaining 22 queries = 1.0) — `PASS (Baseline Parity)`
    - **Mean Reciprocal Rank (MRR)**: **0.9792** ($(23 \\times 1.0 + 1 \\times 0.5) / 24 = 47/48 \\approx 0.979167$; 4-decimal rounded: 0.9792) — `PASS (Baseline Parity)`
    - **Bibliography Intrusions**: **0** (0 leaks) — `PASS`"""
    if old_sec10_summary in text:
        text = text.replace(old_sec10_summary, new_sec10_summary, 1)

    # 4. Section 10.3 Quality Table and Recall Definition
    old_sec10_3 = """| **Hit@1 Rate** | $\\ge 95.83\\%$ | **95.83%** (23/24) | **95.83%** (23/24) | `PASS` | 0 regressions (identical ranks) |
| **Hit@5 Rate** | $= 100.0\\%$ | **100.0%** (24/24) | **100.0%** (24/24) | `PASS` | 0 regressions (identical ranks) |
| **Strict Macro Recall@5** | $\\ge 95.83\\%$ | **95.83%** (23/24) | **95.83%** (23/24) | `PASS` | 0 regressions (identical ranks) |
| **Mean Reciprocal Rank (MRR)** | $\\ge 0.9792$ (rounded) | **0.9792** ($23.5/24$) | **0.9792** ($23.5/24$) | `PASS (Baseline Parity)` | 0 regressions (identical ranks) |
| **Bibliography Intrusions** | $= 0$ leaks | **0** | **0** | `PASS` | 0 regressions |

- **Quality Regression Count**: **ZERO (0)** across all 24 queries and all 96 arm executions.
- **Hit@5 vs Strict Macro Recall@5 Mathematical Definition**:
  - `Hit@5`: 24 of 24 queries (100.0%) successfully retrieved at least one expected ground-truth chunk in the top 5 positions.
  - `Strict Macro Recall@5`: The average, across queries, of expected relevant chunks recovered within the top five divided by the total expected relevant chunks: $\\frac{1}{Q} \\sum_{q=1}^Q \\frac{|\\text{Retrieved}_q \\cap \\text{Expected}_q|}{|\\text{Expected}_q|}$. Across the 24 queries, 23 queries achieved 1.0 (all expected chunks recovered in top 5) and 1 query (Q04) recovered 1 of 2 expected chunks in top 5, yielding an overall strict macro Recall@5 of 95.83% (23/24). It is **not** defined as "all expected chunks at Rank 1".
  - `Hit@1`: 23 of 24 queries (95.83%) had an expected relevant chunk at Rank 1.
- **Exact MRR, Rounded Display, and Compliance Semantics**:
  - Sum of reciprocal ranks across the 24 queries: $23 \\times 1.0 + 1 \\times 0.5 = 23.5$.
  - Exact unrounded MRR: $23.5 / 24 = 47 / 48 = 0.9791666667...$ ($0.9791\\bar{6}$).
  - Standard 4-decimal rounded display: **0.9792**.
  - **Baseline Parity vs Literal Threshold**: Arm 10 achieves exact parity with Arm 15 and the locked Phase 7 baseline ($23.5 / 24$). Under a literal, non-rounded interpretation ($\\ge 0.9792000000$), the unrounded value $0.9791666667$ falls short by $0.0000333333$; however, the threshold itself was originally derived by rounding $23.5 / 24$.
- **Q04 Subject Clarification**:
  - Q04 concerns **Badami Cave 3's carving date (578 CE / Saka 500) and commissioning king (King Mangalesha)** from `Badami_Caves_Guide.pdf` p.2, where expected chunk `79ba4a10-1a85-46c6-93d8-c422d274439a` was ranked at Rank 2 (behind chunk `b25e46f8-d7e1-4e7a-aa89-8fc227d8008d` at Rank 1) in both arms.
  - Note: Kasivisvesvara was only an ad-hoc test query in the 5-query Pattadakal script `backend/scratch/benchmark_retrieval.py`, not in the canonical 24-query gold-standard benchmark."""

    new_sec10_3 = """| **Hit@1 Rate** | $95.83\\%$ (23/24) | **95.83%** (23/24) | **95.83%** (23/24) | `PASS (Baseline Parity)` | 0 regressions (identical ranks) |
| **Hit@5 Rate** | $100.0\\%$ (24/24) | **100.0%** (24/24) | **100.0%** (24/24) | `PASS (Baseline Parity)` | 0 regressions (identical ranks) |
| **Strict Macro Recall@5** | $95.83\\%$ (23/24) | **95.83%** (23/24) | **95.83%** (23/24) | `PASS (Baseline Parity)` | 0 regressions (identical ranks) |
| **Mean Reciprocal Rank (MRR)** | $0.9792$ (23.5/24) | **0.9792** ($23.5/24$) | **0.9792** ($23.5/24$) | `PASS (Baseline Parity)` | 0 regressions (identical ranks) |
| **Bibliography Intrusions** | $= 0$ leaks | **0** | **0** | `PASS` | 0 regressions |

- **Quality Regression Count**: **ZERO (0)** across all 24 queries and all 96 arm executions.
- **Per-Query Recall Calculation & Correct Attribution**:
  - Generated programmatically from ground-truth chunk mapping against active generation `1a2c6365-1bee-4478-9599-a706ee5c7221`:
    - **Q01**: 1 of 2 expected chunks recovered $\\rightarrow$ **Recall@5 = 0.5** (expected: `d47453e8...` and `b3cac416...`; recovered `d47453e8...` at Rank 1).
    - **Q24**: 1 of 2 expected chunks recovered $\\rightarrow$ **Recall@5 = 0.5** (expected: `177133ba...` and `b40b9e04...`; recovered `b40b9e04...` at Rank 1).
    - **Other 22 queries, including Q04**: All expected chunks recovered in top 5 $\rightarrow$ **Recall@5 = 1.0**.
    - **Macro Recall@5**: $\\frac{22 \\times 1.0 + 0.5 + 0.5}{24} = \\frac{23}{24} = \\mathbf{95.8333\\%}$ (exact $23/24$).
  - **Q04 Analysis**: Q04 has exactly **1** expected chunk (`79ba4a10-1a85-46c6-93d8-c422d274439a`, Badami Cave 3 carving date / King Mangalesha), which was recovered at **Rank 2** (behind chunk `b25e46f8-d7e1-4e7a-aa89-8fc227d8008d` at Rank 1) in both arms. Thus, Q04 achieved Recall@5 = 1.0. Q04’s relevant chunk being at Rank 2 explains the Hit@1 ($23/24 = 95.83\\%$) and MRR ($23.5/24 = 0.9792$) reduction, NOT a recall shortfall. Previous claims that Q04 has two expected chunks or caused the recall shortfall are incorrect and retracted.
  - `Hit@5`: 24 of 24 queries (100.0%) successfully retrieved at least one expected ground-truth chunk in the top 5 positions.
  - `Hit@1`: 23 of 24 queries (95.83%) had an expected relevant chunk at Rank 1.
- **Exact MRR, Rounded Display, and Compliance Semantics**:
  - Sum of reciprocal ranks across the 24 queries: $23 \\times 1.0 + 1 \\times 0.5 = 23.5$.
  - Exact unrounded MRR: $23.5 / 24 = 47 / 48 = 0.9791666667...$ ($0.9791\\bar{6}$).
  - Standard 4-decimal rounded display: **0.9792**.
  - **Baseline Parity vs Acceptance Thresholds**: Arm 10 achieves exact parity with Arm 15 ($23.5 / 24$). Under a literal, non-rounded interpretation ($\\ge 0.9792000000$), the unrounded value $0.9791666667$ falls short by $0.0000333333$; however, the 0.9792 threshold was originally derived as the standard 4-decimal rounded value of $23.5 / 24$."""
    if old_sec10_3 in text:
        text = text.replace(old_sec10_3, new_sec10_3, 1)

    # 5. Section 10.6 input reconstruction and narrative contradictions
    old_sec10_6_2 = """#### 2. Programmatic Input Reconstruction Across All 24 Queries
- All 24 benchmark queries were reconstructed programmatically using production `build_grounded_prompt` and `extract_authoritative_citations` (saved in `evidence/20260927_recovery_answer_validation/reconstructed_production_inputs_all24.json`):
  - **20 Identical Queries** (Q01–Q10, Q12, Q13, Q16, Q17, Q19–Q24): Top-5 chunks, system prompts, user prompts, authorized labels (`[1]`, `[2]`), and authoritative citations are **100% bit-for-bit identical**.
  - **Q11, Q15, Q18**: Differ only at Rank 5 (`177133ba` vs `b25e46f8` in Q11; `fbb77ce6` vs `1eb060c8` in Q15; `1eb060c8` vs `bc3dbadb` in Q18). Because the top 4 candidates completely saturate the 2,000-character context budget (`OLLAMA_MAX_CONTEXT_CHARS = 2000`), Rank 5 is never included in the prompt. Consequently, system prompts, user prompts, authorized labels, and authoritative citations are **100% bit-for-bit identical** between Arm 15 and Arm 10 for Q11, Q15, and Q18.
  - **Q14**: The only query where prompt and citations differ. Arm 15 Rank 2 chunk `f65d980c` was candidate #11 in RRF and omitted in Arm 10, promoting chunk `32908665` to Rank 2. User prompts differ; citation labels are identical (`[1]`, `[2]`); citations differ."""

    new_sec10_6_2 = """#### 2. Programmatic Input Reconstruction Across All 24 Queries
- **Distinction Between Originally Captured and Reconstructed Inputs**:
  - The original retrieval candidate benchmark (`run_isolated_rerank_experiment.py`) recorded candidate UUIDs, Cross-Encoder scores, and isolated reranking durations in `benchmark_results.json`. Full prompt strings were **not originally captured** or persisted during that benchmark run and are marked unavailable.
  - All 24 benchmark inputs were subsequently reconstructed programmatically using the production `build_grounded_prompt` implementation (`app/application/rag/prompt_builder.py`) and verified MySQL chunk text from generation `1a2c6365-1bee-4478-9599-a706ee5c7221` (persisted in `evidence/20260927_recovery_answer_validation/reconstructed_production_inputs_all24.json`).
- **Prompt Evidence Passage Limit vs Citation Metadata Count**:
  - In `build_grounded_prompt`, the helper `compress_and_format_evidence` strictly defaults to `max_passages: int = 2`. Thus, **at most 2 passages (`[1]` and `[2]`) ever enter the model prompt evidence block**.
  - In contrast, `extract_authoritative_citations` in `app/application/conversation/citation_formatter.py` extracts up to 3 candidate metadata records (`max_passages = 3`) into the API response dictionary (`[1]`, `[2]`, `[3]`).
  - **Clarification**: Citation `[3]` is strictly API metadata and was **never included in the LLM prompt context**.
- **Per-Query Prompt Comparison**:
  - **20 Identical Retrieval Queries** (Q01–Q10, Q12, Q13, Q16, Q17, Q19–Q24): Top-5 chunks, system prompts, user prompts, authorized labels (`[1]`, `[2]`), and authoritative citations are **100% bit-for-bit identical**.
  - **Q11, Q15, Q18**: In all three queries, Rank 1 and Rank 2 candidates are identical between Arm 15 and Arm 10. Because only the top 2 candidates enter the prompt context (`max_passages = 2`), candidates at Rank 3, 4, or 5 never entered the model prompt. Consequently, system prompts, user prompts, and authorized labels (`[1]`, `[2]`) are **100% bit-for-bit identical** between Arm 15 and Arm 10.
  - **Q14**: The only query where prompt text differs between arms. In Arm 15, Rank 2 is chunk `f65d980c-f74a-4c48-9ca3-b2d54545ebcc`; in Arm 10, chunk `f65d980c` was candidate #11 in RRF and therefore excluded, promoting chunk `32908665-c04a-4b70-b3e9-15bc7643cdde` to Rank 2. User prompts and returned citation lists differ; authorized labels remain `[1]`, `[2]`."""
    if old_sec10_6_2 in text:
        text = text.replace(old_sec10_6_2, new_sec10_6_2, 1)

    # 6. Section 10.6.3 Paired Generation Audit
    old_sec10_6_3 = """#### 3. Bounded Paired LLM Generation Results (8 English Calls, Serial)
Recovered from raw execution log `task-18991.log` (lines 38–78):

- **Q11 ('Eight tiers of relief friezes with charging war elephants at Halebidu')**:
  - Arm 15 (24,749.51 ms): *"The Halebidu Hoysaleswara Temple features eight continuous horizontal tiers of relief friezes, with the lowest layer depicting 1,248 charging war elephants [1]."*
  - Arm 10 (13,222.28 ms): *"The Halebidu Hoysaleswara Temple features eight continuous horizontal tiers of relief friezes, with the lowest layer depicting 1,248 charging war elephants [1]."*
  - **Factual Assessment**: **PASS**. Both answers cite `[1]`, are factually supported by chunk `23677e76-516d-4cce-972f-b74ac0ff1606` (`Belur_Halebidu_Hoysala_Guide.pdf` p.3), and are bit-for-bit identical.

- **Q14 ('What soft stone material was used for star-shaped Hoysala temple platforms?')**:
  - Arm 15 (25,399.36 ms): *"The Hoysala temples were constructed using soft chloritic schist, also known as soapstone, which hardens when exposed to the atmosphere. [1]"*
  - Arm 10 (17,621.79 ms): *"The Hoysala temple platforms are made from soft chloritic schist, also known as soapstone. [1]"*
  - **Factual Assessment**: **PASS (WITH UNEXERCISED CITATIONS)**. Both answers correctly identify chloritic schist (soapstone) from chunk `9562ad24-5749-4156-ad83-62b5d266841e` (`Belur_Halebidu_Hoysala_Guide.pdf` p.1) using citation `[1]`. Note that citations `[2]` and `[3]` were present in prompt context but were not cited in text by either arm.

- **Q15 ('Jain Cave 4 at Badami Mahavira on Simhasana lion throne and Bahubali')**:
  - Arm 15 (65,472.99 ms): *"Cave 4 at Badami, dedicated to Jainism, features a serene sculpture of Lord Mahavira seated on a lion throne, known as Simhasana, and depicts Parshvanatha and Bahubali in meditation. The sanctum is from the late 6th to early 7th century CE, and the open mandapa extends into Agastya Lake, creating a unique heritage vista. [1]"*
  - Arm 10 (34,087.50 ms): *"Cave 4 at Badami, known for its Jain sculptures, features a serene sculpture of Lord Mahavira seated on a lion throne, symbolizing Simhasana. The verandah walls depict Parshvanatha with a multi-hooded cobra and Bahubali in meditation, known as kayotsarga. These carvings date back to the late 6th to early 7th century CE. [1]"*
  - **Factual Assessment**:
    - **Arm 15**: Sentence 1 is supported by chunk `155e4935-d729-4681-9fb4-802bebf51a0b` (`Badami_Caves_Guide.pdf` p.3). Sentence 2 (*"open mandapa extends into Agastya Lake"*) is an **unsupported hallucination** conflated with the Bhutanatha temple group, falsely tagged with `[1]`. A valid citation label does not make an unsupported claim correct.
    - **Arm 10**: Fully supported by chunk `155e4935` (`Badami_Caves_Guide.pdf` p.3).
    - **Causal Distinction**: Because prompts, candidate context, and generation parameters were **100% bit-for-bit identical** between Arm 15 and Arm 10, the difference in generated text was caused exclusively by stochastic sampling (`temperature = 0.1` without fixed random seed), **NOT** candidate-count reduction. Candidate reduction had zero effect on the input prompt for Q15 and cannot be credited with removing the hallucination.

- **Q18 ('Lad Khan temple timber-imitation joinery stone roof slabs floral lattice')**:
  - Arm 15 (62,575.76 ms): Paragraph 1 is supported by chunk `35e88269-3850-4e45-b4dd-e19a41dc7d5a` (`Aihole_Heritage_Guide.pdf` p.2) [1]. Paragraph 2 is an **unrelated off-topic continuation** about Ravana Phadi Cave (from context chunk [3]), uncited, and abruptly truncated mid-word (*"Saptamat"*) due to the 128-token limit (`num_predict = 128`).
  - Arm 10 (60,587.26 ms): Paragraph 1 is supported by chunk `35e88269` [1]. Paragraph 2 generates a **synthetic continuation** (*"Tourist Question: What are the unique architectural features of Hoysala temples? ..."*), uncited, and abruptly truncated mid-sentence (*"intricate ornamental details. They"*) due to the 128-token limit.
  - **Factual Assessment**: **FAIL (OFF-TOPIC CONTINUATION & TOKEN-BUDGET TRUNCATION)** for both arms. Neither arm passed cleanly. Because input prompts were 100% identical, the differing continuations were due to stochastic sampling, not candidate-count reduction. Token-limit truncation must not be described as a quality pass."""

    new_sec10_6_3 = """#### 3. Bounded Paired LLM Generation Results (8 English Calls, Serial)
Recovered from raw execution log `task-18991.log` (lines 38–78):

- **Q11 ('Eight tiers of relief friezes with charging war elephants at Halebidu')**:
  - **Arm 15**: **247,495.10 ms** (~247.5 s) — traced directly to exact raw log record `task-18991.log:L40` (`Arm 15 completed in 247495.1 ms`). The previous narrative report listing 24,749.51 ms was a 10x decimal transcription error in secondary documentation.
  - **Arm 10**: **13,222.28 ms** (~13.2 s) — traced directly to exact raw log record `task-18991.log:L43`.
  - **Generated Output**: *"The Halebidu Hoysaleswara Temple features eight continuous horizontal tiers of relief friezes, with the lowest layer depicting 1,248 charging war elephants [1]."* (Identical in both arms).
  - **Factual Assessment**: **PASS**. Both answers cite `[1]`, are factually supported by chunk `23677e76-516d-4cce-972f-b74ac0ff1606` (`Belur_Halebidu_Hoysala_Guide.pdf` p.3).

- **Q14 ('What soft stone material was used for star-shaped Hoysala temple platforms?')**:
  - **Arm 15**: **25,399.36 ms** (`task-18991.log:L48`): *"The Hoysala temples were constructed using soft chloritic schist, also known as soapstone, which hardens when exposed to the atmosphere. [1]"*
  - **Arm 10**: **17,621.79 ms** (`task-18991.log:L51`): *"The Hoysala temple platforms are made from soft chloritic schist, also known as soapstone. [1]"*
  - **Factual Assessment**: **PASS (WITH UNEXERCISED CITATIONS)**. Both answers correctly identify chloritic schist (soapstone) from chunk `9562ad24-5749-4156-ad83-62b5d266841e` (`Belur_Halebidu_Hoysala_Guide.pdf` p.1) using citation `[1]`. Note: Chunk `[2]` was present in prompt context but was not cited. Citation `[3]` was returned in API response metadata only and was not in prompt context.

- **Q15 ('Jain Cave 4 at Badami Mahavira on Simhasana lion throne and Bahubali')**:
  - **Arm 15**: **65,472.99 ms** (`task-18991.log:L56`): *"Cave 4 at Badami, dedicated to Jainism, features a serene sculpture of Lord Mahavira seated on a lion throne, known as Simhasana, and depicts Parshvanatha and Bahubali in meditation. The sanctum is from the late 6th to early 7th century CE, and the open mandapa extends into Agastya Lake, creating a unique heritage vista. [1]"*
  - **Arm 10**: **34,087.50 ms** (`task-18991.log:L59`): *"Cave 4 at Badami, known for its Jain sculptures, features a serene sculpture of Lord Mahavira seated on a lion throne, symbolizing Simhasana. The verandah walls depict Parshvanatha with a multi-hooded cobra and Bahubali in meditation, known as kayotsarga. These carvings date back to the late 6th to early 7th century CE. [1]"*
  - **Factual Assessment**:
    - **Arm 15**: **FAIL (FACTUAL-GROUNDING FAILURE)**. Sentence 1 is supported by chunk `155e4935-d729-4681-9fb4-802bebf51a0b` (`Badami_Caves_Guide.pdf` p.3). Sentence 2 (*"open mandapa extends into Agastya Lake"*) is an **unsupported hallucination** conflating Cave 4 with the lakeside Bhutanatha temple group, falsely tagged with `[1]`. Attaching a valid citation label to an unsupported claim is a factual-grounding failure.
    - **Arm 10**: Supported by chunk `155e4935` (`Badami_Caves_Guide.pdf` p.3).
    - **Causal Assessment**: For Q15, prompts were bit-for-bit identical across arms (only top 2 passages enter prompt). The observed differences do not establish a benefit from candidate reduction; the precise source of generation variability was not isolated.

- **Q18 ('Lad Khan temple timber-imitation joinery stone roof slabs floral lattice')**:
  - **Arm 15**: **62,575.76 ms** (`task-18991.log:L64`): Paragraph 1 is supported by chunk `35e88269-3850-4e45-b4dd-e19a41dc7d5a` (`Aihole_Heritage_Guide.pdf` p.2) [1]. Paragraph 2 is an **unasked off-topic continuation** about Ravana Phadi Cave (present in chunk [1] text, which covers Lad Khan, Ravana Phadi, and Meguti Inscription), uncited, and abruptly truncated mid-token (*"Saptamat"*) due to the 128-token limit (`num_predict = 128`).
  - **Arm 10**: **60,587.26 ms** (`task-18991.log:L70`): Paragraph 1 is supported by chunk `35e88269` [1]. Paragraph 2 generates a **synthetic continuation** (*"Tourist Question: What are the unique architectural features of Hoysala temples? ..."*) from chunk [2] text in context, uncited, and abruptly truncated mid-sentence (*"intricate ornamental details. They"*) due to the 128-token limit.
  - **Factual Assessment**: **FAIL IN BOTH CONFIGURATIONS**. Neither configuration passed cleanly. Both suffered from unasked topic drift and abrupt token-budget truncation. The observed differences do not establish a benefit from candidate reduction; the precise source of generation variability was not isolated."""
    if old_sec10_6_3 in text:
        text = text.replace(old_sec10_6_3, new_sec10_6_3, 1)

    # 7. Summary in Section 10.6.6
    old_sec10_6_6 = """#### 6. Summary of Verification Findings
- **Quality Metrics Retained**: Hit@1 = 95.83%, Hit@5 = 100.0%, Strict Macro Recall@5 = 95.83%, MRR = 0.9792 (exact $47/48$), Bibliography Intrusions = 0.
- **Latency Savings**: Arm 10 achieves ~292 ms median isolated reranking latency savings (mean: 338.53 ms; faster in 87.5% of pairs).
- **Answer Quality Findings**: Candidate reduction from 15 to 10 does **not** alter prompts for 23 of 24 queries (20 identical retrieval; 3 saturate context budget before Rank 5). Differing answer text in Q15 and Q18 was driven by stochastic sampling at temperature 0.1, not candidate-count reduction. Claims of universal factual accuracy or candidate-driven quality improvements are withdrawn.
- **Recommendation**: Candidate reduction to 10 remains an isolated, viable candidate for a separately approved change, but does not resolve overall voice latency bottlenecks. Production default remains locked at 15."""

    new_sec10_6_6 = """#### 6. Summary of Verification Findings & Audit Closeout
- **Quality Metrics Retained**: Hit@1 = 95.83% (23/24), Hit@5 = 100.0% (24/24), Strict Macro Recall@5 = 95.8333% (23/24; Q01: 0.5, Q24: 0.5, remaining 22 queries: 1.0), MRR = 0.9792 (exact $23.5/24 = 47/48 \\approx 0.979167$), Bibliography Intrusions = 0.
- **Latency Savings**: Arm 10 achieves ~292 ms median isolated reranking latency savings (mean: 338.53 ms; faster in 87.5% of pairs).
- **Answer Quality Audit Findings**:
  - Prompt construction strictly uses `max_passages = 2`. Candidate reduction from 15 to 10 altered input prompts for exactly 1 of 24 queries (Q14).
  - Q15 Arm 15 is recorded as a **factual-grounding failure** (hallucinated open mandapa into Agastya Lake with false citation token).
  - Q18 is recorded as a **failure in both configurations** (unprompted continuations and 128-token truncation).
  - The observed differences between Arm 15 and Arm 10 outputs do not establish a benefit from candidate reduction; the precise source of generation variability was not isolated.
- **Kannada Coverage Status**: **BLOCKED** due to 300.0s Ollama timeouts under Docker memory pressure.
- **Audit Conclusion**: **Completing an audit does not mean the application passed its checks.** Real-time targets remain unmet; answer-quality failures exist; Kannada coverage is blocked.
- **Production Status**: Production configuration remains locked at `RETRIEVAL_RERANK_CANDIDATES = 15`. Active generation `1a2c6365-1bee-4478-9599-a706ee5c7221` remains strictly preserved. Phase 18 remains **NOT FINAL**."""
    if old_sec10_6_6 in text:
        text = text.replace(old_sec10_6_6, new_sec10_6_6, 1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Successfully updated {file_path}")

if __name__ == "__main__":
    correct_benchmarks(r"D:\Karnataka Guide\docs\BENCHMARKS.md")
