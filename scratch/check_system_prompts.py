import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open(r"D:\Karnataka Guide\backend\app\application\rag\prompt_builder.py", "r", encoding="utf-8") as f:
    text_pb = f.read()

print("=== Current host prompt_builder.py lines 1-65 ===")
for l in text_pb.splitlines()[:65]:
    print(l)

with open(r"D:\Karnataka Guide\evidence\20260927_recovery_answer_validation\reconstructed_production_inputs_all24.json", "r", encoding="utf-8") as f:
    data_reconstructed = json.load(f)

first_q = data_reconstructed["queries"]["Q01"]["arm_15"]
print("\n=== Reconstructed system_prompt in reconstructed_production_inputs_all24.json (Q01) ===")
print(first_q["system_prompt"])
