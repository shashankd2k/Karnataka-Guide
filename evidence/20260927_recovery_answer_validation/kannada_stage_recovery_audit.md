# Kannada Pipeline Stage Recovery and Execution Audit

## Overview

- **Test Query**: `ನಕ್ಷತ್ರಾಕಾರದ ಹೊಯ್ಸಳ ದೇವಾಲಯದ ಜಗತಿಗೆ ಯಾವ ಮೃದುವಾದ ಕಲ್ಲಿನ ವಸ್ತುವನ್ನು ಬಳಸಲಾಗಿತ್ತು?`
- **English Equivalent**: What soft stone material was used for star-shaped Hoysala temple platforms? (Q14)
- **Docker Memory Constraint**: 3.696 GiB limit

## Stage-by-Stage Recovery Status Table

| Stage | Arm 15 Status | Arm 15 Timing | Arm 10 Status | Arm 10 Timing | Primary Evidence Source |
| :--- | :---: | :---: | :---: | :---: | :--- |
| 1. NLLB Model Load | **COMPLETED** | 37401.98 ms | **COMPLETED** | Reused | `task-18991.log:L83` |
| 2. Kn->En Translation | **COMPLETED** | 146582.75 ms | **COMPLETED** | Reused | `task-18991.log:L88` |
| 3. Hybrid Retrieval | **COMPLETED** | 72613.4 ms | **COMPLETED** | 8975.63 ms | `task-18991:L98` / `task-19112:L9` |
| 4. English LLM Generation | **TIMED_OUT** | 300000.0 ms | **TIMED_OUT** | 300000.0 ms | `task-18991:L102` / `task-19112:L21` |
| 5. En->Kn Answer Translation | **NOT_RUN** | Blocked | **NOT_RUN** | Blocked | Blocked by Stage 4 Timeout |

## Out-of-Corpus Fallback Check Classification

- **Classification**: `GUARD_LANGUAGE_COMPONENT_CHECK`
- **Rationale**: No task logs exist showing out-of-corpus queries passing through translation and retrieval. The check evaluates the prompt-guard and fallback string logic in isolation.
- **Approved PRD Fallback (English)**: *"Information is not available in the knowledge base."*
- **Approved PRD Fallback (Kannada)**: *"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."*
- **Historical Test Note**: The historical harness in `run_focused_answer_validation.py` asserted on older verbose test strings ("I do not have sufficient information..."), whereas production system policies strictly enforce the approved concise PRD fallbacks.

## Root Cause Analysis and Governance Assessment

Both Arm 15 and Arm 10 completed translation and retrieval successfully, retrieving chunk 9562ad24-5749-4156-ad83-62b5d266841e as top evidence. However, both configurations timed out after 300.0s at the LLM answer generation stage under Docker memory constraints and dual-core CPU contention. Downstream answer translation was NOT RUN. Memory pressure is a documented contributing constraint, but must not be presented as a proven sole cause (system scheduling, CPU contention on 2 physical cores, and Ollama paging also contributed). Per governance instruction, missing stages were attempted once, finite deadlines were enforced, and execution stopped without repeated diagnostic attempts. Kannada answer generation remains BLOCKED/TIMED_OUT WITH DOCUMENTED LIMITATIONS.
