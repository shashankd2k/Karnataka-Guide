import json

res = {}
for q in ['P07', 'P08', 'P10', 'P21', 'P22', 'P24', 'P28']:
    with open(f'scratch/result_{q}.json', 'r', encoding='utf-8') as f:
        res[q] = json.load(f)

with open('scratch/l1e_runaway_results.json', 'w', encoding='utf-8') as f:
    json.dump(res, f, indent=2, ensure_ascii=False)

print('ALL 7 SAVED TO scratch/l1e_runaway_results.json')
for q, d in res.items():
    print(f"{q}: status={d['status']}, tok={d['generated_tokens']}, runaway={d['runaway_detected']}, complete={d['sentence_complete']}, trunc={d['truncated']}")
