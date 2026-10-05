import json
import statistics

def recalculate_performance():
    bench_path = r"D:\Karnataka Guide\evidence\20260927_142438_reranker_verification\original_artifacts\benchmark_results.json"
    with open(bench_path, "r", encoding="utf-8") as f:
        bench = json.load(f)

    queries = bench["queries"]

    arm15_all = []
    arm10_all = []
    paired_deltas_all = []

    rep1_arm15 = []
    rep1_arm10 = []
    rep1_deltas = []

    rep2_arm15 = []
    rep2_arm10 = []
    rep2_deltas = []

    faster_count = 0  # Arm 10 faster (delta > 0)
    slower_count = 0  # Arm 10 slower (delta < 0)
    tied_count = 0    # Tied (delta == 0)

    for qid in sorted(queries.keys()):
        q = queries[qid]
        r1 = q["rep1_15_then_10"]
        r2 = q["rep2_10_then_15"]

        t15_r1 = r1["arm_15"]["rerank_duration_ms"]
        t10_r1 = r1["arm_10"]["rerank_duration_ms"]
        d_r1 = t15_r1 - t10_r1

        t15_r2 = r2["arm_15"]["rerank_duration_ms"]
        t10_r2 = r2["arm_10"]["rerank_duration_ms"]
        d_r2 = t15_r2 - t10_r2

        arm15_all.extend([t15_r1, t15_r2])
        arm10_all.extend([t10_r1, t10_r2])
        paired_deltas_all.extend([d_r1, d_r2])

        rep1_arm15.append(t15_r1)
        rep1_arm10.append(t10_r1)
        rep1_deltas.append(d_r1)

        rep2_arm15.append(t15_r2)
        rep2_arm10.append(t10_r2)
        rep2_deltas.append(d_r2)

        for d in [d_r1, d_r2]:
            if d > 0.001:
                faster_count += 1
            elif d < -0.001:
                slower_count += 1
            else:
                tied_count += 1

    def stats(arr):
        s_arr = sorted(arr)
        n = len(arr)
        def p(pct):
            idx = int(n * pct)
            return s_arr[min(idx, n - 1)]
        return {
            "count": n,
            "mean": round(statistics.mean(arr), 2),
            "median": round(statistics.median(arr), 2),
            "min": round(min(arr), 2),
            "max": round(max(arr), 2),
            "p90": round(p(0.90), 2),
            "p95": round(p(0.95), 2),
            "stdev": round(statistics.stdev(arr), 2),
        }

    s_15 = stats(arm15_all)
    s_10 = stats(arm10_all)
    s_delta = stats(paired_deltas_all)

    median_diff_arms = round(s_15["median"] - s_10["median"], 2)
    median_paired_diff = s_delta["median"]

    print("=" * 80)
    print("PERFORMANCE METRICS RECALCULATION")
    print("=" * 80)
    print("Arm 15 Latency (48 executions):")
    print(f"  Mean: {s_15['mean']} ms, Median: {s_15['median']} ms, Min: {s_15['min']} ms, Max: {s_15['max']} ms, P90: {s_15['p90']} ms, P95: {s_15['p95']} ms, StDev: {s_15['stdev']} ms")
    print("Arm 10 Latency (48 executions):")
    print(f"  Mean: {s_10['mean']} ms, Median: {s_10['median']} ms, Min: {s_10['min']} ms, Max: {s_10['max']} ms, P90: {s_10['p90']} ms, P95: {s_10['p95']} ms, StDev: {s_10['stdev']} ms")
    
    print("\nPaired Differences (T_15 - T_10, 48 pairs):")
    print(f"  Mean Paired Delta: {s_delta['mean']} ms")
    print(f"  Median Paired Delta: {median_paired_diff} ms")
    print(f"  Difference between Arm Medians: {median_diff_arms} ms")
    print(f"  Min: {s_delta['min']} ms, Max: {s_delta['max']} ms, P90: {s_delta['p90']} ms, P95: {s_delta['p95']} ms, StDev: {s_delta['stdev']} ms")
    
    print("\nSpeedup Counts (48 pairs):")
    print(f"  Arm 10 Faster (delta > 0): {faster_count} / 48 ({faster_count / 48 * 100:.1f}%)")
    print(f"  Arm 10 Slower (delta < 0): {slower_count} / 48 ({slower_count / 48 * 100:.1f}%)")
    print(f"  Tied (delta == 0): {tied_count} / 48 ({tied_count / 48 * 100:.1f}%)")

    print("\nRepetition Ordering Comparison:")
    s_r1_d = stats(rep1_deltas)
    s_r2_d = stats(rep2_deltas)
    print(f"  Rep 1 (15-then-10, 24 pairs): Mean Delta = {s_r1_d['mean']} ms, Median Delta = {s_r1_d['median']} ms")
    print(f"  Rep 2 (10-then-15, 24 pairs): Mean Delta = {s_r2_d['mean']} ms, Median Delta = {s_r2_d['median']} ms")

    out_file = r"D:\Karnataka Guide\evidence\20260927_142438_reranker_verification\performance_recalculation.json"
    recalc_export = {
        "arm_15_latency_ms": s_15,
        "arm_10_latency_ms": s_10,
        "paired_deltas_ms": s_delta,
        "difference_between_arm_medians_ms": median_diff_arms,
        "median_paired_difference_ms": median_paired_diff,
        "pair_counts": {
            "total_pairs": len(paired_deltas_all),
            "arm10_faster_count": faster_count,
            "arm10_faster_pct": round(faster_count / len(paired_deltas_all) * 100, 2),
            "arm10_slower_count": slower_count,
            "arm10_slower_pct": round(slower_count / len(paired_deltas_all) * 100, 2),
            "tied_count": tied_count
        },
        "order_comparison": {
            "rep1_15_first": {
                "arm_15": stats(rep1_arm15),
                "arm_10": stats(rep1_arm10),
                "paired_delta": s_r1_d
            },
            "rep2_10_first": {
                "arm_15": stats(rep2_arm15),
                "arm_10": stats(rep2_arm10),
                "paired_delta": s_r2_d
            }
        }
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(recalc_export, f, indent=2)

    print(f"\nSaved performance recalculation to {out_file}")

if __name__ == "__main__":
    recalculate_performance()
