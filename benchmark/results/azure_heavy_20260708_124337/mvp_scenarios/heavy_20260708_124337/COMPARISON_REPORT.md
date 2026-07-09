# LangGraph vs ChorusGraph — Group Comparisons

Each row compares **ChorusGraph − LangGraph** within one domain/mode pair.
Winner uses non-overlapping 95% CIs when possible; otherwise point estimate (marginal).

## Finance Single (FL1 vs FC1)

**Overall:** chorusgraph (Chorus wins 11 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 90.0% [87.1%, 92.9%] | 96.7% [95.2%, 98.2%] | — |
| LLM calls / task | 3.29 [3.16, 3.44] | 0.7967 [0.6900, 0.9167] | -2.4967 [-2.6633, -2.3300] |
| Mean latency | 4966.17 [4719.97, 5231.27] | 1351.40 [1161.03, 1580.21] | -3614.7667 [-3882.3253, -3351.3460] |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 49.7% [44.0%, 55.3%] | — |
| Abstain rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 90.0% [87.1%, 92.9%] | 96.7% [95.2%, 98.2%] | — | **chorusgraph** |
| LLM calls / task | 3.29 [3.16, 3.44] | 0.7967 [0.6900, 0.9167] | -2.4967 [-2.6633, -2.3300] | **chorusgraph** |
| Mean latency | 4966.17 [4719.97, 5231.27] | 1351.40 [1161.03, 1580.21] | -3614.7667 [-3882.3253, -3351.3460] | **chorusgraph** |
| Latency p50 | 4091.50 [3984.99, 4221.15] | 47.50 [37.50, 79.00] | — | **chorusgraph** |
| Latency p95 | 9701.55 [9292.00, 10519.25] | 5250.95 [4695.00, 6514.00] | — | **chorusgraph** |
| Cost / task | 0.0003 [0.0003, 0.0004] | 0.0001 [0.0001, 0.0001] | -0.0003 [-0.0003, -0.0002] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 49.7% [44.0%, 55.3%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 1162.26 [1113.47, 1212.42] | 285.79 [244.67, 330.51] | — | **chorusgraph** |
| Tokens out / task | 268.61 [256.01, 281.65] | 66.15 [56.57, 76.86] | — | **chorusgraph** |
| Tool calls / task | 0.8667 [0.8166, 0.9200] | 0.3633 [0.3033, 0.4233] | — | **chorusgraph** |
| Error rate | 0.7% [0.0%, 2.4%] | 0.0% [0.0%, 1.3%] | — | **chorusgraph** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | — | **tie** |
| Abstain rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — | **tie** |

Paired tasks: **300** (same task/case IDs)

## Finance Multi (FL2 vs FC2)

**Overall:** chorusgraph (Chorus wins 10 metrics, LangGraph wins 2 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|
| Task success | 89.4% [86.3%, 92.5%] | 34.3% [28.8%, 39.9%] | — |
| LLM calls / task | 2.04 [2.01, 2.06] | 0.2133 [0.1600, 0.2667] | -1.8092 [-1.8728, -1.7456] |
| Mean latency | 3071.07 [2867.48, 3286.82] | 408.22 [317.85, 509.49] | -2645.3781 [-2874.6053, -2436.6915] |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 11.0% [7.0%, 15.0%] | — |
| Abstain rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — |

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|
| Task success | 89.4% [86.3%, 92.5%] | 34.3% [28.8%, 39.9%] | — | **langgraph** |
| LLM calls / task | 2.04 [2.01, 2.06] | 0.2133 [0.1600, 0.2667] | -1.8092 [-1.8728, -1.7456] | **chorusgraph** |
| Mean latency | 3071.07 [2867.48, 3286.82] | 408.22 [317.85, 509.49] | -2645.3781 [-2874.6053, -2436.6915] | **chorusgraph** |
| Latency p50 | 2432.00 [2374.00, 2475.00] | 86.00 [80.00, 93.00] | — | **chorusgraph** |
| Latency p95 | 7520.10 [5914.76, 8889.80] | 1878.85 [1515.00, 2490.35] | — | **chorusgraph** |
| Cost / task | 0.0002 [0.0002, 0.0002] | 0.0000 [0.0000, 0.0000] | -0.0001 [-0.0002, -0.0001] | **chorusgraph** |
| Cache hit rate | 0.0% [0.0%, 1.3%] | 11.0% [7.0%, 15.0%] | — | **chorusgraph** |
| LLM calls on cache hit | — | 0.0000 [0.0000, 0.0000] | — | **inconclusive** |
| Tokens in / task | 607.49 [582.53, 632.06] | 47.85 [35.92, 59.82] | — | **chorusgraph** |
| Tokens out / task | 126.69 [123.02, 130.46] | 15.48 [11.61, 19.51] | — | **chorusgraph** |
| Tool calls / task | 0.9293 [0.8834, 0.9718] | 0.1433 [0.1033, 0.1867] | — | **chorusgraph** |
| Error rate | 0.7% [0.0%, 2.5%] | 0.0% [0.0%, 1.3%] | — | **chorusgraph** |
| Embeds / task | 0.0000 [0.0000, 0.0000] | 4.55 [4.24, 4.84] | — | **langgraph** |
| Abstain rate | 0.0% [0.0%, 1.3%] | 0.0% [0.0%, 1.3%] | — | **tie** |

Paired tasks: **283** (same task/case IDs)

## Healthcare Single (HL1 vs HC1)

**Overall:** inconclusive (Chorus wins 0 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|

Paired tasks: **0** (same task/case IDs)

## Healthcare Multi (HL2 vs HC2)

**Overall:** inconclusive (Chorus wins 0 metrics, LangGraph wins 0 metrics)

### Key metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) |
|--------|-----------|-------------|---------|

### All metrics

| Metric | LangGraph | ChorusGraph | Δ (C−L) | Winner |
|--------|-----------|-------------|---------|--------|

Paired tasks: **0** (same task/case IDs)
