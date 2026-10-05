# Live Generation Validation Audit: Prompt/Citation Repair

- **Audit Date**: 2026-09-28T23:13:30+05:30
- **Engine**: Local Host Ollama `phi3:mini` via persistent HTTP client
- **Runtime Environment**: Host Windows, dual-core CPU (`num_thread=2`), `num_ctx=1536`, `keepalive=10m`, `max_context_chars=2000`, `num_predict=128`, `temperature=0.1`, `top_p=0.9`
- **Stop Sequences Enforced**: `["\n\n", "###", "\nTourist Question:", "\nTourist:", "\nUser:", "\nAssistant:", "\nQuestion:"]`
- **Output Log**: `evidence/20260927_recovery_answer_validation/live_generation_validation_results.jsonl`

## Execution Summary & Governance Enforcement

- **Total Budget**: 8 serial live requests maximum.
- **Circuit Breaker Policy**: Abort all further live requests upon the first timeout/error.
- **Executed Attempts**: 4 serial requests attempted (3 successful, 1 timeout).
- **Aborted Requests**: 4 requests aborted due to circuit breaker trip on Request 4.

## Detailed Results per Request

### Request 1: Q11 (Arm 15 Control)
- **Query ID**: `Q11` (Arm 15)
- **Query Text**: *"Eight tiers of relief friezes with charging war elephants at Halebidu"*
- **Accepted Evidence Passages**: 2 passages (`Belur_Halebidu_Hoysala_Guide.pdf`, Page 3)
- **Authorized Labels**: `['[1]', '[2]']`
- **Duration**: 86,521.71 ms (Prompt eval: 862 tokens in 48,371.19 ms; Generation: 90 tokens in 36,069.36 ms)
- **Done Reason**: `stop`
- **Raw Answer**:
  > The Halebidu Hoysaleswara Temple's exterior base features eight continuous horizontal tiers of relief friezes, with the lowest layer depicting 1,248 charging war elephants. This design is part of the temple's narrative reliefs, which also include lions, floral scrolls, cavalry horses, makaras, and hamsas. [1]
- **Sanitized Answer**: Identical (no unauthorized citation brackets, no continuation dialogue).
- **Citations Emitted**:
  - `[1]`: `Belur_Halebidu_Hoysala_Guide.pdf`, Page 3, Section: `WALL FRIEZES AND NARRATIVE RELIEFS`
- **Factual Assessment**: **PASS**. Factually grounded, single-paragraph, zero continuation dialogue, authentic human-readable source filename matching database metadata.

---

### Request 2: Q14 (Arm 15 Control)
- **Query ID**: `Q14` (Arm 15)
- **Query Text**: *"What soft stone material was used for star-shaped Hoysala temple platforms?"*
- **Accepted Evidence Passages**: 2 passages (`Belur_Halebidu_Hoysala_Guide.pdf`, Page 1 & Page 3)
- **Authorized Labels**: `['[1]', '[2]']`
- **Duration**: 45,485.66 ms (Prompt eval: 779 tokens in 20,960.05 ms; Generation: 67 tokens in 24,224.82 ms)
- **Done Reason**: `stop`
- **Raw Answer**:
  > The Hoysala temples, including the Hoysaleswara Temple, are constructed from soft chloritic schist, also known as soapstone, which hardens upon atmospheric exposure. This material allows for the creation of jewel-like ornamental details on the temple platforms. [1]
- **Sanitized Answer**: Identical.
- **Citations Emitted**:
  - `[1]`: `Belur_Halebidu_Hoysala_Guide.pdf`, Page 1, Section: `ARCHITECTURAL CHARACTERISTICS`
- **Factual Assessment**: **PASS**. Factually accurate, identifies chloritic schist (soapstone) from chunk `[1]`, citation metadata strictly matches the supplied evidence.

---

### Request 3: Q14 (Arm 10 Comparison)
- **Query ID**: `Q14` (Arm 10)
- **Query Text**: *"What soft stone material was used for star-shaped Hoysala temple platforms?"*
- **Accepted Evidence Passages**: 2 passages (`Belur_Halebidu_Hoysala_Guide.pdf`, Page 1)
- **Authorized Labels**: `['[1]', '[2]']`
- **Duration**: 34,919.38 ms (Prompt eval: 841 tokens in 13,822.94 ms; Generation: 57 tokens in 20,952.69 ms)
- **Done Reason**: `stop`
- **Raw Answer**:
  > The Hoysala temples were constructed using soft chloritic schist, also known as soapstone, which hardens upon atmospheric exposure. This material allowed for the creation of jewel-like ornamental details on the temple platforms. [1]
- **Sanitized Answer**: Identical.
- **Citations Emitted**:
  - `[1]`: `Belur_Halebidu_Hoysala_Guide.pdf`, Page 1, Section: `ARCHITECTURAL CHARACTERISTICS`
- **Factual Assessment**: **PASS**. Factually accurate, concise, citation metadata strictly matches supplied evidence.

---

### Request 4: Q15 (Arm 15 Failure Case)
- **Query ID**: `Q15` (Arm 15)
- **Query Text**: *"Jain Cave 4 at Badami Mahavira on Simhasana lion throne and Bahubali"*
- **Accepted Evidence Passages**: 2 passages (`Badami_Caves_Guide.pdf`, Page 3 & Page 2)
- **Authorized Labels**: `['[1]', '[2]']`
- **Duration**: 90,042.72 ms
- **Done Reason**: N/A (Timeout)
- **Outcome**: **FAILED (TIMEOUT)**: Request exceeded the 90.0s client timeout during evaluation on host dual-core CPU under load.
- **Circuit Breaker Action**: All further live generation requests immediately aborted per governance rules.

---

## Findings & Provenance Conclusions

1. **Filename Provenance Verified**:
   - Live generation requests confirmed that citation formatting emits authentic original document names (`Belur_Halebidu_Hoysala_Guide.pdf`, etc.) matching database retrieval metadata, rather than storage UUID filenames (`cc5d7b4e-...pdf`).
2. **Defensive Boundary Trimming Verified**:
   - Under the repaired `SYSTEM_POLICY_ENGLISH` and stop tokens, the model stopped cleanly on all 3 successful requests (`done_reason = "stop"`) without generating follow-up simulated questions or dialogue.
3. **Citation Authorization Alignment**:
   - Authorized labels strictly matched the accepted passages (`accepted_candidates_count = 2`, `authorized_labels = ['[1]', '[2]']`), eliminating the defect where unsupplied candidates could be authorized.
4. **Latency & Resource Constraints**:
   - Host Ollama on dual-core CPU exhibits significant latency variability (34.9s to 86.5s, with Q15 exceeding 90.0s), demonstrating that CPU contention and model prompt evaluation overhead are significant operational constraints.
