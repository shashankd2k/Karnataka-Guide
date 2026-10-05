import json, urllib.request, time, re, statistics

with open("scratch/production_prompts_30.json", "r", encoding="utf-8") as f:
    prompts = json.load(f)

print(f"Total extracted prompts: {len(prompts)}")
grounded = [p for p in prompts if p["is_grounded"]]
ungrounded = [p for p in prompts if not p["is_grounded"]]
print(f"Grounded: {len(grounded)}, Ungrounded: {len(ungrounded)}")

for p in prompts:
    print(f"  {p['id']}: grounded={p['is_grounded']}, chars={p['prompt_chars']}, query='{p['query'][:35]}...'")
