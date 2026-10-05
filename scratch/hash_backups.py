import os
import hashlib

p = r"evidence/20260927_recovery_answer_validation/backups/prompt_repair_20260928_225200"
for f in sorted(os.listdir(p)):
    fp = os.path.join(p, f)
    h = hashlib.sha256(open(fp, "rb").read()).hexdigest()
    sz = os.path.getsize(fp)
    print(f"{f} ({sz} bytes): {h}")
