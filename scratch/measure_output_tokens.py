import json, statistics, math

def compute_stats(values):
    if not values:
        return {}
    sorted_v = sorted(values)
    n = len(sorted_v)
    mean = statistics.mean(sorted_v)
    median = statistics.median(sorted_v)
    min_v = sorted_v[0]
    max_v = sorted_v[-1]

    def percentile(p):
        if n == 1:
            return sorted_v[0]
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_v[int(k)]
        return sorted_v[int(f)] * (c - k) + sorted_v[int(c)] * (k - f)

    return {
        'count': n,
        'mean': round(mean, 2),
        'median': round(median, 2),
        'p50': round(median, 2),
        'p90': round(percentile(0.90), 2),
        'p95': round(percentile(0.95), 2),
        'min': round(min_v, 2),
        'max': round(max_v, 2),
    }

with open('scratch/p0_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

output_tokens = []
baselines = data.get('baselines', {})
if 'en_text_cold' in baselines and 'tokens_generated' in baselines['en_text_cold']:
    output_tokens.append(baselines['en_text_cold']['tokens_generated'])

for k, v in data.get('diagnostics', {}).items():
    if isinstance(v, dict) and 'eval_count' in v and v['eval_count'] > 5:
        output_tokens.append(v['eval_count'])
        
for k, v in data.get('threading', {}).items():
    if isinstance(v, dict):
        for run in v.get('sample_runs', []):
            if 'eval_count' in run and run['eval_count'] > 5:
                output_tokens.append(run['eval_count'])

print('Collected output token counts:', output_tokens)
stats = compute_stats(output_tokens)
print('Output Token Distribution:', json.dumps(stats, indent=2))
