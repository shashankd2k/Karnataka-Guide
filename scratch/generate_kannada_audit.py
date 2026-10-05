import json
import os

rec_dir = "evidence/20260927_recovery_answer_validation"
os.makedirs(rec_dir, exist_ok=True)

kannada_audit = {
    "metadata": {
        "evaluation_target": "End-to-End Kannada Query Processing & Retrieval Candidates Comparison",
        "kannada_test_query": "ನಕ್ಷತ್ರಾಕಾರದ ಹೊಯ್ಸಳ ದೇವಾಲಯದ ಜಗತಿಗೆ ಯಾವ ಮೃದುವಾದ ಕಲ್ಲಿನ ವಸ್ತುವನ್ನು ಬಳಸಲಾಗಿತ್ತು?",
        "english_equivalent": "What soft stone material was used for star-shaped Hoysala temple platforms? (Q14)",
        "docker_vm_memory_limit_gib": 3.696,
        "governance_rule": "Recover the actual status of each attempted Kannada stage and each configuration separately. Distinguish COMPLETED, FAILED, TIMED_OUT, and NOT_RUN. Stop on another timeout and report the blocked stage without repeated diagnostic generation.",
    },
    "stages_audit": {
        "arm_15": {
            "stage_1_nllb_load": {
                "status": "COMPLETED",
                "duration_ms": 37401.98,
                "evidence_source": "task-18991.log: line 83",
                "details": "facebook/nllb-200-distilled-600M loaded on CPU successfully.",
            },
            "stage_2_query_translation_kn_to_en": {
                "status": "COMPLETED",
                "duration_ms": 146582.75,
                "evidence_source": "task-18991.log: line 88",
                "chars_in": 77,
                "chars_out": 75,
                "translated_query": "What soft stone material was used for the temple of the star-shaped Hoisal?",
            },
            "stage_3_hybrid_retrieval_candidates_15": {
                "status": "COMPLETED",
                "duration_ms": 72613.4,
                "evidence_source": "task-18991.log: lines 98-99",
                "dense_count": 22,
                "bm25_count": 22,
                "fused_count": 15,
                "final_count": 5,
                "top_candidate": {
                    "chunk_id": "9562ad24-5749-4156-ad83-62b5d266841e",
                    "document": "Belur_Halebidu_Hoysala_Guide.pdf",
                    "page": 1,
                    "section": "ARCHITECTURAL CHARACTERISTICS",
                    "reranker_score": 4.3989,
                },
            },
            "stage_4_english_llm_generation": {
                "status": "TIMED_OUT",
                "duration_ms": 300000.0,
                "evidence_source": "task-18991.log: lines 102-108",
                "error": "ServiceUnavailableException: Ollama LLM generation timed out after 300.0 seconds (httpcore.ReadTimeout at http://ollama:11434/api/generate).",
                "contributing_factor": "Memory pressure under Docker Desktop 3.696 GiB RAM limit (concurrent resident NLLB ~2.4 GiB, Cross-Encoder, and Ollama phi3:mini).",
            },
            "stage_5_answer_translation_en_to_kn": {
                "status": "NOT_RUN",
                "duration_ms": None,
                "evidence_source": "task-18991.log",
                "reason": "Blocked by Stage 4 timeout.",
            },
        },
        "arm_10": {
            "stage_1_nllb_load": {
                "status": "COMPLETED",
                "duration_ms": 37401.98,
                "evidence_source": "reused from task-18991.log",
                "details": "Model snapshot verified and cached.",
            },
            "stage_2_query_translation_kn_to_en": {
                "status": "COMPLETED",
                "duration_ms": 146582.75,
                "evidence_source": "reused from task-18991.log",
                "chars_in": 77,
                "chars_out": 75,
                "translated_query": "What soft stone material was used for the temple of the star-shaped Hoisal?",
            },
            "stage_3_hybrid_retrieval_candidates_10": {
                "status": "COMPLETED",
                "duration_ms": 8975.63,
                "evidence_source": "task-19112.log: lines 9-10",
                "dense_count": 22,
                "bm25_count": 22,
                "fused_count": 10,
                "final_count": 5,
                "top_candidate": {
                    "chunk_id": "9562ad24-5749-4156-ad83-62b5d266841e",
                    "document": "Belur_Halebidu_Hoysala_Guide.pdf",
                    "page": 1,
                    "section": "ARCHITECTURAL CHARACTERISTICS",
                    "reranker_score": 4.3989,
                },
            },
            "stage_4_english_llm_generation": {
                "status": "TIMED_OUT",
                "duration_ms": 300000.0,
                "evidence_source": "task-19112.log: lines 21-25",
                "error": "ServiceUnavailableException: Ollama LLM generation timed out after 300.0 seconds (httpcore.ReadTimeout at http://ollama:11434/api/generate).",
                "contributing_factor": "Memory pressure under Docker Desktop 3.696 GiB RAM limit.",
            },
            "stage_5_answer_translation_en_to_kn": {
                "status": "NOT_RUN",
                "duration_ms": None,
                "evidence_source": "task-19112.log",
                "reason": "Blocked by Stage 4 timeout.",
            },
        },
    },
    "out_of_corpus_fallback_classification": {
        "classification": "GUARD_LANGUAGE_COMPONENT_CHECK",
        "evidence_basis": "No task logs exist showing out-of-corpus queries passing through translation and retrieval. The check evaluates the prompt-guard and fallback string logic in isolation.",
        "english_fallback_string": "I do not have sufficient information in the verified Karnataka tourism records to answer this question.",
        "kannada_fallback_string": "ಈ ಪ್ರಶ್ನೆಗೆ ಉತ್ತರಿಸಲು ಪರಿಶೀಲಿಸಿದ ಕರ್ನಾಟಕ ಪ್ರವಾಸೋದ್ಯಮ ದಾಖಲೆಗಳಲ್ಲಿ ಸಾಕಷ್ಟು ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ.",
    },
    "conclusion": (
        "Both Arm 15 and Arm 10 completed translation and retrieval successfully, retrieving chunk 9562ad24-5749-4156-ad83-62b5d266841e "
        "as top evidence. However, both configurations timed out after 300.0s at the LLM answer generation stage under Docker memory pressure. "
        "Per governance instruction, missing stages were attempted once, finite deadlines were enforced, and execution stopped without "
        "repeated diagnostic attempts. Kannada answer generation remains BLOCKED WITH DOCUMENTED LIMITATIONS."
    ),
}

json_path = os.path.join(rec_dir, "kannada_stage_recovery_audit.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(kannada_audit, f, indent=2, ensure_ascii=False)

md_path = os.path.join(rec_dir, "kannada_stage_recovery_audit.md")
with open(md_path, "w", encoding="utf-8") as f:
    f.write("# Kannada Pipeline Stage Recovery and Execution Audit\n\n")
    f.write("## Overview\n\n")
    f.write(f"- **Test Query**: `{kannada_audit['metadata']['kannada_test_query']}`\n")
    f.write(f"- **English Equivalent**: {kannada_audit['metadata']['english_equivalent']}\n")
    f.write(f"- **Docker Memory Constraint**: {kannada_audit['metadata']['docker_vm_memory_limit_gib']} GiB limit\n\n")
    f.write("## Stage-by-Stage Recovery Status Table\n\n")
    f.write("| Stage | Arm 15 Status | Arm 15 Timing | Arm 10 Status | Arm 10 Timing | Primary Evidence Source |\n")
    f.write("| :--- | :---: | :---: | :---: | :---: | :--- |\n")
    s15 = kannada_audit["stages_audit"]["arm_15"]
    s10 = kannada_audit["stages_audit"]["arm_10"]
    f.write(f"| 1. NLLB Model Load | **{s15['stage_1_nllb_load']['status']}** | {s15['stage_1_nllb_load']['duration_ms']} ms | **{s10['stage_1_nllb_load']['status']}** | Reused | `task-18991.log:L83` |\n")
    f.write(f"| 2. Kn->En Translation | **{s15['stage_2_query_translation_kn_to_en']['status']}** | {s15['stage_2_query_translation_kn_to_en']['duration_ms']} ms | **{s10['stage_2_query_translation_kn_to_en']['status']}** | Reused | `task-18991.log:L88` |\n")
    f.write(f"| 3. Hybrid Retrieval | **{s15['stage_3_hybrid_retrieval_candidates_15']['status']}** | {s15['stage_3_hybrid_retrieval_candidates_15']['duration_ms']} ms | **{s10['stage_3_hybrid_retrieval_candidates_10']['status']}** | {s10['stage_3_hybrid_retrieval_candidates_10']['duration_ms']} ms | `task-18991:L98` / `task-19112:L9` |\n")
    f.write(f"| 4. English LLM Generation | **{s15['stage_4_english_llm_generation']['status']}** | {s15['stage_4_english_llm_generation']['duration_ms']} ms | **{s10['stage_4_english_llm_generation']['status']}** | {s10['stage_4_english_llm_generation']['duration_ms']} ms | `task-18991:L102` / `task-19112:L21` |\n")
    f.write(f"| 5. En->Kn Answer Translation | **{s15['stage_5_answer_translation_en_to_kn']['status']}** | Blocked | **{s10['stage_5_answer_translation_en_to_kn']['status']}** | Blocked | Blocked by Stage 4 Timeout |\n\n")
    f.write("## Out-of-Corpus Fallback Check Classification\n\n")
    f.write(f"- **Classification**: `{kannada_audit['out_of_corpus_fallback_classification']['classification']}`\n")
    f.write(f"- **Rationale**: {kannada_audit['out_of_corpus_fallback_classification']['evidence_basis']}\n")
    f.write(f"- **English Fallback**: *\"{kannada_audit['out_of_corpus_fallback_classification']['english_fallback_string']}\"*\n")
    f.write(f"- **Kannada Fallback**: *\"{kannada_audit['out_of_corpus_fallback_classification']['kannada_fallback_string']}\"*\n\n")
    f.write("## Root Cause Analysis and Governance Assessment\n\n")
    f.write(f"{kannada_audit['conclusion']}\n")

print("Exported kannada_stage_recovery_audit.json and .md successfully.")
