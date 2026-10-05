# Reproducible Percentile Recalculation & Methodological Audit

- **Source Dataset**: scratch/level2_rerank_experiment/benchmark_results.json
- **Source SHA-256**: 89846b3e6dbb04abc233faeea527e70ce9dbdedb3fab1fc8e21f3dd49dafa7b6
- **Total Paired Observations**: 48 paired repetitions across 24 queries (48 Arm 15, 48 Arm 10)

## 1. Mathematical Index Definitions

Four discrete approaches are analyzed across the 48 sorted latency values ( = 48$):

1. **Method 1: Original Harness Discrete Index Rule**:
   - Formula: $\text{idx} = \lfloor p \times (n - 1) \rfloor = \lfloor p \times 47 \rfloor$
   - P50: $\lfloor 0.50 \times 47 \rfloor = 23$ (24th element)
   - P90: $\lfloor 0.90 \times 47 \rfloor = 42$ (43rd element)
   - P95: $\lfloor 0.95 \times 47 \rfloor = 44$ (45th element)
   - *Characteristics*: Integer truncation on zero-indexed range $[0, n-1]$. Does not interpolate.

2. **Method 2: Recalculation Discrete Index Rule**:
   - Formula: $\text{idx} = \min(\lfloor n \times p \rfloor, n - 1) = \min(\lfloor 48 \times p \rfloor, 47)$
   - P50: $\lfloor 48 \times 0.50 \rfloor = 24$ (25th element)
   - P90: $\lfloor 48 \times 0.90 \rfloor = 43$ (44th element)
   - P95: $\lfloor 48 \times 0.95 \rfloor = 45$ (46th element)
   - *Characteristics*: Scales by $ then truncates. For =48$ and =0.90, 0.95$, shifts selected index upward by exactly 1 position compared to Method 1.

3. **Method 3: Standard Nearest-Rank (NIST / ceil)**:
   - Formula: $\text{idx} = \lceil p \times n \rceil - 1$
   - P50: $\lceil 0.50 \times 48 \rceil - 1 = 24 - 1 = 23$
   - P90: $\lceil 0.90 \times 48 \rceil - 1 = 44 - 1 = 43$
   - P95: $\lceil 0.95 \times 48 \rceil - 1 = 46 - 1 = 45$
   - *Characteristics*: Evaluates to index 43 for P90 and index 45 for P95 on =48$, matching Method 2 for P90/P95.

4. **Method 4: Continuous Linear Interpolation (NIST Type 7 / numpy.percentile)**:
   - Formula: (p) = y_i + (y_{i+1} - y_i) \times \text{fraction}$
   - Computes weighted linear interpolation between adjacent order statistics.

---

## 2. Comparative Percentile Matrix (All 48 Observations)

| Series / Metric | Method 1 (Harness: idx=int(p*(n-1))) | Method 2 (Recalc: min(int(n*p), n-1)) | Method 3 (Standard Nearest-Rank) | Method 4 (Linear Interpolation) |
| :--- | :--- | :--- | :--- | :--- |
| **Arm 15 P50** | 937.412 ms (idx 23) | 950.882 ms (idx 24) | 937.412 ms (idx 23) | **944.147 ms** |
| **Arm 15 P90** | 1531.085 ms (idx 42) | 1579.140 ms (idx 43) | **1579.140 ms** (idx 43) | **1545.502 ms** |
| **Arm 15 P95** | 1602.492 ms (idx 44) | 2005.047 ms (idx 45) | **2005.047 ms** (idx 45) | **1864.153 ms** |
| **Arm 10 P50** | 644.209 ms (idx 23) | 647.317 ms (idx 24) | 644.209 ms (idx 23) | **645.763 ms** |
| **Arm 10 P90** | 1153.027 ms (idx 42) | 1215.459 ms (idx 43) | **1215.459 ms** (idx 43) | **1171.757 ms** |
| **Arm 10 P95** | 1360.657 ms (idx 44) | 1400.647 ms (idx 45) | **1400.647 ms** (idx 45) | **1386.650 ms** |
| **Paired Delta P50** | 288.779 ms (idx 23) | 296.014 ms (idx 24) | 288.779 ms (idx 23) | **292.397 ms** |
| **Paired Delta P90** | 691.818 ms (idx 42) | 739.368 ms (idx 43) | **739.368 ms** (idx 43) | **706.083 ms** |
| **Paired Delta P95** | 987.099 ms (idx 44) | 994.458 ms (idx 45) | **994.458 ms** (idx 45) | **991.882 ms** |

---

## 3. Tail Observations (Sorted Top 8 Values, Indices 40 to 47)

| Sorted Index | Arm 15 Latency (ms) | Arm 10 Latency (ms) | Paired Delta Latency ({15} - T_{10}$ ms) |
| :---: | :---: | :---: | :---: |
| 40 | 1485.495 | 1083.563 | 647.469 |
| 41 | 1500.569 | 1148.694 | 674.373 |
| 42 (Harness P90) | 1531.085 | 1153.027 | 691.818 |
| 43 (Nearest-Rank P90) | 1579.140 | 1215.459 | 739.368 |
| 44 (Harness P95) | 1602.492 | 1360.657 | 987.099 |
| 45 (Nearest-Rank P95) | 2005.047 | 1400.647 | 994.458 |
| 46 | 2261.138 | 1464.240 | 1300.776 |
| 47 (Max) | 2385.498 | 1562.467 | 1683.980 |

## 4. Methodological Findings & Guidance

1. **Discrete Index Shift**: Method 1 evaluates at index $\lfloor 0.90 \times 47 \rfloor = 42$ and $\lfloor 0.95 \times 47 \rfloor = 44$. Method 2 and Method 3 evaluate at index 43 and index 45. On discrete data with substantial tail jumps (e.g. Arm 15 jumps from 1602.492 ms at idx 44 to 2005.047 ms at idx 45), this 1-position shift results in a visible delta.
2. **Linear Interpolation**: Continuous linear interpolation (numpy.percentile) yields intermediate values that weight both adjacent observations, confirming median paired savings of 292.397 ms, P90 savings of 706.083 ms, and P95 savings of 991.882 ms.
3. Both discrete and continuous methods confirm consistent, substantial positive latency savings for Arm 10 across all percentiles.
