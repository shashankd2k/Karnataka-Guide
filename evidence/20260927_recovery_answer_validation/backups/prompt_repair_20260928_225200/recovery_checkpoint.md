# Recovery Checkpoint Log: RECOVERY-CHECKPOINT-20260928-FINAL

- **Timestamp**: 2026-09-28T22:15:00+05:30
- **Resumed Position**: Interrupted evidence recovery following `scratch/apply_report_corrections.py` and `BENCHMARKS.md` inspection.
- **Active Generation ID**: `1a2c6365-1bee-4478-9599-a706ee5c7221`
- **Production Setting**: `RETRIEVAL_RERANK_CANDIDATES = 15`
- **Phase Status**: Phase 18 NOT FINAL; Level 1 COMPLETE WITH DOCUMENTED LIMITATIONS; Level 2 INCOMPLETE.

## Stage Execution Status

| Stage | Name | Status | Key Deliverable |
| :---: | :--- | :---: | :--- |
| **Stage 1** | Interruption Resumption & Backup Preservation | **COMPLETED** | Backups in `backups/` with timestamp `20260928_220200` |
| **Stage 2** | Benchmark File Identity Reconciliation | **COMPLETED** | Authentic SHA-256 confirmed (`89846b...`), container marked `NOT CHECKED (LIVE ACCESS UNAVAILABLE)` |
| **Stage 3** | Quality Floor & Recall Attribution Corrections | **COMPLETED** | Q01/Q24 Recall@5 = 0.5, 22 queries Recall@5 = 1.0, Macro Recall@5 = 95.8333% (23/24), Q04 at Rank 2 |
| **Stage 4** | Answer & Prompt Reporting Verification | **COMPLETED** | `max_passages=2` prompt limit vs `max_passages=3` citation metadata; Q11 Arm 15 duration 247495.1 ms; Q15 factual-grounding failure; Q18 failure in both configurations; Kannada blocked/timed out |
| **Stage 5** | Evidence Package Assembly & Verification | **COMPLETED** | SHA-256 manifest generated, ZIP archive created and verified |
| **Stage 6** | Final Report Generation | **IN_PROGRESS** | Detailed closing report and ChatGPT review instructions |

## Authentic Reference Artifact Verification

- `benchmark_results.json` SHA-256: `89846b3e6dbb04abc233faeea527e70ce9dbdedb3fab1fc8e21f3dd49dafa7b6` (521,896 bytes)
- Phantom Hash `6936ee...`: Reconciled as narrative transcription error; does not exist on disk.
