# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).
For **abstain rate**, **latency**, **LLM calls**, and **cost**, lower is better.

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 11 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 90.0% [87.1%, 92.9%] | 96.7% [95.2%, 98.2%] | — |
| LLM calls / task | 3.33 [3.20, 3.48] | 0.7967 [0.6900, 0.9167] | -2.5367 [-2.6968, -2.3767] |
| Mean latency | 4971.84 [4712.69, 5266.48] | 1318.18 [1134.41, 1524.99] | -3653.6633 [-3902.9311, -3402.4148] |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 49.7% [44.0%, 55.3%] | — |
| Abstain rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 90.0% [87.1%, 92.9%] | 96.7% [95.2%, 98.2%] | — | **chorusgraph** |
| LLM calls / task | 3.33 [3.20, 3.48] | 0.7967 [0.6900, 0.9167] | -2.5367 [-2.6968, -2.3767] | **chorusgraph** |
| Mean latency | 4971.84 [4712.69, 5266.48] | 1318.18 [1134.41, 1524.99] | -3653.6633 [-3902.9311, -3402.4148] | **chorusgraph** |
| Latency p50 | 4009.00 [3934.49, 4127.50] | 49.00 [36.00, 98.50] | — | **chorusgraph** |
| Latency p95 | 9784.20 [9125.64, 11253.00] | 5141.20 [4075.85, 6199.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0003 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 49.7% [44.0%, 55.3%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1174.97 [1125.02, 1226.42] | 286.22 [245.15, 330.74] | — | **chorusgraph** |
| Tokens out / task | 270.26 [257.74, 283.35] | 65.08 [55.54, 75.51] | — | **chorusgraph** |
| Tool calls / task | 0.8667 [0.8166, 0.9200] | 0.3633 [0.3033, 0.4233] | — | **chorusgraph** |
| Error rate | 0.7% [0.0%, 2.4%] | 0.0% [0.0%, 1.3%] | — | **chorusgraph** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — | **tie** |

Paired tasks: **300** (same task/case IDs)

## Finance Multi (FL2 vs FC2)

**Overall:** chorusgraph (Chorus wins 11 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 89.0% [85.9%, 92.1%] | 93.0% [90.6%, 95.4%] | — |
| LLM calls / task | 2.04 [2.02, 2.07] | 0.7533 [0.6833, 0.8233] | -1.2867 [-1.3600, -1.2167] |
| Mean latency | 3080.78 [2882.59, 3293.75] | 1334.80 [1167.18, 1515.39] | -1745.9800 [-1987.8531, -1520.6019] |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 34.7% [29.1%, 40.2%] | — |
| Abstain rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 89.0% [85.9%, 92.1%] | 93.0% [90.6%, 95.4%] | — | **chorusgraph** |
| LLM calls / task | 2.04 [2.02, 2.07] | 0.7533 [0.6833, 0.8233] | -1.2867 [-1.3600, -1.2167] | **chorusgraph** |
| Mean latency | 3080.78 [2882.59, 3293.75] | 1334.80 [1167.18, 1515.39] | -1745.9800 [-1987.8531, -1520.6019] | **chorusgraph** |
| Latency p50 | 2530.00 [2477.00, 2584.00] | 1273.00 [1221.49, 1350.50] | — | **chorusgraph** |
| Latency p95 | 6362.55 [5748.55, 9343.00] | 5370.35 [3200.90, 6244.64] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0002, 0.0002] | 0.0001 [0.0001, 0.0001] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 34.7% [29.1%, 40.2%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 615.27 [589.38, 641.80] | 171.67 [156.14, 186.99] | — | **chorusgraph** |
| Tokens out / task | 128.56 [124.29, 132.78] | 60.41 [55.00, 65.95] | — | **chorusgraph** |
| Tool calls / task | 0.9367 [0.8933, 0.9801] | 0.5633 [0.5033, 0.6267] | — | **chorusgraph** |
| Error rate | 0.7% [0.0%, 2.4%] | 0.0% [0.0%, 1.3%] | — | **chorusgraph** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 8.56 [8.35, 8.79] | — | **inconclusive** |
| Abstain rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — | **tie** |

Paired tasks: **300** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** chorusgraph (Chorus wins 11 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 73.7% [69.0%, 78.3%] | 84.0% [80.3%, 87.7%] | — |
| LLM calls / task | 2.94 [2.84, 3.05] | 1.33 [1.26, 1.40] | -1.6067 [-1.7467, -1.4633] |
| Mean latency | 7104.85 [6628.42, 7647.99] | 3811.67 [3615.90, 4031.11] | -3293.1800 [-3786.6292, -2815.4997] |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 72.7% [67.9%, 77.4%] | — |
| Abstain rate | 34.3% [28.8%, 39.9%] | 23.3% [18.2%, 28.4%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 73.7% [69.0%, 78.3%] | 84.0% [80.3%, 87.7%] | — | **chorusgraph** |
| LLM calls / task | 2.94 [2.84, 3.05] | 1.33 [1.26, 1.40] | -1.6067 [-1.7467, -1.4633] | **chorusgraph** |
| Mean latency | 7104.85 [6628.42, 7647.99] | 3811.67 [3615.90, 4031.11] | -3293.1800 [-3786.6292, -2815.4997] | **chorusgraph** |
| Latency p50 | 5950.50 [5607.00, 6670.00] | 3422.00 [3229.00, 3595.00] | — | **chorusgraph** |
| Latency p95 | 16468.25 [14797.00, 18234.65] | 8218.05 [5633.00, 8560.10] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0003] | 0.0002 [0.0002, 0.0002] | -0.0001 [-0.0001, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 72.7% [67.9%, 77.4%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 1.00 [1.00, 1.00] | — | **inconclusive** |
| Tokens in / task | 890.29 [846.80, 939.71] | 884.11 [849.65, 922.74] | — | **chorusgraph** |
| Tokens out / task | 316.41 [303.45, 330.98] | 106.64 [95.22, 118.30] | — | **chorusgraph** |
| Tool calls / task | 1.28 [1.21, 1.36] | 0.2900 [0.2333, 0.3467] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 34.3% [28.8%, 39.9%] | 23.3% [18.2%, 28.4%] | — | **chorusgraph** |

Paired tasks: **300** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 1 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 62.3% [57.0%, 67.6%] | 77.3% [73.0%, 81.7%] | — |
| LLM calls / task | 3.85 [3.68, 4.03] | 2.67 [2.49, 2.84] | -1.1867 [-1.2867, -1.0833] |
| Mean latency | 10354.30 [9723.92, 10952.11] | 9537.39 [8891.84, 10190.57] | -816.9067 [-1238.5342, -401.2293] |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 79.0% [74.8%, 83.2%] | — |
| Abstain rate | 14.7% [10.2%, 19.1%] | 3.0% [0.4%, 5.6%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 62.3% [57.0%, 67.6%] | 77.3% [73.0%, 81.7%] | — | **chorusgraph** |
| LLM calls / task | 3.85 [3.68, 4.03] | 2.67 [2.49, 2.84] | -1.1867 [-1.2867, -1.0833] | **chorusgraph** |
| Mean latency | 10354.30 [9723.92, 10952.11] | 9537.39 [8891.84, 10190.57] | -816.9067 [-1238.5342, -401.2293] | **chorusgraph** |
| Latency p50 | 10668.50 [9834.00, 11962.00] | 9338.50 [8576.00, 10253.50] | — | **chorusgraph** |
| Latency p95 | 18029.95 [17306.05, 18976.40] | 17970.10 [17138.60, 19813.45] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0003] | 0.0002 [0.0002, 0.0003] | -0.0000 [-0.0001, -0.0000] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 79.0% [74.8%, 83.2%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 2.26 [2.11, 2.42] | — | **inconclusive** |
| Tokens in / task | 817.80 [758.74, 875.65] | 898.90 [827.22, 965.70] | — | **langgraph** |
| Tokens out / task | 279.37 [263.40, 295.61] | 183.61 [169.52, 198.05] | — | **chorusgraph** |
| Tool calls / task | 0.8833 [0.8000, 0.9667] | 0.4800 [0.4100, 0.5500] | — | **chorusgraph** |
| Error rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — | **tie** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 7.37 [7.02, 7.72] | — | **inconclusive** |
| Abstain rate | 14.7% [10.2%, 19.1%] | 3.0% [0.4%, 5.6%] | — | **chorusgraph** |

Paired tasks: **300** (same task/case IDs)
