import os
import difflib

backup_dir = r"evidence/20260927_recovery_answer_validation/backups/prompt_repair_20260928_225200"

files_to_check = [
    (r"backend/app/application/rag/prompt_builder.py", os.path.join(backup_dir, "prompt_builder.py")),
    (r"backend/app/application/conversation/citation_formatter.py", os.path.join(backup_dir, "citation_formatter.py")),
    (r"backend/app/application/conversation/service.py", None),  # Check if service.py was in backup or repo
    (r"backend/app/infrastructure/llm/ollama.py", os.path.join(backup_dir, "ollama.py")),
    (r"evidence/20260927_recovery_answer_validation/kannada_stage_recovery_audit.md", os.path.join(backup_dir, "kannada_stage_recovery_audit.md")),
    (r"evidence/20260927_recovery_answer_validation/kannada_stage_recovery_audit.json", os.path.join(backup_dir, "kannada_stage_recovery_audit.json")),
    (r"evidence/20260927_recovery_answer_validation/recovered_answers_and_factual_audit.md", os.path.join(backup_dir, "recovered_answers_and_factual_audit.md")),
    (r"evidence/20260927_recovery_answer_validation/recovered_answers_and_factual_audit.json", os.path.join(backup_dir, "recovered_answers_and_factual_audit.json")),
]

for curr_path, bkp_path in files_to_check:
    print("=" * 80)
    print(f"Comparing: {curr_path}")
    if bkp_path and os.path.exists(bkp_path):
        curr_lines = open(curr_path, "r", encoding="utf-8").readlines()
        bkp_lines = open(bkp_path, "r", encoding="utf-8").readlines()
        diff = list(difflib.unified_diff(bkp_lines, curr_lines, fromfile="backup", tofile="current", lineterm=""))
        if diff:
            print(f"Diff found ({len(diff)} diff lines):")
            for line in diff[:30]:
                print(" ", line)
            if len(diff) > 30:
                print(f"  ... ({len(diff) - 30} more diff lines)")
        else:
            print("IDENTICAL to backup.")
    else:
        print(f"No direct backup file at {bkp_path} (git diff will be checked).")
