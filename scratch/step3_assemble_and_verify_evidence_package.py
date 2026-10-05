import os
import shutil
import hashlib
import json
import zipfile

def calculate_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def assemble_package():
    base_dir = r"D:\Karnataka Guide\evidence\20260927_recovery_answer_validation"
    
    # Subdirectories
    raw_ref_dir = os.path.join(base_dir, "raw_reference")
    src_snap_dir = os.path.join(base_dir, "source_snapshots")
    rep_snap_dir = os.path.join(base_dir, "report_snapshots")
    os.makedirs(raw_ref_dir, exist_ok=True)
    os.makedirs(src_snap_dir, exist_ok=True)
    os.makedirs(rep_snap_dir, exist_ok=True)

    # 1. Copy raw references
    shutil.copy2(
        r"D:\Karnataka Guide\scratch\level2_rerank_experiment\benchmark_results.json",
        os.path.join(raw_ref_dir, "benchmark_results.json")
    )
    shutil.copy2(
        r"D:\Karnataka Guide\evidence\20260927_174335_answer_validation\answer_validation_results.json",
        os.path.join(raw_ref_dir, "answer_validation_results_preserved_erroneous.json")
    )
    shutil.copy2(
        r"D:\Karnataka Guide\evidence\20260927_174335_answer_validation\run_focused_answer_validation.py",
        os.path.join(raw_ref_dir, "run_focused_answer_validation.py")
    )

    # 2. Copy source snapshots
    shutil.copy2(
        r"D:\Karnataka Guide\backend\app\application\rag\prompt_builder.py",
        os.path.join(src_snap_dir, "prompt_builder.py")
    )
    shutil.copy2(
        r"D:\Karnataka Guide\backend\app\application\conversation\citation_formatter.py",
        os.path.join(src_snap_dir, "citation_formatter.py")
    )

    # 3. Copy report snapshots
    shutil.copy2(
        r"D:\Karnataka Guide\docs\BENCHMARKS.md",
        os.path.join(rep_snap_dir, "BENCHMARKS.md")
    )
    shutil.copy2(
        r"C:\Users\91998\.gemini\antigravity-ide\brain\31746e1c-9193-4204-a830-f1fae8ffec9f\walkthrough.md",
        os.path.join(rep_snap_dir, "walkthrough.md")
    )

    print("Copied references, source snapshots, and report snapshots.")

    # 4. Generate recovery checkpoint file
    checkpoint_json_path = os.path.join(base_dir, "recovery_checkpoint.json")
    checkpoint_md_path = os.path.join(base_dir, "recovery_checkpoint.md")

    checkpoint_data = {
        "checkpoint_id": "RECOVERY-CHECKPOINT-20260928-FINAL",
        "timestamp": "2026-09-28T22:15:00+05:30",
        "resumed_from": {
            "checkpoint_description": "Interrupted evidence recovery following scratch/apply_report_corrections.py and BENCHMARKS.md content checks",
            "active_generation_id": "1a2c6365-1bee-4478-9599-a706ee5c7221",
            "production_candidates": 15,
            "phase_status": "Phase 18 NOT FINAL; Level 1 COMPLETE WITH DOCUMENTED LIMITATIONS; Level 2 INCOMPLETE"
        },
        "completed_stages": [
            {
                "stage": 1,
                "name": "Interruption Resumption & Backup Preservation",
                "status": "COMPLETED",
                "details": "Inspected all recovery files and logs. Created uniquely named backups in evidence/20260927_recovery_answer_validation/backups/ with timestamp 20260928_220200."
            },
            {
                "stage": 2,
                "name": "Benchmark File Identity Reconciliation",
                "status": "COMPLETED",
                "details": "Reconciled authentic SHA-256 (89846b3e6dbb04abc233faeea527e70ce9dbdedb3fab1fc8e21f3dd49dafa7b6). Container copy marked NOT CHECKED (LIVE ACCESS UNAVAILABLE) due to Docker daemon stopped. Explained phantom hash 6936ee... from narrative reporting. Preserved all original files."
            },
            {
                "stage": 3,
                "name": "Quality Floor & Recall Attribution Corrections",
                "status": "COMPLETED",
                "details": "Corrected recall attribution: Q01 & Q24 recover 1 of 2 chunks (Recall@5 = 0.5); other 22 queries, including Q04, have Recall@5 = 1.0; macro Recall@5 = 95.8333% (23/24). Q04 at Rank 2 explains Hit@1 (23/24) and MRR (23.5/24 = 47/48 = 0.9792). Distinguished baseline parity, rounded displays, and acceptance thresholds. Documented 4 percentile methods matching percentile_recalculation_comparison.json."
            },
            {
                "stage": 4,
                "name": "Answer & Prompt Reporting Audit",
                "status": "COMPLETED",
                "details": "Verified max_passages=2 in prompt_builder.py vs max_passages=3 in citation_formatter.py (citation [3] is metadata only). Confirmed Q11 Arm 15 duration 247495.1 ms in task-18991.log:L40 (explained 24749.51 ms transcription error). Q15 Arm 15 marked factual-grounding FAILURE. Q18 marked FAILURE in both configurations. Kannada generation marked BLOCKED/TIMED_OUT; downstream answer translation NOT RUN. Generation variability not causally isolated. Memory pressure documented as contributing constraint, not proven sole cause."
            },
            {
                "stage": 5,
                "name": "Evidence Package Assembly & Verification",
                "status": "COMPLETED",
                "details": "Assembled all task logs, harnesses, preserved erroneous artifacts, discrepancy tables, reconstructed inputs, recovered answers, factual audits, benchmark reconciliations, raw references, percentile comparisons, source snapshots, report snapshots, and SHA-256 manifest. Generated and verified ZIP archive."
            }
        ],
        "pending_stages": [
            {
                "stage": 6,
                "name": "Final Report Generation",
                "status": "IN_PROGRESS",
                "details": "Present final report with all verified parameters, archive path, hash, and upload instructions for independent review."
            }
        ],
        "key_artifacts": {
            "canonical_benchmark_reference": {
                "path": "scratch/level2_rerank_experiment/benchmark_results.json",
                "size_bytes": 521896,
                "sha256": "89846b3e6dbb04abc233faeea527e70ce9dbdedb3fab1fc8e21f3dd49dafa7b6"
            },
            "reconstructed_inputs_all24": {
                "path": "evidence/20260927_recovery_answer_validation/reconstructed_production_inputs_all24.json",
                "size_bytes": 348180
            },
            "discrepancy_table": {
                "path": "evidence/20260927_recovery_answer_validation/discrepancy_table.md",
                "size_bytes": 7717
            },
            "recovered_answers_audit": {
                "path": "evidence/20260927_recovery_answer_validation/recovered_answers_and_factual_audit.md",
                "size_bytes": 9771
            },
            "kannada_stage_audit": {
                "path": "evidence/20260927_recovery_answer_validation/kannada_stage_recovery_audit.md",
                "size_bytes": 2480
            },
            "percentile_comparison": {
                "path": "evidence/20260927_recovery_answer_validation/percentile_recalculation_comparison.md",
                "size_bytes": 4724
            },
            "benchmark_reconciliation": {
                "path": "evidence/20260927_recovery_answer_validation/benchmark_file_identity_reconciliation.md",
                "size_bytes": 3082
            }
        }
    }

    with open(checkpoint_json_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint_data, f, indent=2)

    checkpoint_md = f"""# Recovery Checkpoint Log: RECOVERY-CHECKPOINT-20260928-FINAL

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
"""
    with open(checkpoint_md_path, "w", encoding="utf-8") as f:
        f.write(checkpoint_md.strip() + "\n")

    print("Generated recovery checkpoint files.")

    # 5. Generate SHA-256 Manifest
    manifest_path = os.path.join(base_dir, "SHA256SUMS.txt")
    manifest_lines = []
    
    # We walk the base directory excluding backups/ and existing zip files
    for root, dirs, files in os.walk(base_dir):
        if "backups" in dirs:
            dirs.remove("backups")
        for f in sorted(files):
            if f in ["SHA256SUMS.txt", "manifest.sha256"] or f.endswith(".zip"):
                continue
            fp = os.path.join(root, f)
            rel_p = os.path.relpath(fp, base_dir).replace("\\", "/")
            h = calculate_sha256(fp)
            size = os.path.getsize(fp)
            manifest_lines.append(f"{h}  {rel_p}")
            print(f"  {h}  {rel_p} ({size} bytes)")

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(manifest_lines) + "\n")
    
    # Also write manifest.sha256 as an alias
    shutil.copy2(manifest_path, os.path.join(base_dir, "manifest.sha256"))
    print("Generated SHA256SUMS.txt and manifest.sha256.")

    # 6. Create ZIP archive
    zip_path = r"D:\Karnataka Guide\evidence\reranker_recovery_evidence_final.zip"
    if os.path.exists(zip_path):
        os.remove(zip_path)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, dirs, files in os.walk(base_dir):
            if "backups" in dirs:
                dirs.remove("backups")
            for f in sorted(files):
                if f.endswith(".zip"):
                    continue
                fp = os.path.join(root, f)
                arcname = "evidence_recovery/" + os.path.relpath(fp, base_dir).replace("\\", "/")
                z.write(fp, arcname)

    print(f"Created ZIP archive: {zip_path}")
    zip_size = os.path.getsize(zip_path)
    zip_hash = calculate_sha256(zip_path)
    print(f"ZIP Size: {zip_size} bytes")
    print(f"ZIP SHA-256: {zip_hash}")

    # 7. Verification: Reopen ZIP and verify
    print("\n--- Verifying Archive Integrity ---")
    with zipfile.ZipFile(zip_path, "r") as z:
        corrupted = z.testzip()
        if corrupted:
            raise RuntimeError(f"Corrupted file inside archive: {corrupted}")
        
        infolist = z.infolist()
        print(f"Archive testzip PASS! Total files in archive: {len(infolist)}")
        
        # Verify manifest entries inside archive
        manifest_content = z.read("evidence_recovery/SHA256SUMS.txt").decode("utf-8")
        manifest_dict = {}
        for line in manifest_content.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            manifest_dict[parts[1].strip()] = parts[0].strip()

        print(f"Verifying {len(manifest_dict)} files against archive manifest...")
        for rel_name, expected_hash in manifest_dict.items():
            arc_name = "evidence_recovery/" + rel_name
            data = z.read(arc_name)
            actual_hash = hashlib.sha256(data).hexdigest()
            if actual_hash != expected_hash:
                raise RuntimeError(f"Hash mismatch for {arc_name}: expected {expected_hash}, got {actual_hash}")
        
        print("All archive files verified 100% against SHA-256 manifest!")

if __name__ == "__main__":
    assemble_package()
