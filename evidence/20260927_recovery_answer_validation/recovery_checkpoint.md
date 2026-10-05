# Resumption Checkpoint: Focused Prompt/Citation & Answer-Boundary Repair

- **Checkpoint ID**: `RECOVERY-CHECKPOINT-20260928-PROMPT-REPAIR-RESUMED`
- **Timestamp**: `2026-09-28T22:58:00+05:30`
- **Active Generation ID**: `1a2c6365-1bee-4478-9599-a706ee5c7221`
- **Production Configuration**: `RETRIEVAL_RERANK_CANDIDATES = 15`, `phi3:mini`, `num_ctx = 1536`, `num_thread = 2`, `keepalive = 10m`, `max_context_chars = 2000`, `standard tokens = 128`, `streaming tokens = 192`
- **Phase Status**: Phase 18 NOT FINAL; Level 1 COMPLETE WITH DOCUMENTED LIMITATIONS; Level 2 INCOMPLETE.
- **Pending Processes**: 0 running background/python processes.
- **Live Generation Attempts**: 0 attempted of 8 total budget.

## Safety Backups Recorded
- **Location**: `evidence/20260927_recovery_answer_validation/backups/prompt_repair_20260928_225200`
- Files and Verified SHA-256 Hashes:
  - `BENCHMARKS.md`: `6135683cb9938a94596764e9fa4a870fb43ac254b7ff2ddb98fdcc44a320170d` (78,254 bytes)
  - `citation_formatter.py`: `4fe82161ebfdbf288d9ef7146ed05fa300f7db22c9de2d362418185905dbed10` (5,619 bytes)
  - `kannada_stage_recovery_audit.json`: `4cc31c6ea781e342b7f3eaccfad4bc7b026e1fa40320def45a0b2f57987fb3c3` (6,329 bytes)
  - `kannada_stage_recovery_audit.md`: `fa6bfc2235d6ef706c1b962a756a83e006cf158fa7590184c427135a4f8841d5` (2,764 bytes)
  - `ollama.py`: `adc993ca9d66edfe2e4591ff9e17892992ca8f1d7f40b644bc33bdf75fe91c3a` (8,983 bytes)
  - `prompt_builder.py`: `8bd6e20132154cc270d253dc0aff5884a1fdb7b802127edf475c2b645d8ce246` (6,675 bytes)
  - `recovered_answers_and_factual_audit.json`: `5524ea09a210b0d035eab928c349a2a1258e3ec9b1fdcc09253969cd256c2af8` (14,086 bytes)
  - `recovered_answers_and_factual_audit.md`: `01f4d5b3fc8bc2e6a9b96a9c9fc224e8dfc629cedbf4996f87d45cd5796adcc8` (9,915 bytes)
  - `recovery_checkpoint.json`: `b612530746a4b3a51e2ee0b09d97101c630741ad12a5a065a7580fb08a95f636` (4,432 bytes)
  - `recovery_checkpoint.md`: `85134c126a9bcae545f09d5dac80cb91f6d0bb8d4c235c873c37be3418262f5d` (1,885 bytes)
  - `walkthrough.md`: `a9d91e08cd650e440e0f3ac925deecb7e6ea66fb34027fc5fdf33e1394556279` (54,576 bytes)

## Completed & Unfinished Steps

| Step | Task | Status | Details |
| :---: | :--- | :---: | :--- |
| **1** | Working State Recovery & Backups | **COMPLETED** | Verified clean process table, inspected helpers, recorded SHA-256 backup manifest. |
| **2** | Filename & Prompt Provenance | **COMPLETED** | Traced `Document.filename` vs `Document.original_name` (UUID vs original human-readable PDF name). Resolved system prompt version discrepancy. |
| **3** | Focused Repair Implementation | **NEXT ACTION** | Fix `prompt_builder.py` authorized label pruning and character budget break, align citation extraction, verify `ollama.py` stop tokens. |
| **4** | Deterministic Offline Tests | **PENDING** | Validate label exclusion on budget truncation, deduplication, citation filtering, and exact fallback strings. |
| **5** | Bounded Live Generation | **PENDING** | Test Q11/Q14 controls and Q15/Q18 failure cases (max 8 serial requests) with immediate JSONL capture. |
| **6** | Documentation & Evidence Package | **PENDING** | Update factual and Kannada recovery audits, create new verified evidence ZIP. |

**Next Exact Action**: Apply minimal fix to `backend/app/application/rag/prompt_builder.py`.
